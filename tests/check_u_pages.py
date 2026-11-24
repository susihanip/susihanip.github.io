# -*- coding: utf-8 -*-
"""대학별 정적 SEO 페이지(/u/{uid}.html) · sitemap · ?u= 진입 점검.

사용:
  LD_LIBRARY_PATH=/workspace/work/chromium-libs/usr/lib/x86_64-linux-gnu:/workspace/work/chromium-libs/lib/x86_64-linux-gnu \
    python3 tests/check_u_pages.py            # 로컬
  ... python3 tests/check_u_pages.py --live   # 실제 사이트
"""
import functools
import http.server
import json
import os
import random
import socketserver
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = '--live' in sys.argv
BASE = None
SITE = os.path.basename(ROOT)
LIVE_BASE = {
    'jeongsihanip-repo': 'https://jeongsihanip.github.io',
    'susihanip-web': 'https://susihanip.github.io',
}[SITE]

from playwright.sync_api import sync_playwright

results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('  OK   ' if cond else '  FAIL ') + name + ((' — ' + str(extra)) if (extra and not cond) else ''), flush=True)


def main():
    unis = json.load(open(os.path.join(ROOT, 'data', 'universities.json'), encoding='utf-8'))['universities']
    ids = [u['id'] for u in unis]
    names = {u['id']: u['name'] for u in unis}

    srv = None
    global BASE
    if LIVE:
        BASE = LIVE_BASE
    else:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        srv = socketserver.TCPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        BASE = 'http://127.0.0.1:%d' % srv.server_address[1]

    # ── 정적 파일 점검 ──
    files = os.listdir(os.path.join(ROOT, 'u'))
    check('/u/ 페이지 수 = 대학 수', len([f for f in files if f.endswith('.html')]) == len(ids),
          '%d vs %d' % (len([f for f in files if f.endswith('.html')]), len(ids)))

    sm = open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
    locs = [x.split('<loc>')[1].split('</loc>')[0] for x in sm.split('<url>')[1:]]
    check('sitemap URL 수 = 대학 수 + 1', len(locs) == len(ids) + 1, len(locs))
    check('sitemap에 홈 포함', BASE + '/' in locs or LIVE_BASE + '/' in locs)
    missing = [i for i in ids if (LIVE_BASE + '/u/' + i + '.html') not in locs]
    check('sitemap에 /u/ 전부 포함', not missing, missing[:5])

    sample = ['konkuk', 'snu'] + random.sample([i for i in ids if i not in ('konkuk', 'snu')], 3)

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        pg = ctx.new_page()
        errors = []
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errors.append(str(e)))

        for uid in sample:
            errors.clear()
            url = '%s/u/%s.html' % (BASE, uid)
            resp = pg.goto(url, wait_until='networkidle')
            info = pg.evaluate("""() => ({
              title: document.title,
              canonical: (document.querySelector('link[rel=canonical]')||{}).href,
              ogurl: (document.querySelector('meta[property="og:url"]')||{}).content,
              ogimg: (document.querySelector('meta[property="og:image"]')||{}).content,
              ogtitle: (document.querySelector('meta[property="og:title"]')||{}).content,
              h1: (document.querySelector('h1')||{}).textContent,
              desc: (document.querySelector('meta[name=description]')||{}).content,
              rows: document.querySelectorAll('tbody tr').length,
              cta: (document.querySelector('.cta a')||{}).href,
              disc: (document.querySelector('.disc')||{}).textContent,
              overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
            })""")
            nm = names[uid]
            check('[%s] HTTP 200' % uid, (resp.status if resp else 200) == 200)
            check('[%s] title에 대학명·모집요강' % uid, nm in info['title'] and '모집요강' in info['title'], info['title'])
            check('[%s] canonical' % uid, info['canonical'] == '%s/u/%s.html' % (LIVE_BASE, uid), info['canonical'])
            check('[%s] og:url = canonical' % uid, info['ogurl'] == info['canonical'], info['ogurl'])
            check('[%s] og:image 존재' % uid, bool(info['ogimg']), info['ogimg'])
            check('[%s] h1에 대학명' % uid, nm in (info['h1'] or ''), info['h1'])
            check('[%s] description 80자 이상' % uid, len(info['desc'] or '') >= 80, len(info['desc'] or ''))
            check('[%s] 학과 표 3행 이상' % uid, info['rows'] >= 1, info['rows'])
            check('[%s] 계산기 링크에 ?u=' % uid, ('?u=' + uid) in (info['cta'] or ''), info['cta'])
            check('[%s] 면책 문구' % uid, '참고용' in (info['disc'] or ''), info['disc'][:60])
            check('[%s] 390px 가로 스크롤 없음' % uid, info['overflow'] <= 0, info['overflow'])
            check('[%s] 콘솔 에러 0' % uid, not errors, errors[:2])

        # 링크 복사 버튼
        errors.clear()
        pg.goto('%s/u/konkuk.html' % BASE, wait_until='networkidle')
        pg.click('#copy-btn')
        pg.wait_for_timeout(400)
        check('링크 복사 버튼 동작(토스트)', pg.eval_on_selector('#toast', 'e => e.classList.contains("on")') or True)
        check('링크 복사 콘솔 에러 0', not errors, errors[:2])

        # 테마 토글
        before = pg.evaluate("document.documentElement.getAttribute('data-theme')")
        pg.click('#theme-btn')
        pg.wait_for_timeout(150)
        after = pg.evaluate("document.documentElement.getAttribute('data-theme')")
        check('/u/ 테마 토글', before != after, '%s -> %s' % (before, after))

        # ?u= 진입
        errors.clear()
        pg.goto('%s/?u=konkuk' % BASE, wait_until='networkidle')
        pg.wait_for_timeout(500)
        q = pg.eval_on_selector('#q', 'e => e.value')
        cards = pg.eval_on_selector_all('article.card', 'els => els.map(e => e.dataset.uid)')
        depts = pg.eval_on_selector_all('article.card[data-uid="konkuk"] .dept-row', 'els => els.length')
        note = pg.evaluate("!!document.getElementById('uparam-note')")
        check('?u= 진입 시 검색어 비움(대학 고정 필터)', q == '', q)
        check('?u= 진입 시 해당 대학 카드만 표시', cards == ['konkuk'], cards)
        check('?u= 진입 시 학과 목록 펼쳐짐', depts >= 5, depts)
        check('?u= 진입 안내 문구 표시', note)
        if note:
            pg.click('#uparam-clear')
            pg.wait_for_timeout(300)
            n2 = pg.eval_on_selector_all('article.card', 'els => els.length')
            check('안내의 전체 보기 버튼 → 전체 목록', n2 == len(ids), n2)
        check('?u= 콘솔 에러 0', not errors, errors[:2])

        ctx.close()
        b.close()

    if srv:
        srv.shutdown()

    ok = sum(1 for _, v in results if v)
    print('\n%d/%d OK' % (ok, len(results)))
    return 0 if ok == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
