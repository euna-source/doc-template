(function () {
  // 표 반응형: 칸 격자(rowspan·colspan)를 계산해 머리글 이름표를 달고, 폭이 모자라면 카드로 쌓는다.
  var MINCOL = 150;  // 세 칸 이상 표는 칸마다 이만큼(px)이 안 되면 쌓는다 — 휴대폰 폭에서 좁은 칸 여럿보다 카드가 읽힌다
  function text(el) { return (el.textContent || '').replace(/\s+/g, ' ').trim(); }
  function grid(t) {
    var rows = [].slice.call(t.rows), occ = [], info = [];
    rows.forEach(function (tr, ri) {
      occ[ri] = occ[ri] || []; var c = 0;
      [].slice.call(tr.cells).forEach(function (cell) {
        while (occ[ri][c]) c++;
        var rs = cell.rowSpan, cs = Math.max(1, cell.colSpan || 1);
        if (rs === 0) { var sec = tr.parentElement, idx = [].indexOf.call(sec.rows, tr); rs = sec.rows.length - idx; }   // rowspan="0": 줄 묶음 끝까지
        rs = Math.max(1, rs || 1);
        for (var r = 0; r < rs; r++) { occ[ri + r] = occ[ri + r] || []; for (var k = 0; k < cs; k++) occ[ri + r][c + k] = cell; }
        info.push({ cell: cell, r: ri, c: c, rs: rs, cs: cs }); c += cs;
      });
    });
    var cols = 0; occ.forEach(function (o) { cols = Math.max(cols, o.length); });
    return { rows: rows, occ: occ, info: info, cols: cols };
  }
  function prepare(w) {
    var t = w.querySelector(':scope>table'); if (!t || w.dataset.dkReady) return;
    w.dataset.dkReady = '1';
    var g = grid(t), head = [];
    g.rows.forEach(function (tr, ri) {
      var cells = [].slice.call(tr.cells);
      var isHead = tr.parentElement.tagName === 'THEAD' || (ri === head.length && cells.length && cells.every(function (c) { return c.tagName === 'TH'; }) && g.rows.length > 1);
      if (isHead) { head.push(ri); tr.classList.add('dk-head'); }
    });
    var first = g.rows.filter(function (tr) { return !tr.classList.contains('dk-head'); })[0];
    if (first) first.classList.add('dk-first');
    var label = [];
    for (var c = 0; c < g.cols; c++) {
      var parts = []; head.forEach(function (ri) { var h = g.occ[ri] && g.occ[ri][c]; var s = h ? text(h) : ''; if (s && parts.indexOf(s) < 0) parts.push(s); });
      label[c] = parts.join(' · ');
    }
    // 낭독기용: 머리글 칸이 열 머리글인지 줄 머리글인지 알린다(이미 있으면 둔다)
    head.forEach(function (ri) { [].slice.call(g.rows[ri].cells).forEach(function (c) { if (c.tagName === 'TH' && !c.hasAttribute('scope')) c.setAttribute('scope', c.colSpan > 1 ? 'colgroup' : 'col'); }); });
    g.info.forEach(function (x) { if (head.indexOf(x.r) < 0 && x.cell.tagName === 'TH' && !x.cell.hasAttribute('scope')) x.cell.setAttribute('scope', x.rs > 1 ? 'rowgroup' : 'row'); });
    var seenTitle = {};
    g.info.forEach(function (x) {
      if (head.indexOf(x.r) >= 0) return;
      if (x.rs > 1) { x.cell.classList.add('dk-grp'); return; }
      if (!seenTitle[x.r]) { seenTitle[x.r] = 1; x.cell.classList.add('dk-title'); return; }
      if (label[x.c] && label[x.c] !== text(x.cell)) x.cell.setAttribute('data-dk-label', label[x.c]);
    });
    w.dataset.dkCols = g.cols;
  }
  function fit(w) {
    var t = w.querySelector(':scope>table'); if (!t) return;
    var cols = +w.dataset.dkCols || 1;
    w.classList.remove('dk-stack');
    // 낱말(어절)을 쪼개지 않고 들어가는지 본다 — 칸은 overflow-wrap:normal이라 안 들어가면 표가 감싸개보다 넓어진다
    var room = w.clientWidth; if (!room) return;   // 숨은 탭 안 표는 보일 때(크기 바뀜) 다시 잰다
    var over = t.scrollWidth - room;
    var tooNarrow = cols >= 3 && room < cols * MINCOL;
    if ((over > 2 || tooNarrow) && cols >= 2) w.classList.add('dk-stack');
    // 그래도 가로로 넘치면(쌓을 수 없는 한 칸 표 등) 키보드로도 옆으로 움직일 수 있게
    if (w.scrollWidth > w.clientWidth + 2) { if (!w.hasAttribute('tabindex')) { w.setAttribute('tabindex', '0'); w.dataset.dkTab = '1'; } }
    else if (w.dataset.dkTab) { w.removeAttribute('tabindex'); delete w.dataset.dkTab; }
  }
  function wrap(t) {
    // 엔진 열린 표(.table)·배치용 표·표 안의 표·머리·목차 안 표는 건드리지 않는다
    if (t.closest('.dk-table, .table, nav, header') || t.hasAttribute('data-dk-skip') || t.getAttribute('role') === 'presentation' || (t.parentElement && t.parentElement.closest('td,th'))) return null;
    var p = t.parentElement;
    if (p && p.children.length === 1 && /^(DIV|FIGURE)$/.test(p.tagName) && p !== document.body) { p.classList.add('dk-table'); return p; }
    var d = document.createElement('div'); d.className = 'dk-table'; t.parentNode.insertBefore(d, t); d.appendChild(t); return d;
  }
  function run() {
    [].slice.call(document.querySelectorAll('table')).forEach(wrap);
    var ws = [].slice.call(document.querySelectorAll('.dk-table'));
    ws.forEach(prepare); ws.forEach(fit);
    if ('ResizeObserver' in window) {
      var last = new WeakMap();
      var ro = new ResizeObserver(function (es) { es.forEach(function (e) { var w = Math.round(e.contentRect.width); if (last.get(e.target) !== w) { last.set(e.target, w); fit(e.target); } }); });
      ws.forEach(function (w) { ro.observe(w); });
    } else window.addEventListener('resize', function () { ws.forEach(fit); });
    window.addEventListener('beforeprint', function () { ws.forEach(function (w) { w.classList.remove('dk-stack'); }); });
    window.addEventListener('afterprint', function () { ws.forEach(fit); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
