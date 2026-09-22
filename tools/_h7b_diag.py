#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Throwaway diagnostic: what page is the browser on, at each step?"""
import base64
import json
import os
import subprocess
import time

HOST = 'https://dev.zxpet.com'
AUTH = os.environ.get('SF_DEV_AUTH') or 'sfdev:VkEws18Kl5V1qp3TpZ6s'
DETAIL = '/formulas/joint-support-soft-chews/'
DOSAGE = '/products/soft-chews/'


def run(cmd, timeout=120):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def ev(script):
    enc = base64.b64encode(script.encode('utf-8')).decode('ascii')
    rc, out, err = run(['agent-browser', 'eval', '-b', enc])
    if rc != 0:
        return {'eval_error': (out + err)[:200]}
    try:
        v = json.loads(out)
    except Exception:
        return {'raw': out[:200]}
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            return {'raw': v[:200]}
    return v


WHERE = ("(()=>{const l=document.querySelector('link[rel=stylesheet][href*=\"sinofresh-theme\"]');"
         "return {url:location.pathname+location.hash,"
         "sheet:l?l.getAttribute('href'):null,"
         "title:document.title.slice(0,60),"
         "modal:!!document.querySelector('.sf-inquiry-modal'),"
         "gallery:!!document.querySelector('.sf-gallery'),"
         "capsule:!!document.querySelector('.sf-float-btn--inquiry'),"
         "scrollY:Math.round(scrollY)};})()")


def main():
    b64 = base64.b64encode(AUTH.encode('utf-8')).decode('ascii')
    user, _, pw = AUTH.partition(':')
    run(['agent-browser', 'close', '--all'])
    run(['agent-browser', 'set', 'credentials', user, pw])
    run(['agent-browser', 'open', HOST + '/'])
    run(['agent-browser', 'set', 'headers',
         json.dumps({'Authorization': 'Basic ' + b64, 'X-SF-Preflight': '1'})])

    print('--- detail page ---')
    run(['agent-browser', 'open', HOST + DETAIL + '?diag=' + time.strftime('%H%M%S')])
    run(['agent-browser', 'reload'])
    run(['agent-browser', 'set', 'viewport', '1440', '900'])
    time.sleep(1)
    print(' after goto   ', json.dumps(ev(WHERE)))

    ev('window.scrollTo(0,900); scrollY')
    time.sleep(0.6)
    print(' after scroll ', json.dumps(ev(WHERE)))

    box = ev("(()=>{const e=document.querySelector('.sf-float-btn--inquiry');"
             "if(!e)return null;const r=e.getBoundingClientRect();"
             "return {x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),"
             "w:Math.round(r.width),h:Math.round(r.height)};})()")
    print(' capsule box  ', json.dumps(box))
    run(['agent-browser', 'mouse', 'move', str(box['x']), str(box['y'])])
    run(['agent-browser', 'mouse', 'down'])
    run(['agent-browser', 'mouse', 'up'])
    time.sleep(0.8)
    print(' after click  ', json.dumps(ev(WHERE)))
    print(' modal state  ', json.dumps(ev(
        "(()=>{const m=document.querySelector('.sf-inquiry-modal');"
        "return {open:m?m.classList.contains('is-open'):null,hidden:m?m.hidden:null};})()")))

    run(['agent-browser', 'press', 'Escape'])
    time.sleep(0.9)
    print(' after Escape ', json.dumps(ev(WHERE)))

    print('--- dosage page ---')
    run(['agent-browser', 'open', HOST + DOSAGE + '?diag=' + time.strftime('%H%M%S')])
    run(['agent-browser', 'reload'])
    time.sleep(1)
    print(' after goto   ', json.dumps(ev(WHERE)))
    run(['agent-browser', 'set', 'viewport', '1440', '900'])
    run(['agent-browser', 'reload'])
    time.sleep(1)
    print(' after reload ', json.dumps(ev(WHERE)))
    run(['agent-browser', 'close', '--all'])


if __name__ == '__main__':
    main()
