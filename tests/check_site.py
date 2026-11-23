# -*- coding: utf-8 -*-
"""수시한입 사이트 점검 스크립트 (로컬/라이브 공용)

사용:
  python3 tests/check_site.py            # 로컬 (내장 HTTP 서버)
  python3 tests/check_site.py --live     # https://susihanip.github.io/
"""
import sys, json, os, functools, threading, socketserver, http.server, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_DIR = os.path.join(ROOT, '..', '..', 'attachments', '2026-11-23')
LIVE = '--live' in sys.argv
BASE = 'https://susihanip.github.io/' if LIVE else None
TAG = 'live' if LIVE else 'local'

from playwright.sync_api import sync_playwright

N = len(json.load(open(os.path.join(ROOT, 'data', 'universities.json'), encoding='utf-8'))['universities'])

errors = []
def log(msg):
    print(('PASS ' if msg else 'FAIL ') if isinstance(msg, str) else msg, flush=True)

def main():
    srv = None
    base = BASE
    if not LIVE:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        srv = socketserver.TCPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_address[1]}/'
    os.makedirs(SHOT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%H%M%S')
    results = []
    def check(name, cond, extra=''):
        results.append((name, bool(cond)))
        print(('  OK   ' if cond else '  FAIL ') + name + ((' — ' + str(extra)) if extra and not cond else ''))

    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])

        # ── 모바일 390 ──
        pg = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        cons = []
        pg.on('console', lambda m: cons.append((m.type, m.text)) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: cons.append(('pageerror', str(e))))
        pg.goto(base, wait_until='load')
        pg.wait_for_selector('.card', timeout=30000)
        check(f'카드 {N}곳 렌더', pg.locator('.card').count() == N, pg.locator('.card').count())

        # 1) 내신 입력
        pg.fill('#score', '2.8')
        pg.wait_for_timeout(400)
        check('판정 사유 박스 표시', pg.locator('.why').count() == N, pg.locator('.why').count())
        check('내신 비교 문장', 'vs 중위 컷' in pg.locator('.why').first.inner_text() or 'vs 상위' in pg.locator('.why').first.inner_text())
        sum_txt = pg.locator('#score-sum').inner_text()
        check('요약에 내신 구간 카운트', '안정' in sum_txt and '어려움' in sum_txt, sum_txt)

        # 고려대 교과 카드 사유 확인
        korea = pg.locator('.card[data-id="korea"]')
        ktxt = korea.locator('.why').inner_text()
        check('고려대 카드: 내신 컷 비교 사유', '내 2.80' in ktxt and '최고 컷' in ktxt, ktxt)

        # 2) 수능 과목별 입력
        for k, v in [('kor', '3'), ('mat', '4'), ('eng', '2'), ('t1', '2'), ('t2', '3')]:
            pg.fill(f'[data-se="{k}"]', v)
        pg.wait_for_timeout(350)
        ktxt = korea.locator('.why').inner_text()
        check('수능최저 충족 판정 표시', ('기준 충족' in ktxt or '기준 미충족' in ktxt) and '학교추천' in ktxt, ktxt)
        check('수능최저 카운트 요약', '충족' in pg.locator('#score-sum').inner_text())

        # 3) 등급합 직접 입력
        pg.click('[data-se-mode="sum"]')
        pg.wait_for_timeout(150)
        check('등급합 입력칸 표시', pg.is_visible('#se-sum'))
        pg.select_option('#se-n', '3')
        pg.fill('#se-val', '9')
        pg.wait_for_timeout(350)
        ktxt = korea.locator('.why').inner_text()
        check('등급합 기준 판정', '3합 9' in ktxt, ktxt)
        pg.click('[data-se-mode="subject"]')
        pg.wait_for_timeout(150)

        # 4) 전형 전환
        pg.click('[data-track="jonghap"]')
        pg.wait_for_timeout(400)
        check('학생부종합 전환', pg.get_attribute('[data-track="jonghap"]', 'aria-pressed') == 'true')
        check('종합 사유 렌더', pg.locator('.why').count() >= 100)

        # 5) 대안 전형 버튼 (교과 미운영 대학 등)
        pg.click('[data-track="gyogwa"]')
        pg.wait_for_timeout(400)
        alt = pg.locator('.why-alt').first
        check('대안 전형 버튼 존재', alt.count() > 0)
        if alt.count():
            alt.click()
            pg.wait_for_timeout(300)

        # 5-1) 필터·정렬
        pg.fill('#score', '2.8')
        pg.wait_for_timeout(350)
        pg.click('[data-sort="가나다순"]')
        pg.wait_for_timeout(300)
        names = pg.locator('.card h2').all_inner_texts()
        # 한국어 정렬(ㅊ < ㅌ): 가천 → 가톨릭 → 강원 순서면 정상
        ok_sort = names.index('가천대학교') < names.index('가톨릭대학교') < names.index('강원대학교')
        check('가나다순 정렬', ok_sort, names[:3])
        pg.click('[data-region="서울"]')
        pg.wait_for_timeout(300)
        regions_ok = pg.evaluate("Array.from(document.querySelectorAll('.card')).length")
        check('지역 필터(서울) 동작', 0 < regions_ok < N, regions_ok)
        pg.click('[data-region="전체"]'); pg.wait_for_timeout(250)
        pg.click('[data-type="논술"]'); pg.wait_for_timeout(300)
        check('전형 필터(논술) 동작', 0 < pg.locator('.card').count() < N, pg.locator('.card').count())
        pg.click('[data-type="전체"]'); pg.wait_for_timeout(250)
        pg.click('[data-band="어려움"]'); pg.wait_for_timeout(300)
        check('구간 필터(어려움) 동작', 0 < pg.locator('.card').count() < N, pg.locator('.card').count())
        pg.click('[data-band="전체"]'); pg.wait_for_timeout(250)
        pg.click('#score-clear'); pg.wait_for_timeout(300)
        check('초기화로 내신·수능 입력 해제', pg.input_value('#score') == '' and pg.input_value('[data-se="kor"]') == '')

        # 6) 레이아웃 오버플로 · 모바일 여백 · 헤더 배치
        ow = pg.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        check('390px 가로 오버플로 없음', ow <= 1, f'{ow}px')
        gut = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.hero')).paddingLeft)")
        check('모바일 좌우 여백 18px', gut >= 18, f'{gut}px')
        hdr = pg.evaluate("""() => {
          const g = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return {x: r.x, r: r.right, y: r.y, b: r.bottom}; };
          return {brand: g('.brand'), theme: g('.theme-switch'), ch: g('.ch-link'), vw: innerWidth};
        }""")
        check('헤더 요소가 화면 안에 들어옴', hdr['ch']['r'] <= hdr['vw'] - 8 and hdr['brand']['x'] >= 8, hdr)
        check('로고·테마·유튜브 겹치지 않음', hdr['brand']['r'] <= hdr['theme']['x'] and hdr['theme']['r'] <= hdr['ch']['x'], hdr)

        # 7) 스크린샷 (다크/라이트, 모바일)
        pg.evaluate('window.scrollTo(0,0)')
        pg.wait_for_timeout(300)
        pg.screenshot(path=os.path.join(SHOT_DIR, f'{TAG}-susi-dark-390-{stamp}.png'))
        pg.screenshot(path=os.path.join(SHOT_DIR, f'{TAG}-susi-dark-card-390-{stamp}.png'), clip={'x': 0, 'y': 300, 'width': 390, 'height': 900}) if False else None
        pg.click('[data-theme-set="light"]')
        pg.wait_for_timeout(350)
        check('라이트 테마 전환', pg.evaluate('document.documentElement.getAttribute("data-theme")') == 'light')
        bg = pg.evaluate("getComputedStyle(document.querySelector('.ch-link')).backgroundImage")
        check('라이트 테마 유튜브 버튼 빨간색', 'rgb(239, 68, 68)' in bg or 'rgb(220, 38, 38)' in bg, bg)
        pg.screenshot(path=os.path.join(SHOT_DIR, f'{TAG}-susi-light-390-{stamp}.png'))
        pg.reload(wait_until='load')
        pg.wait_for_selector('.card')
        check('테마 유지(새로고침)', pg.evaluate('document.documentElement.getAttribute("data-theme")') == 'light')
        pg.click('[data-theme-set="dark"]')

        # 등급 유지 확인 (localStorage 아님 → 초기화 정상)
        check('모바일 콘솔 오류 0', len(cons) == 0, cons[:3])
        pg.close()

        # ── 데스크톱 1440 ──
        pd = b.new_page(viewport={'width': 1440, 'height': 1000})
        c2 = []
        pd.on('console', lambda m: c2.append((m.type, m.text)) if m.type == 'error' else None)
        pd.on('pageerror', lambda e: c2.append(('pageerror', str(e))))
        pd.goto(base, wait_until='load')
        pd.wait_for_selector('.card', timeout=30000)
        pd.fill('#score', '2.5')
        for k, v in [('kor', '1'), ('mat', '2'), ('eng', '1'), ('t1', '1'), ('t2', '2')]:
            pd.fill(f'[data-se="{k}"]', v)
        pd.wait_for_timeout(400)
        check('데스크톱 카드 렌더', pd.locator('.card').count() == N)
        ow2 = pd.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        check('1440px 가로 오버플로 없음', ow2 <= 1, f'{ow2}px')
        pd.screenshot(path=os.path.join(SHOT_DIR, f'{TAG}-susi-dark-desktop-{stamp}.png'))
        check('데스크톱 콘솔 오류 0', len(c2) == 0, c2[:3])
        pd.close()

        # ── 초소형 320 ──
        ps = b.new_page(viewport={'width': 320, 'height': 720})
        ps.goto(base, wait_until='load')
        ps.wait_for_selector('.card', timeout=30000)
        ow3 = ps.evaluate('document.documentElement.scrollWidth - window.innerWidth')
        check('320px 가로 오버플로 없음', ow3 <= 1, f'{ow3}px')
        ps.close()
        b.close()

    if srv:
        srv.shutdown()
    ok = sum(1 for _, r in results if r)
    print(f'\n결과: {ok}/{len(results)} 통과 ({TAG})')
    print('스크린샷:', SHOT_DIR)
    return 0 if ok == len(results) else 1

if __name__ == '__main__':
    sys.exit(main())
