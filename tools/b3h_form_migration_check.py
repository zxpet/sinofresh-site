#!/usr/bin/env python3
"""Structural fidelity gate for the Gravity Forms -> Fluent Forms migration.

The stock migrator reports success while silently dropping fields, so "the import
completed" is not evidence. This compares the two sides field by field, using the
same normalising dumper for both (tools/b3h_form_dump.php) so a parsing mistake
cannot make both sides agree.

What it asserts, per form:
  * the mapping exists and names Gravity Forms as the source
  * titles and field counts match
  * labels match in order, and so do the required flags and the choice lists
  * each Gravity Forms type lands on the Fluent Forms element the repairs intend
  * every notification survives (Fluent Forms keeps one meta row per notification)
  * an HTML/notice field keeps its content, since a blank one is invisible
  * the date field is a date-only picker and the phone field is a tel input

The final block plants a defect in memory and requires the comparison to notice.
Without it, a comparator that silently compares nothing would still report green.

  python3 tools/b3h_form_migration_check.py [--json out.json]
"""

import argparse
import json
import subprocess
import sys

HOST = "root@65.49.215.152"
PUBLIC = "/var/www/dev.zxpet.com/public"
DUMPER = "tools/b3h_form_dump.php"

# Measured, not assumed: the two repairs are why phone and time are not what the
# plugin's own map (GravityFormsMigrator.php fieldTypes()) would give.
TYPE_MAP = {
    "text": "input_text",
    "email": "input_email",
    "select": "select",
    "textarea": "textarea",
    "checkbox": "input_checkbox",
    "hidden": "input_hidden",
    "date": "input_date",
    "html": "custom_html",
    "phone": "input_text",   # was dropped: 'phone' is a Pro element
    "time": "input_text",    # was input_date; Fluent Forms has no input_time
}

SOURCE_IDS = ["2", "3", "4", "5", "6"]

PASSED, FAILED = [], []


def check(label, ok, detail=""):
    (PASSED if ok else FAILED).append(label)
    line = "  %-4s %s" % ("ok" if ok else "FAIL", label)
    if detail and not ok:
        line += "\n         -- " + str(detail)
    print(line)
    return ok


