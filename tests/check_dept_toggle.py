# -*- coding: utf-8 -*-
"""학과 접기/펼치기 토글 점검: 계열 필터가 켜져 자동 펼침된 카드도 클릭으로 접히고 다시 펼쳐지는지

사용:
  python3 tests/check_dept_toggle.py           # 로컬
  python3 tests/check_dept_toggle.py --live    # https://susihanip.github.io/
"""
import sys, json, os, functools, threading, socketserver, http.server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = '--live' in sys.argv
BASE = 'https://susihanip.github.io/' if LIVE else None

from playwright.sync_api import sync_playwright

N = len(json.load(open(os.path.join(ROOT, 'data', 'universities.json'), encoding='utf-8'))['universities'])
results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('  OK   ' if cond else '  FAIL ') + name + ((' — ' + str(extra)) if extra and not cond else ''), flush=True)


def open_card(pg):
    """학과 목록 박스가 있는 첫 카드"""
    boxes = pg.locator('.card:has(.dept-box)')
    return boxes.first


def main():
    base = BASE
    srv = None
    if not LIVE:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        srv = socketserver.TCPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_address[1]}/'

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        pg = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        cons = []
        pg.on('console', lambda m: cons.append((m.type, m.text)) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: cons.append(('pageerror', str(e))))
        pg.goto(base, wait_until='load')
        pg.wait_for_selector('.card', timeout=40000)
        pg.wait_for_timeout(900)

        # 1) 전체 상태: 기본은 접힘 → 클릭 펼침 → 클릭 접힘
        card = open_card(pg)
        tgl = card.locator('[data-dept-toggle]')
        check('전체: 기본 접힘', tgl.get_attribute('aria-expanded') == 'false' and card.locator('.dept-list').count() == 0,
              tgl.get_attribute('aria-expanded'))
        check('전체: 접힘 버튼 문구 "보기"', '보기' in tgl.inner_text(), tgl.inner_text())
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('전체: 클릭 시 펼침', tgl.get_attribute('aria-expanded') == 'true' and card.locator('.dept-list').count() == 1,
              tgl.get_attribute('aria-expanded'))
        check('전체: 펼침 버튼 문구 "접기"', '접기' in tgl.inner_text(), tgl.inner_text())
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('전체: 다시 클릭 시 접힘', tgl.get_attribute('aria-expanded') == 'false' and card.locator('.dept-list').count() == 0,
              tgl.get_attribute('aria-expanded'))

        # 2) 계열 필터(이공계): 자동 펼침 → 첫 클릭에 접힘 → 다시 클릭에 펼침
        pg.click('[data-cat="i"]')
        pg.wait_for_timeout(900)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('이공계: 자동 펼침', tgl.get_attribute('aria-expanded') == 'true' and card.locator('.dept-list').count() == 1,
              tgl.get_attribute('aria-expanded'))
        n_expanded = card.locator('.dept-item').count()
        txt = tgl.inner_text()
        check('이공계: 펼침 문구에 필터된 학과 수', '접기' in txt and str(n_expanded) in txt, txt)
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('이공계: 첫 클릭에 학과 목록 접힘', card.locator('.dept-list').count() == 0 and tgl.get_attribute('aria-expanded') == 'false',
              card.locator('.dept-list').count())
        check('이공계: 접힌 뒤 버튼 문구 "학과 N개 보기"', '보기' in tgl.inner_text() and str(n_expanded) in tgl.inner_text(), tgl.inner_text())
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('이공계: 다시 클릭하면 펼쳐짐', card.locator('.dept-list').count() == 1 and tgl.get_attribute('aria-expanded') == 'true',
              card.locator('.dept-list').count())

        # 3) 문과 필터로 바꾸면 상태 초기화(자동 펼침)
        pg.click('[data-cat="m"]')
        pg.wait_for_timeout(900)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('문과: 필터 변경 후 자동 펼침', tgl.get_attribute('aria-expanded') == 'true' and card.locator('.dept-list').count() == 1,
              tgl.get_attribute('aria-expanded'))
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('문과: 첫 클릭에 접힘', card.locator('.dept-list').count() == 0 and tgl.get_attribute('aria-expanded') == 'false',
              card.locator('.dept-list').count())

        # 4) 전체로 돌아오면 다시 기본(접힘)
        pg.click('[data-cat="전체"]')
        pg.wait_for_timeout(900)
        cnt_open = pg.locator('.dept-list').count()
        check('전체 복귀: 카드 모두 접힘', cnt_open == 0, cnt_open)
        check('전체 복귀: 카드 수 유지', pg.locator('.card').count() == N, pg.locator('.card').count())

        check('콘솔 오류 0', len(cons) == 0, cons[:3])
        pg.close()
        b.close()

    ok = sum(1 for _, v in results if v)
    print(f'\n결과: {ok}/{len(results)} 통과 ({"live" if LIVE else "local"})')
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
