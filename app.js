(function () {
  var state = { items: [], q: "", type: "전체", region: "전체", sort: "추천순", ready: false };
  var listEl = document.getElementById("list");
  var countEl = document.getElementById("count");
  var qEl = document.getElementById("q");
  var clearEl = document.getElementById("clear");

  var TYPE_CLASS = { "학생부교과": "", "학생부종합": "t2", "논술": "t3" };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

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
      return okType && okRegion && okQuery;
    });
    if (state.sort === "가나다순") {
      rows.sort(function (a, b) {
        return String(a.name || "").localeCompare(String(b.name || ""), "ko");
      });
    } else if (q) {
      // 대학명이 검색어와 맞는 항목을 먼저 보여줌
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

  function render() {
    if (!state.ready) return;
    var rows = filtered();
    countEl.hidden = false;
    countEl.innerHTML = "총 <b>" + rows.length + "</b>곳" +
      (state.type === "전체" ? "" : " · " + esc(state.type)) +
      (state.region === "전체" ? "" : " · " + esc(state.region)) +
      (state.q.trim() ? " · ‘" + esc(state.q.trim()) + "’ 검색" : "");

    if (!rows.length) {
      listEl.innerHTML = '<div class="empty"><b>해당하는 대학이 없어요</b>' +
        (state.q.trim()
          ? "다른 대학명이나 키워드로 검색해 보세요.<br>새 대학은 쇼츠가 올라오면 계속 추가됩니다."
          : "이 전형으로 등록된 대학이 아직 없습니다.") + "</div>";
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
        render();
      });
    });
  }

  wireChips("type", function (v) { state.type = v; });
  wireChips("region", function (v) { state.region = v; });
  wireChips("sort", function (v) { state.sort = v; });

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

  fetch("data/universities.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
    .then(function (data) {
      state.items = (data.universities || []).slice();
      state.ready = true;
      document.getElementById("stat-count").textContent = state.items.length;
      if (data.updated) {
        var d = String(data.updated).split("-");
        document.getElementById("stat-updated").textContent =
          d.length === 3 ? d[0] + "." + Number(d[1]) + "." + Number(d[2]) : data.updated;
      }
      render();
    })
    .catch(function () {
      listEl.innerHTML = '<div class="empty"><b>목록을 불러오지 못했어요</b>' +
        "잠시 후 새로고침해 주세요. 계속 안 되면 수시한입 채널에 알려 주세요.</div>";
    });
})();