def fetch():
    subprocess.run(["scp", "-o", "ConnectTimeout=20", DUMPER, "%s:/tmp/" % HOST],
                   check=True, capture_output=True)
    out = subprocess.run(
        ["ssh", "-o", "ConnectTimeout=40", HOST,
         "cd %s && php -d error_reporting=0 /usr/local/bin/wp eval-file /tmp/b3h_form_dump.php --allow-root"
         % PUBLIC],
        check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def compare(gf, ff, rev, ff_rows):
    """Returns a list of (label, ok, detail). A pure function of the two sides."""
    problems = []
    for gid in SOURCE_IDS:
        if gid not in gf:
            problems.append(("GF %s is absent from the dump" % gid, False, "source missing"))
            continue
        fid = rev.get(int(gid))
        if fid is None or str(fid) not in ff:
            problems.append(("GF %s maps to a Fluent Forms form" % gid, False,
                             "map says %r" % fid))
            continue
        g, f = gf[gid], ff[str(fid)]
        tag = "GF %s -> FF %s" % (gid, fid)

        problems.append(("%s: title preserved" % tag, g["title"] == f["title"],
                         "%r vs %r" % (g["title"], f["title"])))
        problems.append(("%s: field count preserved" % tag,
                         len(g["fields"]) == len(f["fields"]),
                         "%d vs %d" % (len(g["fields"]), len(f["fields"]))))
        if len(g["fields"]) != len(f["fields"]):
            continue

        for i, (a, b) in enumerate(zip(g["fields"], f["fields"])):
            where = "%s field %d (%s)" % (tag, i + 1, a["label"] or a["type"])
            # Hidden fields: FF keeps the GF adminLabel as its admin label, so
            # that is the name expected to survive.
            want_label = (a.get("admin_label") or a["label"]) if a["type"] == "hidden" else a["label"]
            problems.append(("%s: label" % where, want_label == b["label"],
                             "%r vs %r" % (want_label, b["label"])))
            problems.append(("%s: required" % where, a["required"] == b["required"],
                             "%r vs %r" % (a["required"], b["required"])))
            problems.append(("%s: choices" % where, a["choices"] == b["choices"],
                             "%r vs %r" % (a["choices"], b["choices"])))
            want = TYPE_MAP.get(a["type"])
            problems.append(("%s: element %s" % (where, want), b["type"] == want,
                             "got %r, wanted %r" % (b["type"], want)))
            if a["type"] == "html":
                problems.append(("%s: notice content kept" % where,
                                 a["html"] != "" and a["html"] == b["html"],
                                 "gf=%r ff=%r" % (a["html"][:60], b["html"][:60])))

        rows = ff_rows.get(str(fid), 0)
        problems.append(("%s: every notification kept (%d)" % (tag, len(g["notifications"])),
                         rows == len(g["notifications"]),
                         "%d rows for %d notifications" % (rows, len(g["notifications"]))))

    return problems


def extras_checks(ff, rows):
    """The two repairs, asserted on the stored structures rather than the log."""
    out = []
    # The tour form pairs "Preferred Date" with "Preferred Time"; a combined
    # Time & Date picker on the date field would duplicate the time question.
    dates = [(k, f) for k, form in ff.items() for f in form["fields"]
             if f["type"] == "input_date"]
    out.append(("every date field is a date-only picker",
                all(f["is_time_enabled"] is False for _, f in dates),
                [(k, f["label"], f["is_time_enabled"]) for k, f in dates]))
    phones = [(k, f) for k, form in ff.items() for f in form["fields"]
              if f["input_type"] == "tel"]
    out.append(("both phone fields exist and are tel inputs", len(phones) == 2,
                "%d found" % len(phones)))
    out.append(("no demo forms were left behind",
                not [k for k, f in ff.items() if f["title"] in
                     ("Contact Form Demo", "Subscription Form")],
                [f["title"] for f in ff.values()]))
    out.append(("the import map has exactly the five site forms",
                len(rows["map"]) == 5, rows["map"]))
    return out


args = argparse.ArgumentParser()
args.add_argument("--json")
opts = args.parse_args()

data = fetch()
gf, ff, ff_rows = data["gf"], data["ff"], data["ff_notification_rows"]
rev = {v["imported_form_id"]: int(k) for k, v in (data["map"] or {}).items()}

print("=== field-by-field comparison ===")
results = compare(gf, ff, rev, ff_rows)
for label, ok, detail in results:
    check(label, ok, detail)

print("\n=== repairs and leftovers ===")
for label, ok, detail in extras_checks(ff, data):
    check(label, ok, detail)

# ---- planted-defect control -------------------------------------------------
# Shift one form's fields by one and require the comparator to reject the pairing.
print("\n=== control: a planted mismatch must make the comparison fail ===")
baseline_bad = {label for label, ok, _ in results if not ok}
fid = rev.get(3)
if fid is None:
    check("control could run (GF 3 has a mapping)", False, "no mapping for GF 3")
else:
    tampered_ff = json.loads(json.dumps(ff))
    tampered_ff[str(fid)]["fields"] = (
        tampered_ff[str(fid)]["fields"][1:] + tampered_ff[str(fid)]["fields"][:1])
    tampered = compare(gf, tampered_ff, rev, ff_rows)
    new_bad = [(label, detail) for label, ok, detail in tampered
               if not ok and label not in baseline_bad]
    check("rotating one form's fields creates NEW failures", len(new_bad) > 0,
          "the comparator did not notice a rotated field list")
    check("and every new failure is specific to that form",
          all("GF 3 -> FF" in label for label, _ in new_bad),
          [label for label, _ in new_bad][:4])

print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
if opts.json:
    with open(opts.json, "w") as fh:
        json.dump({"passed": PASSED, "failed": FAILED, "data": data}, fh,
                  indent=1, ensure_ascii=False)
sys.exit(1 if FAILED else 0)
