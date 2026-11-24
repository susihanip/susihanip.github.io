# -*- coding: utf-8 -*-
"""정시한입·수시한입 대학별 정적 SEO 페이지(/u/{uid}.html) + sitemap.xml 생성기.

사용(저장소 루트에서):
  python3 tools/build_u_pages.py          # 이 저장소의 /u/ 페이지 + sitemap.xml 재생성
  (대학 목록·학과 데이터가 바뀌면 반드시 다시 실행)

법적 원칙:
  - 요강 PDF·본문을 복제하지 않고 입학처 공식 링크만 연결한다.
  - 대학 로고·상표 이미지를 쓰지 않는다(텍스트 사실 정보만).
  - 모든 페이지에 "전년도 70% 컷 참고용 / 최종 지원 전 입학처 요강 확인" 면책 문구를 둔다.
"""
import json
import os
import sys
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SELF_SITE = "jeongsihanip" if "jeongsihanip" in os.path.basename(REPO_ROOT) else "susihanip"

BASE_SITES = {
    "jeongsihanip": {
        "root": REPO_ROOT,
        "base": "https://jeongsihanip.github.io",
        "brand": "정시한입",
        "handle": "@jeongsihanip",
        "color": "#38BDF8",
        "gold": "#E9C46A",
        "ga": "G-MZ5B4J0HXY",
        "mode": "jeongsi",
        "mode_label": "정시",
        "cut_label": "정시 70% 컷",
        "track_header": "전형",
    },
    "susihanip": {
        "root": REPO_ROOT,
        "base": "https://susihanip.github.io",
        "brand": "수시한입",
        "handle": "@susihanip",
        "color": "#FACC15",
        "gold": "#F59E0B",
        "ga": "G-S9MYLSQM1V",
        "mode": "susi",
        "mode_label": "수시",
        "cut_label": "수시 70% 컷(내신)",
        "track_header": "전형",
    },
}

DISCLAIMER = ("전년도 70% 컷(대입정보포털 ‘어디가’ 공시 · 최종등록자 기준)을 참고용으로 보여드립니다. "
              "학과·반영비율·변환표준점수·수능최저에 따라 결과가 달라지니, 최종 지원 전에는 반드시 "
              "대학 입학처 공식 모집요강을 확인하세요.")
DISCLAIMER_SHORT = "전년도 70% 컷(어디가 공시) 기준 참고용 · 최종 지원 전 대학 입학처 공식 모집요강을 확인하세요."


