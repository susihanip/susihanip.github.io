# -*- coding: utf-8 -*-
"""수시한입 학과(모집단위) 기능 점검: 계열 필터·학과 검색·학과별 판정·자동 펼침

사용:
  python3 tests/check_depts.py           # 로컬
  python3 tests/check_depts.py --live    # https://susihanip.github.io/
"""
import sys, json, os, functools, threading, socketserver, http.server

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = '--live' in sys.argv
BASE = 'https://susihanip.github.io/' if LIVE else None

from playwright.sync_api import sync_playwright

N = len(json.load(open(os.path.join(ROOT, 'data', 'universities.json'), encoding='utf-8'))['universities'])
DEPT_UNIV = len(json.load(open(os.path.join(ROOT, 'data', 'depts.json'), encoding='utf-8'))['universities'])
results = []


def check(name, cond, extra=''):
    results.append((name, bool(cond)))
    print(('  OK   ' if cond else '  FAIL ') + name + ((' — ' + str(extra)) if extra and not cond else ''), flush=True)


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
        pg.wait_for_timeout(800)

        check(f'카드 {N}곳', pg.locator('.card').count() == N, pg.locator('.card').count())
        check('모든 대학 카드에 학과 목록', pg.locator('.dept-box').count() == N, pg.locator('.dept-box').count())
        check('학과 데이터 파일 로드(대학 수)', DEPT_UNIV >= N, DEPT_UNIV)

        # 1) 내신 입력 → 학과별 판정
        pg.fill('#score', '2.5')
        pg.wait_for_timeout(700)
        check('학과 판정 필터 노출', pg.is_visible('#dept-band-filters'))
        card = pg.locator('.card[data-id="konkuk"]')
        card.locator('[data-dept-toggle]').click()
        pg.wait_for_timeout(400)
        n_items = card.locator('.dept-item').count()
        check('학과 펼치기 동작', n_items > 0, n_items)
        first = card.locator('.dept-item').first.inner_text()
        check('학과 판정 배지 표시', any(x in first for x in ('안정', '적정', '소신', '어려움', '미등록')), first)
        check('학과 컷·내신 차이 표시', ('컷' in first), first)

        # 2) 학과별 전형 내역
        rows_with_tracks = card.locator('.dept-item:has(.dept-arw)')
        check('전형 여러 개 학과 표시(▾)', rows_with_tracks.count() > 0, rows_with_tracks.count())
        if rows_with_tracks.count():
            rows_with_tracks.first.locator('.dept-row').click()
            pg.wait_for_timeout(400)
        check('전형별 컷 펼치기', card.locator('.dept-tracks').count() > 0, card.locator('.dept-tracks').count())

        # 3) 계열 필터
        pg.click('[data-cat="s"]')
        pg.wait_for_timeout(700)
        cnt = pg.locator('#count').inner_text()
        check('계열 필터: 학과 수 표시', '학과' in cnt, cnt)
        cats = set()
        for i in range(min(20, pg.locator('.dept-item').count())):
            cats.add(pg.locator('.dept-item .dept-cat').nth(i).inner_text())
        check('계열 필터: 의약·보건만 노출', cats <= {'의약·보건'}, cats)
        check('계열 필터: 카드 자동 펼침', pg.locator('.dept-item').count() > 0, pg.locator('.dept-item').count())

        # 4) 학과명 검색
        pg.click('[data-cat="전체"]')
        pg.wait_for_timeout(400)
        pg.fill('#q', '간호')
        pg.wait_for_timeout(800)
        cnt2 = pg.locator('#count').inner_text()
        check('학과 검색: 결과 집계', '학과' in cnt2, cnt2)
        names = [pg.locator('.dept-item .dept-name').nth(i).inner_text() for i in range(min(10, pg.locator('.dept-item .dept-name').count()))]
        check('학과 검색: 일치 학과만', all('간호' in n for n in names), names)

        # 5) 학과 판정 필터
        pg.fill('#q', '')
        pg.wait_for_timeout(500)
        pg.click('[data-vband="어려움"]')
        pg.wait_for_timeout(800)
        badges = set()
        for i in range(min(15, pg.locator('.dept-item .badge').count())):
            badges.add(pg.locator('.dept-item .badge').nth(i).inner_text())
        check('학과 판정 필터: 어려움만', badges <= {'어려움', '어려움*'}, badges)

        pg.click('[data-vband="전체"]')
        pg.click('[data-cat="전체"]')
        pg.wait_for_timeout(500)
        check('필터 해제 후 카드 복귀', pg.locator('.card').count() == N, pg.locator('.card').count())

        # 6) 전형 전환(교과→종합) 시 학과 컷도 바뀐다
        pg.click('[data-track="jonghap"]')
        pg.wait_for_timeout(700)
        check('종합 전환 후 학과 목록 유지', pg.locator('.dept-box').count() == N, pg.locator('.dept-box').count())

        ov = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check('390px 가로 오버플로 없음', ov <= 0, ov)
        check('콘솔 오류 0', len(cons) == 0, cons[:3])

        # 데스크톱
        pg2 = b.new_page(viewport={'width': 1440, 'height': 900})
        cons2 = []
        pg2.on('console', lambda m: cons2.append((m.type, m.text)) if m.type == 'error' else None)
        pg2.on('pageerror', lambda e: cons2.append(('pageerror', str(e))))
        pg2.goto(base, wait_until='load')
        pg2.wait_for_selector('.card', timeout=40000)
        pg2.wait_for_timeout(600)
        check('데스크톱 카드 렌더', pg2.locator('.card').count() == N, pg2.locator('.card').count())
        check('데스크톱 콘솔 오류 0', len(cons2) == 0, cons2[:3])
        b.close()

    ok = sum(1 for _, v in results if v)
    print(f'\n결과: {ok}/{len(results)} 통과 ({"live" if LIVE else "local"})')
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
