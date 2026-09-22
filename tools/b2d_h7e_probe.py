#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7e — the routing probe: does the renderer READ the option, or did it
just stop printing the old string?

The byte gate proves the 75 pages did not move. That is the whole point of the
batch, and it is also exactly what a batch that deleted the two rows would
have produced. `scoped` covers the rows being present and `--source` covers
the renderer CALLING the reader — but neither answers the question a person
actually asks about a change like this one: if operations edit the field
tomorrow, does the page change?

So the option is made to answer differently, in memory, and the page is asked.
`pre_option_<name>` short-circuits get_option() before it reaches the database,
so NOTHING IS WRITTEN: no option row is created, no option row is read, and the
probe installs a mu-plugin, takes three captures and deletes it again.

  before   the candidate as it ships                     -> the default prints
  during   pre_option returns FIXTURE-ORIGIN-H7E         -> the fixture prints
  after    the mu-plugin is gone                         -> the default returns

The third capture is not ceremony. A probe that only showed the fixture
printing would be satisfied by a filter that never unset itself, and the whole
point of the exercise is that the dev box is left exactly as it was found.

AND IT CHECKS PRECISION, not just effect. The value `Linyi, Shandong, China`
also appears 154 times outside this row — the about page's copy, the contact
page's address, the Organization schema's streetAddress. The probe fetches
/about/ in all three states and requires the fixture to move NOTHING there. A
batch that had replaced a global string instead of one row's source would pass
the product-page check and fail this one.

usage:
    b2d_h7e_probe.py --run [--theme default|preflight] [--json OUT]
"""

import argparse
import json
import os
import subprocess
import sys

HOST = 'root@65.49.215.152'
PUB = '/var/www/dev.zxpet.com/public'
MU = PUB + '/wp-content/mu-plugins'
FIX = MU + '/zz-sf-h7e-fixture.php'
BASE_URL = 'https://dev.zxpet.com'
AUTH = os.environ.get('SF_DEV_AUTH', 'sfdev:VkEws18Kl5V1qp3TpZ6s')

# One product page (carries the spec sheet) and one page that mentions the
# origin for an entirely different reason (no spec sheet at all).
PRODUCT = '/formulas/joint-support-soft-chews/'
OTHER = '/about/'

FIXTURE_PHP = """<?php
/**
 * Batch H7e routing probe — installed for one measurement and removed again.
 *
 * pre_option_<name> short-circuits get_option() before it reaches the
 * database, so this is the only way to make the option answer differently
 * without writing a row nothing would clean up.
 */