def esc(s):
    return (str("" if s is None else s)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def num(v):
    """47.0 -> '47', 1.74 -> '1.74'"""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if abs(v - round(v)) < 0.005:
        return str(int(round(v)))
    return ("%.2f" % v).rstrip("0").rstrip(".")


def grade(v):
    """내신 등급 표기: 1.74 / 2"""
    if v is None:
        return None
    return num(v)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def stats_for(mode, cut_entry):
    if not cut_entry:
        return None
    if mode == "jeongsi":
        return cut_entry.get("pct70")
    g, j = cut_entry.get("gyogwa"), cut_entry.get("jonghap")
    return {"gyogwa": g, "jonghap": j, "note": cut_entry.get("note"),
            "suneung": cut_entry.get("suneung_choejeo")}


CSS = """
:root{
  --bg:#09090b;--panel:#141417;--panel2:#18181b;--line:rgba(255,255,255,.11);--line2:rgba(255,255,255,.18);
  --text:#EAF1F8;--body:#cbdcec;--muted:#9FB0C3;--dim:#8295aa;
  --accent:%(accent)s;--gold:%(gold)s;--accent-soft:%(accent_soft)s;--accent-line:%(accent_line)s;
  --btn-ink:#0D1B2A;--chip:rgba(255,255,255,.06);
}
html[data-theme="light"]{
  --bg:#f8fafc;--panel:#ffffff;--panel2:#ffffff;--line:rgba(15,23,42,.12);--line2:rgba(15,23,42,.2);
  --text:#0f172a;--body:#22344a;--muted:#526075;--dim:#64748b;--chip:rgba(15,23,42,.05);
  --accent-soft:%(accent_soft_light)s;--accent-line:%(accent_line_light)s;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:radial-gradient(900px 520px at 50%% -200px, %(glow)s, transparent 70%%),var(--bg);
  color:var(--text);font-family:Pretendard,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;line-height:1.62;word-break:keep-all;overflow-wrap:anywhere;
}
a{color:inherit}
.wrap{width:100%%;max-width:880px;margin:0 auto;padding:0 16px}
header.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%%, transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top-in{display:flex;align-items:center;gap:10px;min-height:56px;padding-top:8px;padding-bottom:8px;flex-wrap:wrap}
.brand{display:inline-flex;align-items:center;gap:8px;text-decoration:none;font-weight:800;font-size:15px;letter-spacing:-.3px}
.brand svg{width:22px;height:22px;flex:0 0 auto}
.brand small{display:block;font-size:10.5px;font-weight:600;color:var(--muted);letter-spacing:-.2px}
@media(max-width:460px){.brand small{display:none}.top-in{min-height:52px}}
.nav{margin-left:auto;display:flex;align-items:center;gap:5px}
.nav a,.nav span{font-size:11.5px;font-weight:700;text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:4px 9px;color:var(--muted);white-space:nowrap}
.nav .on{color:var(--btn-ink);background:var(--accent);border-color:transparent}
.theme{background:none;border:1px solid var(--line);border-radius:999px;color:var(--muted);font:inherit;font-size:11.5px;font-weight:700;padding:4px 9px;cursor:pointer;line-height:1.4}
main{padding:18px 0 40px}
.crumb{font-size:11.5px;color:var(--dim);margin:2px 0 10px;display:flex;gap:6px;flex-wrap:wrap}
.crumb a{text-decoration:none;color:var(--muted)}
h1{font-size:24px;line-height:1.35;letter-spacing:-.7px;margin:0 0 6px}
.sub{color:var(--muted);font-size:13px;margin:0 0 12px}
.badges{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.badge{font-size:11px;font-weight:700;border:1px solid var(--line2);border-radius:999px;padding:3px 9px;color:var(--body)}
.badge.ga{color:#bae6fd;border-color:rgba(56,189,248,.45);background:rgba(56,189,248,.12)}
.badge.na{color:#fde68a;border-color:rgba(233,196,106,.45);background:rgba(233,196,106,.12)}
.badge.da{color:#bbf7d0;border-color:rgba(74,222,128,.45);background:rgba(74,222,128,.12)}
.cta{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}
.btn{display:inline-flex;align-items:center;gap:6px;text-decoration:none;font:inherit;font-size:13px;font-weight:800;border-radius:12px;padding:11px 15px;border:1px solid var(--line2);background:var(--panel2);color:var(--text);cursor:pointer}
.btn.primary{background:var(--accent);border-color:transparent;color:var(--btn-ink);box-shadow:0 6px 18px %(glow)s}
.btn.ghost{background:transparent}
.btn:active{transform:scale(.99)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:14px 14px;margin-bottom:12px}
.card h2{font-size:15px;margin:0 0 10px;letter-spacing:-.3px}
.facts{display:grid;gap:8px;margin:0}
.fact{display:grid;grid-template-columns:64px minmax(0,1fr);gap:8px;font-size:12.5px;align-items:start}
.fact dt{color:var(--dim);font-weight:700;font-size:11.5px;padding-top:1px}
.fact dd{margin:0;color:var(--body)}
.fact dd b{color:var(--text)}
.cutline{display:flex;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:0}
.cutline b{color:var(--text)}
table{width:100%%;border-collapse:collapse;table-layout:fixed;font-size:11.5px}
caption{caption-side:top;text-align:left;font-size:11px;color:var(--dim);padding:0 0 8px;line-height:1.55}
th,td{padding:7px 6px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{font-size:10.5px;color:var(--dim);font-weight:700;background:var(--chip)}
th:first-child,td:first-child{padding-left:8px}
th:last-child,td:last-child{padding-right:8px;text-align:right}
td.n{font-variant-numeric:tabular-nums;font-weight:800;color:var(--text);white-space:nowrap}
td.name{font-weight:700;color:var(--text)}
td.cat{color:var(--dim);font-size:10px;padding-right:8px}
td.tk{color:var(--muted);font-size:10.5px}
td .sp{color:var(--dim);font-size:9.5px;border:1px solid var(--line);border-radius:999px;padding:0 4px;margin-left:3px}
tr.grp td{border-bottom:1px solid var(--line2)}
.empty{font-size:12px;color:var(--muted);margin:0}
.links{display:grid;gap:8px}
.links a{display:flex;align-items:center;justify-content:space-between;gap:8px;text-decoration:none;font-size:12.5px;font-weight:700;border:1px solid var(--line);border-radius:12px;padding:10px 12px;background:var(--panel2)}
.links a span.k{color:var(--muted);font-weight:600;font-size:11px}
.others{display:flex;gap:6px;flex-wrap:wrap}
.others a{font-size:11.5px;font-weight:700;text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:5px 10px;color:var(--body);background:var(--chip)}
.note{font-size:11px;line-height:1.65;color:var(--dim);margin:8px 0 0}
.disc{border:1px dashed var(--line2);border-radius:12px;padding:11px 12px;font-size:11px;line-height:1.65;color:var(--muted);background:var(--chip)}
footer{border-top:1px solid var(--line);padding:16px 0 30px;font-size:11px;color:var(--dim);line-height:1.7}
footer a{color:var(--muted);text-decoration:none}
.toast{position:fixed;left:50%%;bottom:22px;transform:translateX(-50%%) translateY(10px);opacity:0;transition:.2s;background:var(--accent);color:var(--btn-ink);font-size:12px;font-weight:800;padding:9px 15px;border-radius:999px;pointer-events:none;z-index:50}
.toast.on{opacity:1;transform:translateX(-50%%)}
@media(max-width:420px){
  h1{font-size:21px}
  .fact{grid-template-columns:56px minmax(0,1fr)}
  th,td{padding:6px 5px}
  table{font-size:11px}
}
"""


def page_css(cfg):
    if cfg["mode"] == "jeongsi":
        accent, gold = "#38BDF8", "#E9C46A"
        accent_soft = "rgba(56,189,248,.12)"
        accent_line = "rgba(56,189,248,.34)"
        accent_soft_light = "rgba(2,132,199,.10)"
        accent_line_light = "rgba(2,132,199,.28)"
        glow = "rgba(56,189,248,.16)"
    else:
        accent, gold = "#FACC15", "#F59E0B"
        accent_soft = "rgba(250,204,21,.14)"
        accent_line = "rgba(250,204,21,.36)"
        accent_soft_light = "rgba(202,138,4,.12)"
        accent_line_light = "rgba(202,138,4,.30)"
        glow = "rgba(250,204,21,.14)"
    return CSS % {
        "accent": accent, "gold": gold, "accent_soft": accent_soft, "accent_line": accent_line,
        "accent_soft_light": accent_soft_light, "accent_line_light": accent_line_light, "glow": glow,
    }


def mark_svg(cfg):
    if cfg["mode"] == "jeongsi":
        return ('<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 2.5 7.5 12 12l9.5-4.5L12 3Z" fill="#38BDF8"/>'
                '<path d="M6 11.4v4.3C6 17.6 8.7 19 12 19s6-1.4 6-3.3v-4.3l-6 2.8-6-2.8Z" fill="#E9C46A"/></svg>')
    return ('<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 2.5 7.5 12 12l9.5-4.5L12 3Z" fill="#FACC15"/>'
            '<path d="M6 11.4v4.3C6 17.6 8.7 19 12 19s6-1.4 6-3.3v-4.3l-6 2.8-6-2.8Z" fill="#F59E0B"/></svg>')


def dept_rows(mode, entry):
    if not entry:
        return []
    key = "j" if mode == "jeongsi" else "s"
    return entry.get(key) or []


def rep_cut(mode, tracks):
    """학과 대표 컷: 일반전형 중 가장 높은(정시 백분위)/가장 낮은(수시 등급) 값."""
    vals_general, vals_special = [], []
    for t in tracks:
        cut = t[3] if len(t) > 3 else None
        if cut is None:
            continue
        if len(t) > 1 and t[1]:
            vals_special.append(cut)
        else:
            vals_general.append(cut)
    pool = vals_general or vals_special
    if not pool:
        return None
    return max(pool) if mode == "jeongsi" else min(pool)


def quota_sum(tracks):
    q = 0.0
    for t in tracks:
        if len(t) > 2 and isinstance(t[2], (int, float)):
            q += t[2]
    return q or None


def other_universities(all_unis, u, limit=12):
    same = [x for x in all_unis if x.get("region") == u.get("region") and x["id"] != u["id"]]
    out = same[:limit]
    if len(out) < 6:
        for x in all_unis:
            if x["id"] != u["id"] and x not in out:
                out.append(x)
            if len(out) >= 8:
                break
    return out


def suneung_block(uid, suneung):
    """수시 수능최저: 전형 유형별 기준을 짧게 요약."""
    d = (suneung or {}).get(uid)
    if not d:
        return None
    parts = []
    for kind in ("교과", "종합", "논술"):
        v = d.get(kind)
        if not v:
            continue
        crit = []
        for c in v.get("criteria") or []:
            label = c.get("label") or kind
            if c.get("kind") == "sum":
                crit.append("%s %d합 %s" % (label, c.get("count") or 0, num(c.get("limit"))))
            elif c.get("kind") == "topN":
                crit.append("%s %d개 %s등급" % (label, c.get("count") or 0, num(c.get("limit"))))
            else:
                crit.append("%s %s" % (label, num(c.get("limit"))))
        none = v.get("none") or []
        txt = []
        if crit:
            txt.append(", ".join(crit))
        if none:
            shown = ", ".join(none[:3]) + (" 외" if len(none) > 3 else "")
            txt.append("미적용: " + shown)
        if not txt:
            txt.append("요강 확인")
        parts.append(kind + " · " + " / ".join(txt))
    return " | ".join(parts) if parts else None


def build_page(cfg, u, dept_entry, cut_entry, all_unis, suneung, today):
    mode = cfg["mode"]
    name = u["name"]
    base = cfg["base"]
    url = "%s/u/%s.html" % (base, u["id"])
    rows = dept_rows(mode, dept_entry)
    st = stats_for(mode, cut_entry)

    # ── 요약 수치 ──
    if mode == "jeongsi":
        med = st.get("median") if st else None
        rng = st
    else:
        med = None
        rng = st

    dept_n = len(rows)
    track_n = sum(len(r[2] or []) for r in rows)

    # ── 설명문 ──
    if mode == "jeongsi":
        title = "%s 2027 정시 모집요강 · 학과별 70%% 컷 | 정시한입" % name
        desc_bits = []
        if u.get("group"):
            desc_bits.append("모집군 " + "·".join(u["group"]))
        if u.get("quota"):
            desc_bits.append(u["quota"].split("(")[0].strip())
        if med is not None:
            desc_bits.append("2026 정시 70%% 컷 중위 %s백분위(%s~%s)" % (num(med), num(rng.get("min")), num(rng.get("max"))))
        desc = ("%s 2027학년도 정시 모집요강 요약 — %s. 학과(모집단위) %d곳의 전형·모집인원·70%% 컷을 한 표에 정리했고, "
                "내 수능 백분위로 소신·적정을 바로 계산할 수 있습니다. (정시한입)") % (
                    name, ", ".join(desc_bits) if desc_bits else "모집요강·입학처 공지 정리", dept_n)
    else:
        title = "%s 2027 수시 모집요강 · 학과별 내신 70%% 컷 | 수시한입" % name
        desc_bits = []
        if u.get("types"):
            desc_bits.append("전형 " + "·".join(u["types"]))
        if u.get("quota"):
            desc_bits.append(u["quota"].split("(")[0].strip())
        g = (st or {}).get("gyogwa")
        j = (st or {}).get("jonghap")
        cuts = []
        if g:
            cuts.append("교과 70%% 컷 %s등급" % grade(g.get("median")))
        if j:
            cuts.append("종합 70%% 컷 %s등급" % grade(j.get("median")))
        if cuts:
            desc_bits.append(" / ".join(cuts))
        desc = ("%s 2027학년도 수시 모집요강 요약 — %s. 학과(모집단위) %d곳의 전형·모집인원·내신 70%% 컷과 "
                "수능최저학력기준을 한눈에 정리했습니다. (수시한입)") % (
                    name, ", ".join(desc_bits) if desc_bits else "모집요강·입학처 공지 정리", dept_n)

    # ── 사실 정보 ──
    facts = []
    if mode == "jeongsi":
        if u.get("group"):
            facts.append(("모집군", " · ".join(u["group"])))
    else:
        if u.get("types"):
            facts.append(("전형", " · ".join(u["types"])))
    if u.get("quota"):
        facts.append(("모집인원", u["quota"]))
    if u.get("schedule"):
        facts.append(("원서접수", u["schedule"]))
    if u.get("summary"):
        facts.append(("전형 요약", u["summary"]))
    if u.get("campus"):
        facts.append(("캠퍼스", u["campus"]))

    facts_html = "".join(
        '<div class="fact"><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v)) for k, v in facts
    )

    # ── 70% 컷 요약 줄 ──
    if mode == "jeongsi":
        if st and st.get("median") is not None:
            cutline = ('<p class="cutline"><span>2026 정시 70%% 컷 중위 <b>%s</b>백분위</span>'
                       '<span>공개 모집단위 <b>%s~%s</b> · %s개</span></p>') % (
                num(st.get("median")), num(st.get("min")), num(st.get("max")), num(st.get("n")))
        else:
            cutline = '<p class="cutline"><span>어디가 공시 70% 컷 자료가 없어 자동 비교가 되지 않습니다. 입학처 입시결과를 확인하세요.</span></p>'
    else:
        g = (st or {}).get("gyogwa")
        j = (st or {}).get("jonghap")
        bits = []
        if g:
            bits.append('<span>학생부교과 70%% 컷 <b>%s</b>등급 (%s~%s · %s개)</span>' % (
                grade(g.get("median")), grade(g.get("min")), grade(g.get("max")), num(g.get("n"))))
        if j:
            bits.append('<span>학생부종합 70%% 컷 <b>%s</b>등급 (%s~%s · %s개)</span>' % (
                grade(j.get("median")), grade(j.get("min")), grade(j.get("max")), num(j.get("n"))))
        if not bits:
            bits.append("<span>어디가 공시 내신 70% 컷 자료가 없습니다. 입학처 입시결과를 확인하세요.</span>")
        cutline = '<p class="cutline">' + "".join(bits) + "</p>"

    # ── 학과 표 ──
    if rows:
        trs = []
        for r in rows:
            dept_name, cat = r[0], r[1]
            tracks = r[2] or []
            cat_name = {"m": "문과", "i": "이공계", "s": "의약·보건", "e": "사범·교육",
                        "a": "예체능", "f": "자유전공", "x": "기타"}.get(cat, "기타")
            if not tracks:
                trs.append('<tr><td class="name">%s</td><td class="cat">%s</td><td class="tk">-</td><td class="n">-</td></tr>'
                           % (esc(dept_name), esc(cat_name)))
                continue
            for i, t in enumerate(tracks):
                tk = t[0]
                special = bool(len(t) > 1 and t[1])
                cut = t[3] if len(t) > 3 else None
                cut_txt = grade(cut) if mode == "susi" else num(cut)
                if cut_txt is None:
                    cut_txt = "미공개"
                sp = '<span class="sp">특별</span>' if special else ""
                cls = ' class="grp"' if i == 0 else ""
                trs.append('<tr%s><td class="name">%s</td><td class="cat">%s</td><td class="tk">%s%s</td><td class="n">%s</td></tr>'
                           % (cls, esc(dept_name) if i == 0 else '<span style="color:var(--dim);font-weight:600">〃</span>',
                              esc(cat_name) if i == 0 else "",
                              esc(tk), sp, esc(cut_txt)))
        table_html = (
            '<table><caption>%s 학과(모집단위)별 전형·70%% 컷 — 2026학년도 %s 최종등록자 기준(어디가 공시). '
            '‘〃’는 바로 위 학과와 같은 모집단위입니다.</caption>'
            '<thead><tr><th style="width:36%%">모집단위</th><th style="width:16%%">계열</th>'
            '<th style="width:29%%">%s</th><th style="width:19%%">70%% 컷</th></tr></thead><tbody>%s</tbody></table>'
        ) % (esc(name), "정시" if mode == "jeongsi" else "수시", "전형", "".join(trs))
    else:
        table_html = '<p class="empty">이 대학의 학과(모집단위) 상세 데이터가 아직 등록되지 않았습니다. 입학처 모집요강에서 모집단위를 확인하세요.</p>'

    dnote = (dept_entry or {}).get("note") or (dept_entry or {}).get("nj")
    if dnote:
        table_html += '<p class="note">※ %s</p>' % esc(dnote)

    # ── 공식 링크 ──
    links = []
    if u.get("noticeUrl"):
        links.append('<a href="%s" target="_blank" rel="noopener nofollow"><span>🏛️ 입학처 공지 · 모집요강 안내</span><span class="k">공식 원문</span></a>' % esc(u["noticeUrl"]))
    if u.get("pdfUrl"):
        links.append('<a href="%s" target="_blank" rel="noopener nofollow"><span>📄 2027 모집요강 PDF (입학처 원본)</span><span class="k">공식 원문</span></a>' % esc(u["pdfUrl"]))
    if u.get("shortsUrl"):
        links.append('<a href="%s" target="_blank" rel="noopener"><span>▶ 1분 요약 쇼츠로 보기</span><span class="k">%s</span></a>' % (esc(u["shortsUrl"]), esc(cfg["handle"])))
    links_html = "".join(links) if links else '<p class="empty">공식 링크가 아직 등록되지 않았습니다.</p>'

    # ── 다른 대학 ──
    others = other_universities(all_unis, u)
    others_html = "".join('<a href="./%s.html">%s</a>' % (esc(x["id"]), esc(x["name"])) for x in others)

    # ── 수능최저(수시) ──
    extra_section = ""
    if mode == "susi":
        se = suneung_block(u["id"], suneung)
        if se:
            extra_section = ('<section class="card"><h2>수능최저학력기준</h2>'
                             '<p class="cutline">%s</p>'
                             '<p class="note">전형·모집단위·계열별로 기준이 달라요. 탐구 반영 과목 수와 영어·한국사 조건은 %s 2027 모집요강 원문에서 확인하세요.</p></section>'
                             % (esc(se), esc(name)))
        else:
            extra_section = ('<section class="card"><h2>수능최저학력기준</h2>'
                             '<p class="empty">어디가 공시 전형별 주요사항에 수능최저 정보가 없습니다. 일부 전형은 수능최저를 적용하지 않거나, 요강 원문 확인이 필요합니다.</p></section>')

    calclink = "%s/?u=%s" % (base, u["id"])
    css = page_css(cfg)
    svg = mark_svg(cfg)

    og_img = "%s/og/%s-og.png" % (base, cfg["brand"] if False else ("jeongsihanip" if mode == "jeongsi" else "susihanip"))
    og_img = "%s/og/og-%s.png" % (base, "jeongsi" if mode == "jeongsi" else "susi")

    nav = ('<nav class="nav" aria-label="모집 시기 전환">'
           '<a class="%s" href="https://jeongsihanip.github.io/">정시</a>'
           '<a class="%s" href="https://susihanip.github.io/">수시</a>'
           '<a href="https://ipsihanip.github.io/">대문</a></nav>') % (
        "on" if mode == "jeongsi" else "", "on" if mode == "susi" else "")

    jsonld = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "%s 2027 %s 모집요강" % (name, "정시" if mode == "jeongsi" else "수시"),
        "url": url,
        "description": desc,
        "inLanguage": "ko",
        "isPartOf": {"@type": "WebSite", "name": cfg["brand"], "url": base + "/"},
        "about": {"@type": "CollegeOrUniversity", "name": name},
        "dateModified": today,
    }

    html = """<!DOCTYPE html>
<html lang="ko" data-theme="dark">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<meta name="theme-color" content="#09090b" id="meta-theme" />
<link rel="canonical" href="{url}" />
<meta name="robots" content="index,follow,max-image-preview:large" />
<meta property="og:type" content="article" />
<meta property="og:title" content="{ogtitle}" />
<meta property="og:description" content="{ogdesc}" />
<meta property="og:url" content="{url}" />
<meta property="og:site_name" content="{brand}" />
<meta property="og:locale" content="ko_KR" />
<meta property="og:image" content="{ogimg}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{ogtitle}" />
<meta name="twitter:description" content="{ogdesc}" />
<meta name="twitter:image" content="{ogimg}" />
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='24' fill='%230D1B2A'/%3E%3Cpath d='M50 26 18 40l32 14 32-14z' fill='%23{icon1}'/%3E%3Cpath d='M30 50v14c0 6 9 10 20 10s20-4 20-10V50l-20 9z' fill='%23{icon2}'/%3E%3C/svg%3E" />
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" />
<style>{css}</style>
<script type="application/ld+json">{jsonld}</script>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={ga}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{ga}');
</script>
</head>
<body>
<header class="top">
  <div class="wrap top-in">
    <a class="brand" href="{base}/" aria-label="{brand} 홈으로">
      {svg}
      <span>{brand}<small>대학별 2027 {modelabel}모집요강</small></span>
    </a>
    {nav}
    <button type="button" class="theme" id="theme-btn" aria-label="라이트/다크 테마 전환" title="라이트/다크 테마 전환">☀</button>
  </div>
</header>

<main class="wrap">
  <p class="crumb"><a href="{base}/">{brand}</a> <span>›</span> <a href="{base}/">대학별 {modelabel}모집요강</a> <span>›</span> <span>{name}</span></p>
  <h1>{name} 2027 {modelabel} 모집요강</h1>
  <p class="sub">{sub}</p>
  <div class="badges">{badges}</div>

  <div class="cta">
    <a class="btn primary" href="{calclink}">내 점수로 소신·적정 계산하기 →</a>
    <button type="button" class="btn ghost" id="copy-btn">🔗 링크 복사</button>
  </div>

  <section class="card">
    <h2>{name} {modelabel} 모집요강 핵심 요약</h2>
    <dl class="facts">{facts}</dl>
    <div style="margin-top:11px">{cutline}</div>
  </section>

  <section class="card">
    <h2>학과(모집단위)별 전형 · 70% 컷</h2>
    {table}
    <p class="note">학과 {deptn}곳 · 전형 {trackn}개를 정리했습니다.</p>
  </section>

  {extra}

  <section class="card">
    <h2>공식 자료 · 원문 확인</h2>
    <div class="links">{links}</div>
    <p class="note">요강 PDF는 복제·재배포하지 않고 대학 입학처 원본 링크로만 연결합니다.</p>
  </section>

  <section class="card">
    <h2>같은 지역 다른 대학</h2>
    <div class="others">{others}</div>
    <p class="note"><a href="{base}/" style="color:var(--accent)">전체 196개 대학 {modelabel}모집요강 보기 →</a></p>
  </section>

  <p class="disc">{disc}</p>
</main>

<footer class="wrap">
  <p>{brand}({handle}) · 대학별 2027 {modelabel}모집요강 · 기준일 {today}</p>
  <p>자료 출처: 대입정보포털 ‘어디가’(KCUE) 전형 평가기준 및 전년도 결과공개, 각 대학 입학처 공지. 본 사이트는 대학 공식 사이트가 아니며, 대학 로고·요강 PDF를 사용하지 않습니다.</p>
  <p><a href="{base}/">{brand} 홈</a> · <a href="https://ipsihanip.github.io/">입시한입 대문</a> · <a href="https://www.youtube.com/{handle}">{handle} 유튜브</a></p>
</footer>
<div class="toast" id="toast">링크를 복사했어요</div>
<script>
(function () {{
  var KEY = "hanip-theme";
  var root = document.documentElement;
  var btn = document.getElementById("theme-btn");
  function apply(t) {{
    root.setAttribute("data-theme", t);
    btn.textContent = t === "light" ? "🌙" : "☀";
    var m = document.getElementById("meta-theme");
    if (m) m.setAttribute("content", t === "light" ? "#f8fafc" : "#09090b");
  }}
  var saved = null;
  try {{ saved = localStorage.getItem(KEY); }} catch (e) {{}}
  apply(saved === "light" ? "light" : "dark");
  btn.addEventListener("click", function () {{
    var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    apply(next);
    try {{ localStorage.setItem(KEY, next); }} catch (e) {{}}
  }});
  var toast = document.getElementById("toast");
  function showToast(msg) {{
    toast.textContent = msg;
    toast.classList.add("on");
    setTimeout(function () {{ toast.classList.remove("on"); }}, 1800);
  }}
  document.getElementById("copy-btn").addEventListener("click", function () {{
    var url = location.href;
    function done() {{ showToast("링크를 복사했어요"); }}
    function fallback() {{
      var ta = document.createElement("textarea");
      ta.value = url; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.top = "-1000px";
      document.body.appendChild(ta); ta.select();
      try {{ document.execCommand("copy"); done(); }} catch (e) {{ showToast("주소창의 링크를 복사해 주세요"); }}
      document.body.removeChild(ta);
    }}
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(url).then(done, fallback);
    }} else {{ fallback(); }}
  }});
}})();
</script>
</body>
</html>
"""

    icon1 = "38BDF8" if mode == "jeongsi" else "FACC15"
    icon2 = "E9C46A" if mode == "jeongsi" else "F59E0B"
    badges = []
    if mode == "jeongsi":
        cls = {"가군": "ga", "나군": "na", "다군": "da"}
        for g in u.get("group") or []:
            badges.append('<span class="badge %s">%s</span>' % (cls.get(g, ""), esc(g)))
    else:
        for t in u.get("types") or []:
            badges.append('<span class="badge">%s</span>' % esc(t))
    if u.get("region"):
        badges.append('<span class="badge">%s</span>' % esc(u["region"]))
    if u.get("campus"):
        badges.append('<span class="badge">%s</span>' % esc(u["campus"]))
    if mode == "jeongsi" and st and st.get("median") is not None:
        badges.append('<span class="badge">70%% 컷 중위 %s</span>' % num(st.get("median")))
    if mode == "susi" and st and st.get("gyogwa") and st["gyogwa"].get("median") is not None:
        badges.append('<span class="badge">교과 70%% 컷 %s등급</span>' % grade(st["gyogwa"]["median"]))

    ogtitle = title.split(" | ")[0]
    ogdesc = desc[:110] + ("…" if len(desc) > 110 else "")
    sub = " · ".join([x for x in [u.get("campus"), u.get("region")] if x])
    if mode == "jeongsi" and u.get("summary"):
        sub = (sub + " · " if sub else "") + u["summary"][:70]
    elif mode == "susi" and u.get("summary"):
        sub = (sub + " · " if sub else "") + u["summary"][:70]

    return html.format(
        title=esc(title), desc=esc(desc), url=url, ogtitle=esc(ogtitle), ogdesc=esc(ogdesc),
        ogimg=esc(og_img), brand=esc(cfg["brand"]), handle=esc(cfg["handle"]),
        css=css, jsonld=json.dumps(jsonld, ensure_ascii=False), ga=cfg["ga"],
        base=base, svg=svg, nav=nav, name=esc(name), modelabel=cfg["mode_label"],
        sub=esc(sub), badges="".join(badges), calclink=esc(calclink), facts=facts_html,
        cutline=cutline, table=table_html, extra=extra_section, links=links_html,
        others=others_html, disc=esc(DISCLAIMER), today=today,
        deptn=dept_n, trackn=track_n, icon1=icon1, icon2=icon2,
    )


