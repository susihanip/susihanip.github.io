# -*- coding: utf-8 -*-
"""학과 접기/펼치기 + 첫 방문 기본 테마 점검

  - 첫 방문(localStorage 비어 있음) 기본 테마 = light
  - 계열(이공계·문과) / 판정 필터 선택 시에도 모든 카드 학과 목록은 기본 접힘(aria-expanded="false")
  - 버튼 클릭 시 펼침("true"), 다시 클릭 시 접힘("false")
  - 다크 선택 시 저장·유지

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
    return pg.locator('.card:has(.dept-box)').first


def all_collapsed(pg):
    """학과 박스가 있는 모든 카드가 접혀 있고 펼쳐진 목록이 하나도 없는지"""
    flags = pg.eval_on_selector_all(
        '.card:has(.dept-box) [data-dept-toggle]',
        'els => els.map(e => e.getAttribute("aria-expanded"))')
    return flags, all(f == 'false' for f in flags) and pg.locator('.dept-list').count() == 0


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
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        pg = ctx.new_page()
        cons = []
        pg.on('console', lambda m: cons.append((m.type, m.text)) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: cons.append(('pageerror', str(e))))
        pg.goto(base, wait_until='load')
        pg.wait_for_selector('.card', timeout=40000)
        pg.wait_for_timeout(900)

        # 0) 첫 방문 기본 테마 = 라이트
        check('첫 방문: data-theme="light"', pg.evaluate('document.documentElement.getAttribute("data-theme")') == 'light',
              pg.evaluate('document.documentElement.getAttribute("data-theme")'))
        check('첫 방문: meta theme-color 라이트 배경',
              pg.evaluate('document.getElementById("meta-theme").getAttribute("content")') == '#f8fafc',
              pg.evaluate('document.getElementById("meta-theme").getAttribute("content")'))
        check('첫 방문: 라이트 버튼 aria-pressed="true"',
              pg.get_attribute('[data-theme-set="light"]', 'aria-pressed') == 'true')
        check('첫 방문: 다크 버튼 aria-pressed="false"',
              pg.get_attribute('[data-theme-set="dark"]', 'aria-pressed') == 'false')
        # 첫 페인트 이전에도 라이트였는지(html 속성) — 저장값 없는 컨텍스트의 초기 HTML
        check('첫 방문: localStorage 비어 있음', pg.evaluate('localStorage.getItem("susihanip-theme")') is None)

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

        # 2) 계열 필터(이공계): 모든 카드 기본 접힘 → 클릭 펼침 → 다시 클릭 접힘
        pg.click('[data-cat="i"]')
        pg.wait_for_timeout(900)
        flags, ok = all_collapsed(pg)
        check('이공계: 모든 카드 기본 접힘', ok, flags[:6])
        check('이공계: 카드가 남아 있음(필터 동작)', len(flags) > 0, len(flags))
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('이공계: 접힘 버튼 문구 "학과 N개 보기"', '보기' in tgl.inner_text() and '▼' in tgl.inner_text(), tgl.inner_text())
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        n_expanded = card.locator('.dept-item').count()
        txt = tgl.inner_text()
        check('이공계: 클릭 시 펼침', tgl.get_attribute('aria-expanded') == 'true' and card.locator('.dept-list').count() == 1,
              tgl.get_attribute('aria-expanded'))
        check('이공계: 펼침 문구에 학과 수', '접기' in txt and str(n_expanded) in txt, txt)
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('이공계: 다시 클릭 시 접힘', card.locator('.dept-list').count() == 0 and tgl.get_attribute('aria-expanded') == 'false',
              card.locator('.dept-list').count())

        # 3) 문과 필터로 바꿔도 기본 접힘
        pg.click('[data-cat="m"]')
        pg.wait_for_timeout(900)
        flags, ok = all_collapsed(pg)
        check('문과: 모든 카드 기본 접힘', ok, flags[:6])
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('문과: 클릭 시 펼침', card.locator('.dept-list').count() == 1 and tgl.get_attribute('aria-expanded') == 'true',
              tgl.get_attribute('aria-expanded'))
        tgl.click(); pg.wait_for_timeout(350)
        card = open_card(pg); tgl = card.locator('[data-dept-toggle]')
        check('문과: 다시 클릭 시 접힘', card.locator('.dept-list').count() == 0 and tgl.get_attribute('aria-expanded') == 'false',
              tgl.get_attribute('aria-expanded'))

        # 4) 전체로 돌아오면 다시 기본(접힘), 카드 수 유지
        pg.click('[data-cat="전체"]')
        pg.wait_for_timeout(900)
        flags, ok = all_collapsed(pg)
        check('전체 복귀: 카드 모두 접힘', ok, pg.locator('.dept-list').count())
        check('전체 복귀: 카드 수 유지', pg.locator('.card').count() == N, pg.locator('.card').count())

        # 5) 테마 전환·저장: 다크 선택 → 새로고침 후 다크 유지
        pg.click('[data-theme-set="dark"]')
        pg.wait_for_timeout(200)
        check('다크 선택 반영', pg.evaluate('document.documentElement.getAttribute("data-theme")') == 'dark')
        pg.reload(wait_until='load'); pg.wait_for_timeout(600)
        check('다크 저장 유지(새로고침)', pg.evaluate('document.documentElement.getAttribute("data-theme")') == 'dark')
        pg.click('[data-theme-set="light"]')
        pg.wait_for_timeout(200)
        pg.reload(wait_until='load'); pg.wait_for_timeout(600)
        check('라이트 저장 유지(새로고침)', pg.evaluate('document.documentElement.getAttribute("data-theme")') == 'light')

        check('콘솔 오류 0', len(cons) == 0, cons[:3])
        pg.close(); ctx.close()
        b.close()

    ok = sum(1 for _, v in results if v)
    print(f'\n결과: {ok}/{len(results)} 통과 ({"live" if LIVE else "local"})')
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
