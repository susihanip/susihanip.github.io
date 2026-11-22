(function () {
  var state = {
    items: [], cuts: {}, sunj: {},
    q: "", type: "전체", region: "전체", sort: "추천순", band: "전체",
    track: "gyogwa", grade: null,
    seMode: "subject", se: { kor: null, mat: null, eng: null, t1: null, t2: null },
    seN: 2, seVal: null,
    ready: false
  };
  var listEl = document.getElementById("list");
  var countEl = document.getElementById("count");
  var qEl = document.getElementById("q");
  var clearEl = document.getElementById("clear");
  var scoreEl = document.getElementById("score");
  var scoreClear = document.getElementById("score-clear");
  var bandWrap = document.getElementById("band-filters");
  var scoreSum = document.getElementById("score-sum");
  var legendEl = document.getElementById("legend");
  var seSubjEl = document.getElementById("se-subj");
  var seSumEl = document.getElementById("se-sum");
  var seNEl = document.getElementById("se-n");
  var seValEl = document.getElementById("se-val");

  var TYPE_CLASS = { "학생부교과": "", "학생부종합": "t2", "논술": "t3" };
  var TRACK_NAME = { gyogwa: "학생부교과", jonghap: "학생부종합" };
  var TRACK_KEY = { gyogwa: "교과", jonghap: "종합" };
  var BAND_RANK = { "안정": 0, "적정": 1, "소신": 2, "어려움": 3, "미등록": 4 };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(v) { return v == null ? "-" : (Math.round(v * 100) / 100).toFixed(2); }
  function f1(v) { return (Math.round(v * 10) / 10).toFixed(1); }
  function gapTxt(v) {
    var a = Math.abs(v);
    return (Math.abs(a - Math.round(a)) < 0.005 ? String(Math.round(a)) : fmt(a)) + "등급";
  }

  /* ── 입결 컷 데이터 ── */
  function cutOf(u) {
    var c = state.cuts[u.id];
    if (!c) return null;
    if (c.susi) c = c.susi;
    if (!c.gyogwa && !c.jonghap) return null;
    return c;
  }
  function trackCut(u) {
    var c = cutOf(u);
    if (!c) return null;
    return c[state.track] || null;
  }
  function cutNote(u, key) {
    var c = state.cuts[u.id];
    if (!c) return null;
    if (c.susi) c = c.susi;
    if (key && c[key]) return c[key];
    return c.note || null;
  }
  function bandOf(u) {
    if (state.grade == null) return null;
    var c = trackCut(u);
    if (!c) return "미등록";
    var g = state.grade;
    if (g <= c.p20) return "안정";
    if (g <= c.median) return "적정";
    if (g <= c.max) return "소신";
    return "어려움";
  }
  function bandClass(b) {
    return b === "안정" ? "b-stable" : b === "적정" ? "b-fit" : b === "소신" ? "b-bold" : b === "어려움" ? "b-hard" : "b-none";
  }

  /* ── 수능 등급 입력 ── */
  function gradeVal(v) {
    var n = parseFloat(v);
    if (!isFinite(n) || n <= 0) return null;
    return Math.min(Math.max(n, 1), 9);
  }
  function hasSe() {
    if (state.seMode === "sum") return state.seVal != null;
    var s = state.se;
    return s.kor != null || s.mat != null || s.eng != null || s.t1 != null || s.t2 != null;
  }
  function seAreas() {
    var s = state.se, out = [];
    if (s.kor != null) out.push({ k: "국", v: s.kor });
    if (s.mat != null) out.push({ k: "수", v: s.mat });
    if (s.eng != null) out.push({ k: "영", v: s.eng });
    var t = null;
    if (s.t1 != null && s.t2 != null) t = Math.min(s.t1, s.t2);
    else if (s.t1 != null) t = s.t1;
    else if (s.t2 != null) t = s.t2;
    if (t != null) out.push({ k: "탐", v: t });
    return out;
  }
  /* n개 영역 최고 등급합 (수학 필수 / 국·수 중 1개 포함 조건 반영) */
  function bestCombo(areas, n, flags) {
    if (areas.length < n) return null;
    var best = null;
    var pick = [];
    function ok(picks) {
      if (!flags) return true;
      var has = function (k) { return picks.some(function (p) { return p.k === k; }); };
      if (flags.math === "require" && !has("수")) return false;
      if (flags.math === "korormath" && !has("국") && !has("수")) return false;
      return true;
    }
    function rec(start) {
      if (pick.length === n) {
        if (!ok(pick)) return;
        var sum = pick.reduce(function (a, p) { return a + p.v; }, 0);
        if (!best || sum < best.sum) best = { sum: sum, picks: pick.slice() };
        return;
      }
      for (var i = start; i < areas.length; i++) {
        pick.push(areas[i]); rec(i + 1); pick.pop();
      }
    }
    rec(0);
    return best;
  }
  function shortLabel(l) {
    if (!l) return "";
    l = l.replace(/\s*\([^)]*외\)$/, "").replace(/\s+/g, " ").trim();
    return l.length > 15 ? l.slice(0, 14) + "…" : l;
  }
  function critText(c) {
    var lab = c.label ? "(" + shortLabel(c.label) + ")" : "";
    if (c.kind === "sum") {
      if (c.count === 1) return "1개 영역 " + c.limit + "등급 이내" + lab;
      return c.count + "개 영역 합 " + c.limit + lab;
    }
    return c.limit + "등급 " + c.count + "개 이상" + lab;
  }
  function critExtra(c) {
    var f = c.flags || {}, out = [];
    if (f.math === "require") out.push("수학 필수");
    if (f.math === "korormath") out.push("국·수 중 1개 포함");
    if (f.hanguksa) out.push("한국사 " + f.hanguksa + "등급");
    return out.length ? " · " + out.join(" · ") : "";
  }
  function evalCrit(c) {
    if (c.kind === "topN") {
      var ar = seAreas();
      if (!ar.length) return { s: "na" };
      if (state.seMode === "sum") return { s: "na" };
      var cnt = 0;
      ar.forEach(function (a) { if (a.v <= c.limit) cnt++; });
      return { s: cnt >= c.count ? "met" : "miss", gap: c.count - cnt, mine: c.limit + "등급 " + cnt + "개" };
    }
    if (c.kind !== "sum") return { s: "na", why: "subjects" };
    if (state.seMode === "sum") {
      if (state.seVal == null) return { s: "na", why: "count", need: c.count };
      if (state.seN !== c.count) return { s: "na", why: "count", need: c.count };
      var d = state.seVal - c.limit;
      return { s: d <= 0 ? "met" : "miss", gap: d, mine: String(state.seVal), combo: null };
    }
    var combo = bestCombo(seAreas(), c.count, c.flags || {});
    if (!combo) return { s: "na", why: "subjects", need: c.count };
    var diff = combo.sum - c.limit;
    return { s: diff <= 0 ? "met" : "miss", gap: diff, mine: combo.sum, combo: combo.picks };
  }
  function comboText(r) {
    if (!r.combo || !r.combo.length) return "";
    return " (" + r.combo.map(function (p) { return p.k + " " + p.v; }).join("·") + ")";
  }
  function sunOf(u) {
    var s = state.sunj[u.id];
    if (!s) return null;
    return s[TRACK_KEY[state.track]] || null;
  }
  /* 판정: met / miss / none(최저 미적용) / unknown(적용·수치 미확인) / nodata / noinput */
  function judge(u) {
    var d = sunOf(u);
    if (!d) return { s: "nodata", d: null };
    var crit = d.criteria || [];
    var gen = [], nar = [];
    crit.forEach(function (c) { (c.narrow ? nar : gen).push(c); });
    var hasNone = !!(d.none && d.none.length);
    var hasApplied = !!(d.applied && d.applied.length);
    if (!hasSe()) {
      if (crit.length) return { s: "noinput", d: d };
      if (hasNone) return { s: "none", d: d };
      if (hasApplied) return { s: "unknown", d: d };
      return { s: "nodata", d: d };
    }
    function run(list) {
      var met = [], miss = [], na = [];
      list.forEach(function (c) {
        var r = evalCrit(c);
        r.c = c;
        if (r.s === "met") met.push(r);
        else if (r.s === "miss") miss.push(r);
        else na.push(r);
      });
      return { met: met, miss: miss, na: na };
    }
    if (gen.length) {
      var g = run(gen);
      if (g.met.length) return { s: "met", best: g.met[0], d: d, nar: nar };
      if (g.miss.length) {
        g.miss.sort(function (a, b) { return a.gap - b.gap; });
        return { s: "miss", closest: g.miss[0], d: d, na: g.na.length, nar: nar };
      }
      if (g.na.length) return { s: "unknown", d: d, naOnly: true, reasons: g.na };
    }
    if (nar.length) {
      var n = run(nar);
      if (hasNone) {
        var nm = n.met.length ? n.met[0] : null;
        var nx = n.miss.length ? n.miss.sort(function (a, b) { return a.gap - b.gap; })[0] : null;
        return { s: "none", d: d, narrowMet: nm, narrowMiss: nx };
      }
      if (n.met.length) return { s: "met", best: n.met[0], d: d, narrowOnly: true };
      if (n.miss.length) {
        n.miss.sort(function (a, b) { return a.gap - b.gap; });
        return { s: "unknown", d: d, narrowMiss: n.miss[0] };
      }
    }
    if (hasNone) return { s: "none", d: d };
    if (hasApplied) return { s: "unknown", d: d };
    return { s: "nodata", d: d };
  }

  /* ── 사유 문장 ── */
  function gradeLine(u) {
    var c = trackCut(u);
    var g = state.grade;
    if (!c || g == null) return null;
    if (g <= c.p20) return "내 " + fmt(g) + " vs 상위 20% 컷 " + fmt(c.p20) + " → " + gapTxt(c.p20 - g) + " 여유 (중위 " + fmt(c.median) + " 대비 " + gapTxt(c.median - g) + " 여유)";
    if (g <= c.median) return "내 " + fmt(g) + " vs 중위 컷 " + fmt(c.median) + " → " + gapTxt(c.median - g) + " 여유 (상위 20% 컷 " + fmt(c.p20) + "보다 " + gapTxt(g - c.p20) + " 낮음)";
    if (g <= c.max) return "내 " + fmt(g) + " vs 중위 컷 " + fmt(c.median) + " → " + gapTxt(g - c.median) + " 부족 · 최고 컷 " + fmt(c.max) + " 이내(" + gapTxt(c.max - g) + " 여유)";
    return "내 " + fmt(g) + " vs 최고 컷 " + fmt(c.max) + " → " + gapTxt(g - c.max) + " 초과 (중위 " + fmt(c.median) + " 대비 " + gapTxt(g - c.median) + " 부족)";
  }
  function sunLine(u, j) {
    if (!j) return null;
    if (j.s === "noinput") return "수능 등급을 넣으면 최저 충족 여부까지 판정";
    if (j.s === "nodata") return "수능최저 정보 미등록 — 요강 확인";
    if (j.s === "none") {
      var nm2 = j.d.none.slice(0, 2).map(shortLabel).join(" · ") + (j.d.none.length > 2 ? " 외 " + (j.d.none.length - 2) + "개" : "");
      var base = "수능최저 미적용 전형 있음 — " + nm2;
      if (j.narrowMiss || j.narrowMet) {
        var nc = (j.narrowMet || j.narrowMiss).c;
        base += " · 일부 모집단위는 " + critText(nc) + " 별도 적용";
      }
      return base;
    }
    if (j.s === "unknown") {
      if (j.narrowMiss) return "일부 모집단위만 최저 적용(" + critText(j.narrowMiss.c) + ") — 내 " + (j.narrowMiss.c.kind === "sum" ? j.narrowMiss.c.count + "합 " + j.narrowMiss.mine : j.narrowMiss.mine) + "로는 미달, 대상 모집단위는 요강 확인";
      if (j.naOnly && j.reasons && j.reasons.length) {
        var cnt = j.reasons.filter(function (r) { return r.why === "count"; })[0];
        var sub = j.reasons.filter(function (r) { return r.why === "subjects"; })[0];
        var c0 = (j.d.criteria || [])[0];
        if (cnt) return "이 대학 기준은 " + (cnt.need || 3) + "개 영역 합 " + (c0 ? c0.limit : "-") + " — " + (cnt.need || 3) + "합으로 입력해야 비교돼";
        if (sub) return "과목 " + (sub.need || 2) + "개 이상 입력해야 비교할 수 있어";
      }
      if (j.d.applied && j.d.applied.length) return "수능최저 적용 — 전형별 기준은 요강 확인 (" + j.d.applied.slice(0, 2).map(shortLabel).join(" · ") + ")";
      return "수능최저 기준을 비교할 수 없음 — 요강 확인";
    }
    if (j.s === "met") {
      var b = j.best;
      var s0 = b.c.kind !== "sum" ? "내 " + b.mine : (b.c.count === 1 ? "내 1개 영역 " + b.mine + "등급" + comboText(b) : "내 " + b.c.count + "합 " + b.mine + comboText(b));
      var s = s0 + " → " + critText(b.c) + (j.narrowOnly ? " 기준 충족(일부 모집단위)" : " 기준 충족");
      if (b.gap < 0) s += " (" + gapTxt(b.gap) + " 여유)";
      if (j.d && j.d.none && j.d.none.length) s += " · 최저 없는 전형: " + j.d.none.slice(0, 2).map(shortLabel).join("·") + (j.d.none.length > 2 ? " 외" : "");
      return s + critExtra(b.c);
    }
    if (j.s === "miss") {
      var m = j.closest;
      var m0 = m.c.kind !== "sum" ? "내 " + m.mine : (m.c.count === 1 ? "내 1개 영역 " + m.mine + "등급" + comboText(m) : "내 " + m.c.count + "합 " + m.mine + comboText(m));
      var t = m0 + " → " + critText(m.c) + " 기준 미충족 (" + gapTxt(m.gap) + " 부족)";
      if (j.nar && j.nar.length) t += " · 일부 모집단위는 별도 기준(" + critText(j.nar[0]) + ")";
      if (j.d && j.d.none && j.d.none.length) t += " · 최저 없는 전형: " + j.d.none.slice(0, 2).map(shortLabel).join("·") + (j.d.none.length > 2 ? " 외" : "");
      return t + critExtra(m.c);
    }
    return null;
  }
  function verdict(u, band, j) {
    var c = trackCut(u);
    var other = state.track === "gyogwa" ? "jonghap" : "gyogwa";
    var otherCut = (function () {
      var cc = cutOf(u);
      if (!cc) return null;
      return cc[other] || null;
    })();
    if (!c) {
      var note = cutNote(u, state.track === "gyogwa" ? "gyogwa_note" : "jonghap_note") || cutNote(u);
      var shortNote = note && note.length > 46 ? note.slice(0, 44) + "…" : note;
      if (note && note.indexOf("미운영") !== -1) {
        return { tone: "info", text: TRACK_NAME[state.track] + " 전형을 운영하지 않아 — " + TRACK_NAME[other] + " 기준으로 확인해야 해." };
      }
      if (note) return { tone: "info", text: "이 전형 입결이 공개되지 않았어(" + shortNote + "). 정확한 판단은 입학처 요강에서 확인해줘." };
      return { tone: "info", text: "이 전형의 2026학년도 70% 컷이 공개되지 않았어. 입학처 공지·요강에서 확인해줘." };
    }
    var g = state.grade;
    var seMiss = j && j.s === "miss";
    var seMet = j && j.s === "met";
    var seNone = j && j.s === "none";
    var seUnknown = j && (j.s === "nodata" || (j.s === "unknown" && !j.naOnly));
    if (band === "안정" || band === "적정") {
      if (seUnknown) return { tone: "good", text: "내신은 " + band + " 범위야. 다만 이 전형의 수능최저 기준이 공개되지 않아(요강 확인) 최저 충족 여부는 따로 봐야 해." };
      if (seMiss) return { tone: "warn", text: "내신은 " + band + " 범위인데 수능최저를 못 맞추면 그 단계에서 불합격이야. 최저가 없거나 기준이 낮은 전형·학과를 같이 봐야 해." };
      if (seMet) {
        var t0 = j.narrowOnly
          ? "내신은 " + band + " 범위이고 수능최저는 일부 모집단위에만 적용돼. 지원 학과가 그 대상인지 요강에서 확인해줘."
          : "내신·수능최저 모두 기준 안이야. 단, 대학 단위 컷이라 학과별로 ±0.5등급 차이가 크니 지원 학과 컷은 따로 확인해줘.";
        return { tone: "good", text: t0 };
      }
      if (seNone) return { tone: "good", text: "내신은 " + band + " 범위이고, 수능최저 없는 전형이 있어." };
      return { tone: "good", text: "내신은 " + band + " 범위야. 수능 등급까지 넣으면 최저 충족 여부도 판정해 줄게." };
    }
    if (band === "소신") {
      if (seMiss) return { tone: "warn", text: "내신은 최고 컷 이내(소신)지만 수능최저를 못 맞춰. 최저만 충족하면 충분히 노려볼 만해." };
      return { tone: "warn", text: "내신이 중위 컷보다 " + gapTxt(g - c.median) + " 높은 소신 구간이야. 수능최저 충족이 관건이야." };
    }
    if (g > c.max) {
      var extra = otherCut && g <= otherCut.max ? " " + TRACK_NAME[other] + " 기준으로는 최고 컷 " + fmt(otherCut.max) + " 이내라 그쪽은 볼 만해." : "";
      return { tone: "bad", text: "내신이 최고 컷(" + fmt(c.max) + ")보다 " + gapTxt(g - c.max) + " 높아. 이 전형은 어려워." + extra };
    }
    return { tone: "warn", text: "내신이 최고 컷 근처(소신~어려움 경계)야." };
  }

  /* ── 렌더 ── */
  function haystack(u) {
    return [u.name, u.campus, (u.types || []).join(" "), u.quota, u.schedule, u.summary, u.keywords || ""]
      .join(" ").toLowerCase();
  }
  function filtered() {
    var q = state.q.trim().toLowerCase();
    var rows = state.items.filter(function (u) {
      var okType = state.type === "전체" || (u.types || []).indexOf(state.type) !== -1;
      var okRegion = state.region === "전체" || u.region === state.region;
      var okQuery = !q || haystack(u).indexOf(q) !== -1;
      var b = bandOf(u);
      var okBand = state.band === "전체" || b === state.band || b === "미등록";
      return okType && okRegion && okQuery && okBand;
    });
    if (state.sort === "가나다순") {
      rows.sort(function (a, b) { return String(a.name || "").localeCompare(String(b.name || ""), "ko"); });
    } else if (state.grade != null) {
      rows.sort(function (a, b) {
        var ra = BAND_RANK[bandOf(a)] || 0, rb = BAND_RANK[bandOf(b)] || 0;
        if (ra !== rb) return ra - rb;
        var ca = trackCut(a), cb = trackCut(b);
        var da = ca ? Math.abs(ca.median - state.grade) : 99, db = cb ? Math.abs(cb.median - state.grade) : 99;
        return da - db;
      });
    } else if (q) {
      rows.sort(function (a, b) {
        var an = String(a.name || "").toLowerCase().indexOf(q) !== -1 ? 0 : 1;
        var bn = String(b.name || "").toLowerCase().indexOf(q) !== -1 ? 0 : 1;
        return an - bn;
      });
    }
    return rows;
  }

  function extIcon() {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>';
  }

  function cutBlock(u) {
    var b = bandOf(u);
    var c = cutOf(u);
    var shortName = state.track === "gyogwa" ? "교과" : "종합";
    if (!c) {
      return '<div class="cut">' +
        (b ? '<span class="badge b-none">입결 데이터 미등록</span>' : '') +
        '<span class="cut-empty">' + (b ? "직접 확인" : "2026학년도 수시 70% 컷 미공개") + "</span></div>";
    }
    var line = function (label, t) {
      if (!t) return '<span class="cut-main">' + label + ' <span class="cut-sub">70% 컷 미공개</span></span>';
      return '<span class="cut-main">' + label + " <b>" + fmt(t.median) + "</b>등급" +
        ' <span class="cut-sub">' + fmt(t.min) + "~" + fmt(t.max) + " · " + t.n + "개 모집단위</span></span>";
    };
    var badge;
    if (!b) badge = "";
    else if (b === "미등록") badge = '<span class="badge b-none">' + shortName + " 미등록</span>";
    else badge = '<span class="badge ' + bandClass(b) + '">' + esc(b) + "</span>";
    return '<div class="cut">' +
      '<div class="cut-head">' + badge + '<span class="cut-sub">2026 수시 70% 컷(최종등록자)</span></div>' +
      '<div class="cut-lines">' + line("교과", c.gyogwa) + line("종합", c.jonghap) + "</div>" +
      "</div>";
  }

  function whyBlock(u, band) {
    if (state.grade == null && !hasSe()) return "";
    var j = judge(u);
    var g = gradeLine(u);
    var sl = sunLine(u, j);
    var v = verdict(u, band, j);
    var rows = [];
    if (g) rows.push('<div class="why-row"><span class="why-k">내신</span><span class="why-v">' + esc(g) + "</span></div>");
    else if (state.grade != null && !trackCut(u)) {
      var n0 = cutNote(u, state.track === "gyogwa" ? "gyogwa_note" : "jonghap_note") || "";
      rows.push('<div class="why-row"><span class="why-k">내신</span><span class="why-v">' +
        (n0.indexOf("미운영") !== -1 ? esc(TRACK_NAME[state.track]) + " 전형 미운영" : esc(TRACK_NAME[state.track]) + " 입결 컷 없음") +
        "</span></div>");
    }
    if (sl) rows.push('<div class="why-row"><span class="why-k">수능최저</span><span class="why-v">' + esc(sl) + "</span></div>");
    var alt = "";
    if (trackCut(u) == null) {
      var oc = cutOf(u) || {};
      var ocut = oc[state.track === "gyogwa" ? "jonghap" : "gyogwa"];
      if (ocut) alt = '<button type="button" class="why-alt" data-alt-track="' + (state.track === "gyogwa" ? "jonghap" : "gyogwa") + '">' + TRACK_NAME[state.track === "gyogwa" ? "jonghap" : "gyogwa"] + "으로 보기</button>";
    }
    return '<div class="why why-' + v.tone + '">' +
      '<div class="why-rows">' + rows.join("") + "</div>" +
      '<p class="why-verdict">' + esc(v.text) + "</p>" + alt +
      "</div>";
  }

  function card(u) {
    var types = (u.types || []).map(function (t) {
      return '<span class="g ' + (TYPE_CLASS[t] || "") + '">' + esc(t) + "</span>";
    }).join("");

    var solo = !!u.noticeUrl && !u.pdfUrl;
    var links = [];
    if (u.noticeUrl) links.push('<a class="btn notice-link' + (solo ? " solo" : "") + '" href="' + esc(u.noticeUrl) + '" target="_blank" rel="noopener">' +
      (solo ? '<span class="ic" aria-hidden="true">🏛️</span>입학처 공지 바로가기' : "입학처 공지") + extIcon() + "</a>");
    if (u.pdfUrl) links.push('<a class="btn pdf" href="' + esc(u.pdfUrl) + '" target="_blank" rel="noopener">요강 PDF' + extIcon() + "</a>");
    if (u.shortsUrl) links.push('<a class="btn shorts" href="' + esc(u.shortsUrl) + '" target="_blank" rel="noopener">1분 요약 쇼츠 보기' + extIcon() + "</a>");
    else links.push('<span class="btn pending" aria-disabled="true">1분 요약 쇼츠 준비 중</span>');

    var band = bandOf(u);
    return '' +
      '<article class="card" data-id="' + esc(u.id) + '">' +
        '<div class="card-head">' +
          '<div class="card-title">' +
            "<h2>" + esc(u.name) + "</h2>" +
            (u.campus ? '<span class="campus">' + esc(u.campus) + "</span>" : "") +
          "</div>" +
          '<div class="groups">' + types + "</div>" +
        "</div>" +
        cutBlock(u) +
        whyBlock(u, band) +
        '<dl class="facts">' +
          (u.quota ? '<div class="fact"><dt>모집인원</dt><dd>' + esc(u.quota) + "</dd></div>" : "") +
          (u.schedule ? '<div class="fact"><dt>원서접수</dt><dd class="strong">' + esc(u.schedule) + "</dd></div>" : "") +
        "</dl>" +
        (u.summary
          ? '<div class="summary"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 7h16M4 12h10M4 17h13"/></svg><span>' + esc(u.summary) + "</span></div>"
          : "") +
        '<div class="actions' + (solo ? " solo" : "") + '">' + links.join("") + "</div>" +
      "</article>";
  }

  function bandCounts() {
    var n = { "안정": 0, "적정": 0, "소신": 0, "어려움": 0, "미등록": 0 };
    state.items.forEach(function (u) { var b = bandOf(u); if (b) n[b]++; });
    return n;
  }
  function sunCounts() {
    var n = { met: 0, miss: 0, none: 0, unknown: 0, nodata: 0, noinput: 0 };
    if (!hasSe()) return null;
    state.items.forEach(function (u) {
      var j = judge(u);
      if (n[j.s] != null) n[j.s]++;
    });
    return n;
  }

  function updateScoreUI() {
    var on = state.grade != null;
    bandWrap.hidden = !on;
    scoreSum.hidden = !on && !hasSe();
    legendEl.hidden = !on;
    scoreClear.hidden = state.grade == null && !hasSe();
    if (!on) {
      state.band = "전체";
      Array.prototype.forEach.call(bandWrap.querySelectorAll(".chip"), function (c) {
        c.setAttribute("aria-pressed", String(c.dataset.band === "전체"));
      });
    }
    if (!on && !hasSe()) { scoreSum.innerHTML = ""; return; }
    var parts = [];
    if (on) {
      var n = bandCounts();
      parts.push("내신 <b>" + state.grade + "등급</b> · " + esc(TRACK_NAME[state.track]) + " 기준 · " +
        '<span class="pill" style="color:var(--b-stable-fg);border-color:var(--b-stable-bd);background:var(--b-stable-bg)">안정 ' + n["안정"] + "</span> " +
        '<span class="pill" style="color:var(--b-fit-fg);border-color:var(--b-fit-bd);background:var(--b-fit-bg)">적정 ' + n["적정"] + "</span> " +
        '<span class="pill" style="color:var(--b-bold-fg);border-color:var(--b-bold-bd);background:var(--b-bold-bg)">소신 ' + n["소신"] + "</span> " +
        '<span class="pill" style="color:var(--b-hard-fg);border-color:var(--b-hard-bd);background:var(--b-hard-bg)">어려움 ' + n["어려움"] + "</span> " +
        '<span class="pill">입결 미등록 ' + n["미등록"] + "</span>");
    }
    var sc = sunCounts();
    if (sc) {
      var subj = state.seMode === "sum" ? "등급합 " + state.seN + "합 " + state.seVal : "과목별";
      parts.push("수능최저(" + subj + ") · " +
        '<span class="pill" style="color:var(--b-stable-fg);border-color:var(--b-stable-bd);background:var(--b-stable-bg)">충족 ' + sc.met + "</span> " +
        '<span class="pill" style="color:var(--b-hard-fg);border-color:var(--b-hard-bd);background:var(--b-hard-bg)">미충족 ' + sc.miss + "</span> " +
        '<span class="pill">미적용 ' + sc.none + "</span> " +
        '<span class="pill">확인 필요 ' + (sc.unknown + sc.nodata) + "</span>");
    }
    scoreSum.innerHTML = parts.join("<br>");
  }

  function render() {
    if (!state.ready) return;
    var rows = filtered();
    countEl.hidden = false;
    countEl.innerHTML = "총 <b>" + rows.length + "</b>곳" +
      (state.type === "전체" ? "" : " · " + esc(state.type)) +
      (state.region === "전체" ? "" : " · " + esc(state.region)) +
      (state.band === "전체" ? "" : " · " + esc(state.band)) +
      (state.q.trim() ? " · ‘" + esc(state.q.trim()) + "’ 검색" : "") +
      (state.grade != null && state.band !== "전체" ? ' <span style="color:var(--muted)">(입결 미등록 대학은 하단에 별도 표시)</span>' : "");

    if (!rows.length) {
      listEl.innerHTML = '<div class="empty"><b>해당하는 대학이 없어요</b>' +
        (state.q.trim()
          ? "다른 대학명이나 키워드로 검색해 보세요.<br>새 대학은 쇼츠가 올라오면 계속 추가됩니다."
          : (state.grade != null ? "등급을 조금 낮추거나 다른 구간·전형을 선택해 보세요.<br>입결이 공개되지 않은 대학은 ‘입결 데이터 미등록’으로 표시됩니다." : "이 전형으로 등록된 대학이 아직 없습니다.")) + "</div>";
      return;
    }
    listEl.innerHTML = rows.map(card).join("");
  }

  /* ── 이벤트 ── */
  function wireChips(attr, apply) {
    var chips = document.querySelectorAll(".chip[data-" + attr + "]");
    Array.prototype.forEach.call(chips, function (chip) {
      chip.addEventListener("click", function () {
        apply(chip.dataset[attr]);
        Array.prototype.forEach.call(chips, function (c) {
          c.setAttribute("aria-pressed", String(c === chip));
        });
        if (attr === "track") updateScoreUI();
        render();
      });
    });
  }
  wireChips("type", function (v) { state.type = v; });
  wireChips("region", function (v) { state.region = v; });
  wireChips("sort", function (v) { state.sort = v; });
  wireChips("band", function (v) { state.band = v; });

  Array.prototype.forEach.call(document.querySelectorAll("[data-track]"), function (btn) {
    btn.addEventListener("click", function () {
      state.track = btn.dataset.track;
      Array.prototype.forEach.call(document.querySelectorAll("[data-track]"), function (b) {
        b.setAttribute("aria-pressed", String(b === btn));
      });
      updateScoreUI(); render();
    });
  });

  var st = null;
  scoreEl.addEventListener("input", function () {
    clearTimeout(st);
    st = setTimeout(function () {
      var v = parseFloat(scoreEl.value);
      state.grade = (!isFinite(v) || v <= 0) ? null : Math.min(Math.max(v, 1), 9);
      updateScoreUI(); render();
    }, 120);
  });
  scoreClear.addEventListener("click", function () {
    scoreEl.value = ""; state.grade = null; state.band = "전체";
    state.se = { kor: null, mat: null, eng: null, t1: null, t2: null };
    state.seVal = null;
    Array.prototype.forEach.call(document.querySelectorAll("[data-se]"), function (i) { i.value = ""; });
    if (seValEl) seValEl.value = "";
    Array.prototype.forEach.call(bandWrap.querySelectorAll(".chip"), function (c) {
      c.setAttribute("aria-pressed", String(c.dataset.band === "전체"));
    });
    updateScoreUI(); render(); scoreEl.focus();
  });

  // 수능 등급 입력
  Array.prototype.forEach.call(document.querySelectorAll("[data-se]"), function (inp) {
    inp.addEventListener("input", function () {
      state.se[inp.dataset.se] = gradeVal(inp.value);
      updateScoreUI(); render();
    });
  });
  seNEl.addEventListener("change", function () {
    state.seN = parseInt(seNEl.value, 10) || 2;
    updateScoreUI(); render();
  });
  seValEl.addEventListener("input", function () {
    state.seVal = gradeVal(seValEl.value);
    updateScoreUI(); render();
  });
  Array.prototype.forEach.call(document.querySelectorAll("[data-se-mode]"), function (b) {
    b.addEventListener("click", function () {
      state.seMode = b.dataset.seMode;
      Array.prototype.forEach.call(document.querySelectorAll("[data-se-mode]"), function (x) {
        x.setAttribute("aria-pressed", String(x === b));
      });
      var sum = state.seMode === "sum";
      seSubjEl.hidden = sum;
      seSumEl.hidden = !sum;
      updateScoreUI(); render();
    });
  });

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-alt-track]");
    if (!btn) return;
    var t = btn.dataset.altTrack;
    state.track = t;
    Array.prototype.forEach.call(document.querySelectorAll("[data-track]"), function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.track === t));
    });
    updateScoreUI(); render();
  });

  var t = null;
  qEl.addEventListener("input", function () {
    state.q = qEl.value;
    clearEl.classList.toggle("show", !!qEl.value);
    clearTimeout(t);
    t = setTimeout(render, 90);
  });
  clearEl.addEventListener("click", function () {
    qEl.value = ""; state.q = ""; clearEl.classList.remove("show"); qEl.focus(); render();
  });
  qEl.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { qEl.value = ""; state.q = ""; clearEl.classList.remove("show"); render(); }
  });

  // ── 테마 ──
  var THEME_KEY = "susihanip-theme";
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    Array.prototype.forEach.call(document.querySelectorAll("[data-theme-set]"), function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.themeSet === theme));
    });
    var m = document.getElementById("meta-theme");
    if (m) m.setAttribute("content", theme === "light" ? "#f8fafc" : "#09090b");
  }
  var savedTheme = null;
  try { savedTheme = localStorage.getItem(THEME_KEY); } catch (e) {}
  applyTheme(savedTheme === "light" ? "light" : "dark");
  Array.prototype.forEach.call(document.querySelectorAll("[data-theme-set]"), function (b) {
    b.addEventListener("click", function () {
      var theme = b.dataset.themeSet;
      applyTheme(theme);
      try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
    });
  });

  Promise.all([
    fetch("data/universities.json", { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }),
    fetch("data/cutoffs.json", { cache: "no-cache" }).then(function (r) { return r.ok ? r.json() : { universities: {} }; }).catch(function () { return { universities: {} }; }),
    fetch("data/suneung.json", { cache: "no-cache" }).then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; })
  ]).then(function (res) {
    var data = res[0], cuts = res[1], sunj = res[2];
    state.items = (data.universities || []).slice();
    state.cuts = (cuts && cuts.universities) || {};
    state.sunj = sunj || {};
    state.ready = true;
    document.getElementById("stat-count").textContent = state.items.length;
    if (data.updated) {
      var d = String(data.updated).split("-");
      document.getElementById("stat-updated").textContent =
        d.length === 3 ? d[0] + "." + Number(d[1]) + "." + Number(d[2]) : data.updated;
    }
    updateScoreUI();
    render();
  }).catch(function () {
    listEl.innerHTML = '<div class="empty"><b>목록을 불러오지 못했어요</b>' +
      "잠시 후 새로고침해 주세요. 계속 안 되면 수시한입 채널에 알려 주세요.</div>";
  });
})();