def write_sitemap(cfg, unis, today):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
             '  <url>',
             '    <loc>%s/</loc>' % cfg["base"],
             '    <lastmod>%s</lastmod>' % today,
             '    <changefreq>daily</changefreq>',
             '    <priority>1.0</priority>',
             '  </url>']
    for u in unis:
        lines += ['  <url>',
                  '    <loc>%s/u/%s.html</loc>' % (cfg["base"], u["id"]),
                  '    <lastmod>%s</lastmod>' % today,
                  '    <changefreq>weekly</changefreq>',
                  '    <priority>0.8</priority>',
                  '  </url>']
    lines.append('</urlset>')
    path = os.path.join(cfg["root"], "sitemap.xml")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(unis) + 1


def build(site, today=None):
    cfg = BASE_SITES[site]
    today = today or date.today().isoformat()
    root = cfg["root"]
    udata = load(os.path.join(root, "data", "universities.json"))
    unis = udata["universities"]
    ddata = load(os.path.join(root, "data", "depts.json"))
    depts = ddata["universities"]
    cuts = load(os.path.join(root, "data", "cutoffs.json"))["universities"]
    suneung = {}
    sp = os.path.join(root, "data", "suneung.json")
    if os.path.exists(sp):
        suneung = load(sp)

    outdir = os.path.join(root, "u")
    os.makedirs(outdir, exist_ok=True)
    # 이전에 만든 파일 정리(대학 목록에서 빠진 것)
    keep = set(u["id"] + ".html" for u in unis)
    removed = 0
    for fn in os.listdir(outdir):
        if fn.endswith(".html") and fn not in keep:
            os.remove(os.path.join(outdir, fn))
            removed += 1

    total_bytes = 0
    for u in unis:
        html = build_page(cfg, u, depts.get(u["id"]), cuts.get(u["id"]), unis, suneung, today)
        p = os.path.join(outdir, u["id"] + ".html")
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
        total_bytes += len(html.encode("utf-8"))
    n_urls = write_sitemap(cfg, unis, today)
    print("[%s] /u/ pages: %d (removed %d) · sitemap urls: %d · html %.1f MB" % (
        site, len(unis), removed, n_urls, total_bytes / 1024 / 1024))


if __name__ == "__main__":
    targets = [t for t in sys.argv[1:] if t in BASE_SITES] or [SELF_SITE]
    for t in targets:
        build(t)
