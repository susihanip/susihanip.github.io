# -*- coding: utf-8 -*-
"""검색어에 따른 학과 목록 필터 점검

  - 대학명 검색('건국대') → 학과 수가 0개가 아니라 실제 학과 수로 표시, 클릭하면 펼쳐짐
  - 대학명 검색 + 계열 필터('이공계') → 그 계열 학과만 정상 카운트·표시(기본 접힘 유지)
  - 학과명 검색('컴퓨터') → 매칭된 학과만 표시되고 자동 펼침

사용:
  python3 tests/check_search_depts.py           # 로컬
  python3 tests/check_search_depts.py --live    # https://susihanip.github.io/
"""
import sys, json, os, functools, threading, socketserver, http.server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = '--live' in sys.argv
BASE = 'https://susihanip.github.io/' if LIVE else None

from playwright.sync_api import sync_playwright

DEPTS = json.load(open(os.path.join(ROOT, 'data', 'depts.json'), encoding='utf-8'))['universities']
TRACK = 'gyogwa'  # 기본 선택 전형 = 학생부교과


def kind(name):
    n = str(name)
    if '교과' in n:
        return 'gyogwa'
    if '종합' in n:
        return 'jonghap'
    return None


def pool(uid):
    """app.js 의 deptPool 과 같은 규칙(선택 전형 기준, 없으면 전체)"""
    rows = (DEPTS.get(uid) or {}).get('s') or []
    picked = [r for r in rows if any(kind(t[0]) == TRACK for t in (r[2] or []))]
    return picked if picked else rows


results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('  OK   ' if cond else '  FAIL ') + name + ((' — ' + str(extra)) if extra and not cond else ''), flush=True)


def search(pg, text):
    pg.fill('#q', '')
    pg.fill('#q', text)
    pg.wait_for_timeout(700)


def main():
    base = BASE
    srv = None
    if not LIVE:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        srv = socketserver.TCPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_address[1]}/'

    k_pool = pool('konkuk')
    n_konkuk = len(k_pool)
    n_konkuk_i = sum(1 for r in k_pool if r[1] == 'i')
    n_computer = sum(1 for uid in DEPTS for r in pool(uid) if '컴퓨터' in r[0])

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        pg = ctx.new_page()
        cons = []
        pg.on('console', lambda m: cons.append((m.type, m.text)) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: cons.append(('pageerror', str(e))))
        pg.goto(base, wait_until='load')
        pg.wait_for_selector('.card', timeout=40000)
        pg.wait_for_timeout(800)

        # 1) 대학명 검색만
        search(pg, '건국대')
        cnt = pg.inner_text('#count')
        check('건국대 검색: 카드 1곳', pg.locator('.card').count() == 1, pg.locator('.card').count())
        check(f'건국대 검색: 요약 "학과 {n_konkuk}개"', f'학과 {n_konkuk}개' in cnt, cnt)
        tgl = pg.locator('.card [data-dept-toggle]').first
        check(f'건국대 검색: 버튼 "학과 {n_konkuk}개"', f'학과 {n_konkuk}개' in tgl.inner_text(), tgl.inner_text())
        check('건국대 검색: 기본 접힘(11-25 규칙)', tgl.get_attribute('aria-expanded') == 'false' and pg.locator('.dept-list').count() == 0,
              tgl.get_attribute('aria-expanded'))
        tgl.click(); pg.wait_for_timeout(400)
        check('건국대 검색: 클릭 시 학과 목록 펼침', pg.locator('.dept-list').count() == 1)
        check('건국대 검색: 학과 항목 표시', pg.locator('.dept-item').count() == min(n_konkuk, 40), pg.locator('.dept-item').count())
        tgl = pg.locator('.card [data-dept-toggle]').first
        pg.screenshot(path=os.path.join(ROOT, 'tests', 'shot_search_konkuk_open.png'), full_page=False)
        tgl.click(); pg.wait_for_timeout(400)
        check('건국대 검색: 다시 클릭 시 접힘', pg.locator('.dept-list').count() == 0)

        # 2) 대학명 검색 + 계열 필터
        pg.click('[data-cat="i"]'); pg.wait_for_timeout(700)
        cnt = pg.inner_text('#count')
        check(f'건국대+이공계: 요약 "학과 {n_konkuk_i}개"', f'학과 {n_konkuk_i}개' in cnt, cnt)
        tgl = pg.locator('.card [data-dept-toggle]').first
        check(f'건국대+이공계: 버튼 "학과 {n_konkuk_i}개", 기본 접힘',
              f'학과 {n_konkuk_i}개' in tgl.inner_text() and tgl.get_attribute('aria-expanded') == 'false', tgl.inner_text())
        tgl.click(); pg.wait_for_timeout(400)
        names = pg.eval_on_selector_all('.dept-item .dept-name', 'els => els.map(e => e.textContent)')
        check('건국대+이공계: 펼친 목록이 전부 이공계 학과',
              len(names) == n_konkuk_i and set(names) <= set(r[0] for r in k_pool if r[1] == 'i'), names[:5])
        tgl = pg.locator('.card [data-dept-toggle]').first
        tgl.click(); pg.wait_for_timeout(400)
        check('건국대+이공계: 다시 클릭 시 접힘', pg.locator('.dept-list').count() == 0)
        pg.click('[data-cat="전체"]'); pg.wait_for_timeout(500)

        # 3) 학과명 검색 자동 펼침
        search(pg, '컴퓨터')
        cnt = pg.inner_text('#count')
        check(f'컴퓨터 검색: 요약 "학과 {n_computer}개"', f'학과 {n_computer}개' in cnt, cnt)
        flags = pg.eval_on_selector_all('[data-dept-toggle]', 'els => els.map(e => e.getAttribute("aria-expanded"))')
        check('컴퓨터 검색: 카드 전부 자동 펼침', flags and all(f == 'true' for f in flags), flags[:5])
        names = pg.eval_on_selector_all('.dept-item .dept-name', 'els => els.map(e => e.textContent)')
        check('컴퓨터 검색: 표시 학과가 전부 "컴퓨터" 포함', names and all('컴퓨터' in n for n in names), names[:5])
        pg.screenshot(path=os.path.join(ROOT, 'tests', 'shot_search_computer.png'), full_page=False)

        check('콘솔 오류 0', len(cons) == 0, cons[:3])
        pg.close(); ctx.close()
        b.close()
        if srv:
            srv.shutdown()

    ok = sum(1 for _, v in results if v)
    print(f'\n결과: {ok}/{len(results)} 통과 ({"live" if LIVE else "local"})')
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
