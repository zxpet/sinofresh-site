/* H14 live pick verification — driven by `tools/h14_gate.py --live`.
 *
 *   usage: node h14_live_pick.js <cookies.json>
 *
 * Opens the Shape Library and the Container Library, clicks "Choose", picks
 * the first image in the media modal and confirms it, then reads the row's
 * hidden attachment input back. Prints one RESULT <json> line per page.
 *
 * READ-ONLY BY CONSTRUCTION: it never presses Submit, so no option is written.
 * The only server-side trace is the short-lived auth session the gate issues
 * and destroys around this run.
 *
 * The assertion that matters is `after`: a picked image must land in
 * `sf_<opt>[attachment_id][]`. Before H14 the selector missed the trailing
 * [] and this array stayed all-zero while the preview thumbnail updated —
 * which is why the bug looked like a successful pick.
 */
const fs = require('fs');
const { chromium } = require('playwright');

const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const H = data.hash;
const DOMAIN = data.domain;
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
         + '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

const PAGES = [
    { key: 'shapes',     field: 'sf_shapes',     table: 'sf-shapes',
      pick: '.sf-shapes__pick',
      url: 'https://' + DOMAIN + '/wp-admin/admin.php?page=sf-shapes' },
    { key: 'containers', field: 'sf_containers', table: 'sf-containers',
      pick: '.sf-containers__pick',
      url: 'https://' + DOMAIN + '/wp-admin/admin.php?page=sf-containers' },
];

function cookies() {
    return [
        ['wordpress_logged_in_' + H, data.logged_in],
        ['wordpress_sec_' + H, data.secure_auth],
        ['wordpress_' + H, data.auth],
    ].map(function (pair) {
        return {
            name: pair[0], value: pair[1], domain: DOMAIN, path: '/',
            httpOnly: true, secure: true, sameSite: 'Lax',
        };
    });
}

async function clickEl(page, handle) {
    await handle.scrollIntoViewIfNeeded();
    const b = await handle.boundingBox();
    if (!b) { return false; }
    await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
    return true;
}

async function runPage(browser, spec) {
    const rec = {
        key: spec.key, title: '', served: false,
        before: [], after: [], picked: 0, items: 0, errors: [], http: [],
        sel_old: -1, sel_new: -1,
    };
    const ctx = await browser.newContext({
        ignoreHTTPSErrors: true,
        httpCredentials: { username: data.user, password: data.pass },
        userAgent: UA,
    });
    await ctx.addCookies(cookies());
    const page = await ctx.newPage();
    page.on('console', function (m) {
        if (m.type() === 'error') { rec.errors.push(m.text().slice(0, 120)); }
    });
    // Record failed responses explicitly: a console "404" line names no URL,
    // and this gate has to be able to tell a missing theme asset from noise.
    page.on('response', function (r) {
        if (r.status() >= 400) {
            rec.http.push(r.status() + ' ' + r.url().slice(0, 140));
        }
    });
    try {
        await page.goto(spec.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
        await page.waitForTimeout(3000);
        rec.title = await page.title();
        rec.served = !!(await page.$('#' + spec.table));
        const sel = 'input[name="' + spec.field + '[attachment_id][]"]';
        // Which selector actually matches the RENDERED DOM — page truth,
        // independent of which sf-site-settings.js version is loaded. This is
        // the half of the bug that can be proven before the pull.
        const counts = await page.evaluate(function () {
            return {
                old: document.querySelectorAll('input[name$="[attachment_id]"]').length,
                neu: document.querySelectorAll('input[name$="[attachment_id][]"]').length,
            };
        });
        rec.sel_old = counts.old;
        rec.sel_new = counts.neu;
        rec.before = await page.$$eval(sel, function (els) {
            return els.map(function (e) { return e.value; });
        });
        const pick = await page.$(spec.pick);
        if (pick) {
            await clickEl(page, pick);
            await page.waitForTimeout(2500);
            const items = await page.$$('.media-frame .attachments .attachment');
            rec.items = items.length;
            if (items.length) {
                await clickEl(page, items[0]);
                await page.waitForTimeout(900);
            }
            const btn = await page.$('.media-frame .media-button-select, '
                                   + '.media-frame .media-button-insert');
            if (btn) {
                await clickEl(page, btn);
                await page.waitForTimeout(1600);
            }
        } else {
            rec.errors.push('no pick button ' + spec.pick);
        }
        rec.after = await page.$$eval(sel, function (els) {
            return els.map(function (e) { return e.value; });
        });
        const hit = rec.after.filter(function (v) { return v && v !== '0'; });
        rec.picked = hit.length ? parseInt(hit[0], 10) : 0;
    } catch (e) {
        rec.errors.push('SCRIPT: ' + String(e.message).slice(0, 140));
    }
    await ctx.close();
    console.log('RESULT ' + JSON.stringify(rec));
}

(async function () {
    const browser = await chromium.launch();
    for (const spec of PAGES) {
        await runPage(browser, spec);
    }
    await browser.close();
    console.log('DONE');
})().catch(function (e) {
    console.error('FATAL ' + e.message);
    process.exit(1);
});