add_filter('pre_option_sf_factory_origin', function () { return 'FIXTURE-ORIGIN-H7E'; });
add_filter('pre_option_sf_factory_oem', function () { return 'FIXTURE-OEM-H7E'; });
"""

ORIGIN = 'Linyi, Shandong, China'
OEM_CELL = '<dd class="sf-fdetail-specs__value">Available</dd>'


def ssh(script, check=True):
    p = subprocess.run(['ssh', '-o', 'ConnectTimeout=25', HOST, 'bash -s'],
                       input=script, text=True, capture_output=True)
    if p.stdout:
        print(p.stdout, end='')
    if p.stderr:
        print(p.stderr, end='', file=sys.stderr)
    if check and p.returncode != 0:
        raise SystemExit('remote command failed (%d)' % p.returncode)
    return p


def fetch(path, theme):
    """One page, from the copy under test, with credentials."""
    cmd = ['curl', '-s', '--max-time', '45', '-u', AUTH, '-w', '\n%{http_code}']
    if theme == 'preflight':
        cmd += ['-H', 'X-SF-Preflight: 1']
    cmd.append(BASE_URL + path)
    p = subprocess.run(cmd, capture_output=True, text=True)
    body, _, code = p.stdout.rpartition('\n')
    return code.strip(), body


def install():
    """Write the mu-plugin and lint it BEFORE the next request can load it.

    A syntactically broken mu-plugin is a 500 on every page of the dev box, so
    the file is linted in the same ssh call that creates it and the caller
    refuses to go on if the lint did not pass.
    """
    p = ssh('cat > %s <<\'H7E_FIXTURE\'\n%s\nH7E_FIXTURE\nphp -l %s\n'
            % (FIX, FIXTURE_PHP, FIX))
    return 'No syntax errors' in p.stdout or 'No syntax errors' in p.stderr


def remove():
    """Delete the fixture and CONFIRM it is gone, by asking whether it is there.

    The confirmation is `test -e`, not `ls`. `ls` exits 2 on a missing file —
    which is exactly the outcome this function wants — and the first version of
    this tool ran it under `check=True`, so a SUCCESSFUL cleanup raised
    SystemExit. That is worth spelling out because of how it failed: SystemExit
    is not an Exception, so the `except Exception` around the cleanup in main()
    did not catch it either, the mu-plugin stayed on the dev box, and the whole
    visible symptom was a two-word "remote command failed (2)" printed under a
    run that had otherwise passed every row.
    """
    ssh('rm -f %s\n' % FIX, check=False)
    p = ssh('test -e %s && echo PRESENT || echo GONE\n' % FIX, check=False)
    return 'GONE' in p.stdout


def state_of(body):
    """Everything the probe asserts about one fetch, as plain counts."""
    return {
        'bytes': len(body),
        'fixture_origin': body.count('FIXTURE-ORIGIN-H7E'),
        'fixture_oem': body.count('FIXTURE-OEM-H7E'),
        'origin_value': body.count(ORIGIN),
        'origin_row': body.count('<dd class="sf-fdetail-specs__value">%s</dd>' % ORIGIN),
        'oem_row': body.count(OEM_CELL),
        'spec_sheet': body.count('class="sf-fdetail-specs"'),
    }


def run(theme, verbose=True):
    rows = []

    def ok(label, cond, detail=''):
        rows.append({'label': label, 'ok': bool(cond), 'detail': str(detail)})
        if verbose:
            print('  %s  %-64s %s' % ('ok  ' if cond else 'FAIL', label, detail))
        return bool(cond)

    ok_all = True

    # ---- state 0: as it ships -------------------------------------------
    code, prod_before = fetch(PRODUCT, theme)
    code2, other_before = fetch(OTHER, theme)
    b = state_of(prod_before)
    ob = state_of(other_before)
    ok_all &= ok('the product page is served, not a 401', code == '200' and code2 == '200',
                 'codes=%s/%s' % (code, code2))
    ok_all &= ok('the spec sheet carries the origin default', b['origin_row'] == 1, '%d row(s)' % b['origin_row'])
    ok_all &= ok('...and the OEM row is there', b['oem_row'] == 1, '%d row(s)' % b['oem_row'])
    ok_all &= ok('and no fixture string is present yet',
                 b['fixture_origin'] == 0 and b['fixture_oem'] == 0, '')

    # ---- state 1: the option answers differently ------------------------
    if not install():
        raise SystemExit('FATAL the fixture mu-plugin did not survive php -l')
    code, prod_during = fetch(PRODUCT, theme)
    _, other_during = fetch(OTHER, theme)
    d = state_of(prod_during)
    od = state_of(other_during)
    ok_all &= ok('with the fixture in place the page is still served', code == '200', 'code=%s' % code)
    ok_all &= ok('the origin row now prints the FIXTURE value',
                 d['fixture_origin'] == 1, '%d occurrence(s)' % d['fixture_origin'])
    ok_all &= ok('...and the OEM row prints the fixture value too',
                 d['fixture_oem'] == 1, '%d occurrence(s)' % d['fixture_oem'])
    # The two halves of the routing claim, together: the new value arrived AND
    # the old one left that cell. Either alone is satisfied by printing both.
    ok_all &= ok('...and the default has LEFT that row',
                 d['origin_row'] == 0 and d['oem_row'] == 0,
                 'origin_row=%d oem_row=%d' % (d['origin_row'], d['oem_row']))
    ok_all &= ok('the spec sheet itself is still in place',
                 d['spec_sheet'] == 1, '%d' % d['spec_sheet'])
    # Precision: the same string, elsewhere, must not have moved at all.
    ok_all &= ok('the other page is untouched by the fixture on the option path',
                 od['origin_value'] == ob['origin_value'] and od['fixture_origin'] == 0,
                 'origin mentions %d -> %d' % (ob['origin_value'], od['origin_value']))

    # ---- state 2: the fixture is gone -----------------------------------
    ok_all &= ok('the fixture mu-plugin is gone before the state is re-measured',
                 remove(), 'confirmed with test -e')
    code, prod_after = fetch(PRODUCT, theme)
    _, other_after = fetch(OTHER, theme)
    a = state_of(prod_after)
    oa = state_of(other_after)
    ok_all &= ok('after removal the page is served again', code == '200', 'code=%s' % code)
    ok_all &= ok('no fixture string survives anywhere',
                 a['fixture_origin'] == 0 and a['fixture_oem'] == 0
                 and oa['fixture_origin'] == 0, '')
    ok_all &= ok('...and the default is back in that row',
                 a['origin_row'] == 1 and a['oem_row'] == 1,
                 'origin_row=%d oem_row=%d' % (a['origin_row'], a['oem_row']))
    # The state the batch ships must be byte-identical to the state it started
    # in. The two fetches are the same request twice, so the masks the gate
    # applies are not needed here — but Cloudflare's data-cfemail is
    # re-randomised per response, so the comparison is made on the counts and
    # on a length that those tokens do not change.
    ok_all &= ok('the product page is back to the byte count it started at',
                 a['bytes'] == b['bytes'], '%d vs %d' % (b['bytes'], a['bytes']))
    ok_all &= ok('...and so is the page that never had the row',
                 oa['bytes'] == ob['bytes'], '%d vs %d' % (ob['bytes'], oa['bytes']))

    if verbose:
        print('  %s  routing probe: the renderer reads the option, and only that row'
              % ('PASS' if ok_all else 'FAIL'))
    return ok_all, rows, {'before': b, 'during': d, 'after': a,
                          'other_before': ob, 'other_during': od, 'other_after': oa}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--theme', choices=('default', 'preflight'), default='preflight')
    ap.add_argument('--json')
    args = ap.parse_args(argv)
    if not args.run:
        ap.error('--run is required; this tool installs a mu-plugin on the dev box')

    print('== H7e routing probe (theme=%s) ==' % args.theme)
    try:
        ok, rows, states = run(args.theme)
    finally:
        # Whatever happened, the mu-plugin does not outlive the process. This is
        # written to never raise: BaseException rather than Exception, because
        # the failure that actually bit was a SystemExit from a cleanup command
        # read as a failure, and SystemExit is not an Exception — so the guard
        # that was supposed to cover this case did not fire, and the fixture sat
        # on the dev box while the message that would have said so went by.
        try:
            if not remove():
                print('  cleanup: fixture STILL PRESENT after a second attempt',
                      file=sys.stderr)
        except BaseException as exc:                          # pragma: no cover
            print('  cleanup FAILED: %r' % (exc,), file=sys.stderr)

    print('\n%s  H7e routing probe' % ('PASS' if ok else 'FAIL'))
    if args.json:
        json.dump({'theme': args.theme, 'ok': ok, 'rows': rows, 'states': states},
                  open(args.json, 'w'), indent=1)
        print('  json -> %s' % args.json)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
