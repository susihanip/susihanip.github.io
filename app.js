(function () {
  var state = { items: [], cuts: {}, q: "", type: "전체", region: "전체", sort: "추천순", band: "전체", track: "gyogwa", grade: null, ready: false };
  var listEl = document.getElementById("list");
  var countEl = document.getElementById("count");
  var qEl = document.getElementById("q");
  var clearEl = document.getElementById("clear");
  var scoreEl = document.getElementById("score");
  var scoreClear = document.getElementById("score-clear");
  var bandWrap = document.getElementById("band-filters");
  var scoreSum = document.getElementById("score-sum");
  var legendEl = document.getElementById("legend");

  var TYPE_CLASS = { "학생부교과": "", "학생부종합": "t2", "논술": "t3" };
  var TRACK_NAME = { gyogwa: "학생부교과", jonghap: "학생부종합" };
  var BAND_RANK = { "안정": 0, "적정": 1, "소신": 2, "어려움": 3, "미등록": 4 };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
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
    var t = c[state.track];
    if (!t && c.jungsi && c.jungsi.pct70) return null;
    return t || null;
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
  function fmt(v) { return v == null ? "-" : (Math.round(v * 100) / 100).toFixed(2); }

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
      var okBand = state.band === "전체" || b === state.band || (b === "미등록" && state.grade != null && state.band !== "전체");
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

    return '' +
      '<article class="card">' +
        '<div class="card-head">' +
          '<div class="card-title">' +
            "<h2>" + esc(u.name) + "</h2>" +
            (u.campus ? '<span class="campus">' + esc(u.campus) + "</span>" : "") +
          "</div>" +
          '<div class="groups">' + types + "</div>" +
        "</div>" +
        cutBlock(u) +
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

  function updateScoreUI() {
    if (state.grade == null) {
      bandWrap.hidden = true; scoreSum.hidden = true; legendEl.hidden = true; scoreClear.hidden = true;
      state.band = "전체";
      Array.prototype.forEach.call(bandWrap.querySelectorAll(".chip"), function (c) {
        c.setAttribute("aria-pressed", String(c.dataset.band === "전체"));
      });
      return;
    }
    bandWrap.hidden = false; scoreSum.hidden = false; legendEl.hidden = false; scoreClear.hidden = false;
    var n = bandCounts();
    scoreSum.innerHTML = "내신 <b>" + state.grade + "등급</b> · " + esc(TRACK_NAME[state.track]) + " 기준 · " +
      '<span class="pill" style="color:var(--b-stable-fg);border-color:var(--b-stable-bd);background:var(--b-stable-bg)">안정 ' + n["안정"] + "</span>" +
      '<span class="pill" style="color:var(--b-fit-fg);border-color:var(--b-fit-bd);background:var(--b-fit-bg)">적정 ' + n["적정"] + "</span>" +
      '<span class="pill" style="color:var(--b-bold-fg);border-color:var(--b-bold-bd);background:var(--b-bold-bg)">소신 ' + n["소신"] + "</span>" +
      '<span class="pill" style="color:var(--b-hard-fg);border-color:var(--b-hard-bd);background:var(--b-hard-bg)">어려움 ' + n["어려움"] + "</span>" +
      '<span class="pill">입결 미등록 ' + n["미등록"] + "</span>";
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
    Array.prototype.forEach.call(bandWrap.querySelectorAll(".chip"), function (c) {
      c.setAttribute("aria-pressed", String(c.dataset.band === "전체"));
    });
    updateScoreUI(); render(); scoreEl.focus();
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
    fetch("data/cutoffs.json", { cache: "no-cache" }).then(function (r) { return r.ok ? r.json() : { universities: {} }; }).catch(function () { return { universities: {} }; })
  ]).then(function (res) {
    var data = res[0], cuts = res[1];
    state.items = (data.universities || []).slice();
    state.cuts = (cuts && cuts.universities) || {};
    state.ready = true;
    document.getElementById("stat-count").textContent = state.items.length;
    if (data.updated) {
      var d = String(data.updated).split("-");
      document.getElementById("stat-updated").textContent =
        d.length === 3 ? d[0] + "." + Number(d[1]) + "." + Number(d[2]) : data.updated;
    }
    render();
  }).catch(function () {
    listEl.innerHTML = '<div class="empty"><b>목록을 불러오지 못했어요</b>' +
      "잠시 후 새로고침해 주세요. 계속 안 되면 수시한입 채널에 알려 주세요.</div>";
  });
})();
