(function () {
  var el = document.querySelector('script[data-dk-data="history"]'); if (!el) return;
  var d; try { d = JSON.parse(el.textContent); } catch (e) { return; }
  var vs = (d && d.versions) || []; if (!vs.length) return;
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var LBL = { new: '신규', mod: '수정', del: '삭제' };
  var btn = document.createElement('button'); btn.type = 'button'; btn.className = 'dk-hbtn'; btn.setAttribute('aria-expanded', 'false');
  btn.textContent = '버전 기록 v' + vs[0].version;
  var p = document.createElement('section'); p.className = 'dk-hpanel'; p.hidden = true; p.setAttribute('aria-label', '버전 기록');
  p.innerHTML = '<h2>버전 기록</h2><label><input type="checkbox" class="dk-show"> v' + esc(vs[0].version) + '에서 바뀐 곳 보기</label>'
    + vs.map(function (v) { return '<h3>v' + esc(v.version) + (v.date ? ' · ' + esc(v.date) : '') + '</h3><ul>' + (v.changes || []).map(function (c) {
      var t = LBL[c.type] ? c.type : 'mod'; return '<li><span class="dk-tag ' + t + '">' + LBL[t] + '</span>' + esc(c.text) + '</li>'; }).join('') + '</ul>'; }).join('');
  document.body.appendChild(btn); document.body.appendChild(p);
  btn.onclick = function () { p.hidden = !p.hidden; btn.setAttribute('aria-expanded', String(!p.hidden)); };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !p.hidden) { p.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.focus(); } });
  function clear() { [].slice.call(document.querySelectorAll('mark.dk-chg')).forEach(function (m) { var pa = m.parentNode; while (m.firstChild) pa.insertBefore(m.firstChild, m); pa.removeChild(m); pa.normalize(); }); }
  function mark(target, type) {   // 본문 글자 마디에서 문장 일부를 찾아 형광으로(첫 번째만)
    var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: function (n) { return n.parentElement && !n.parentElement.closest('script,style,.dk-hpanel,.dk-hbtn,.dk-tog,.dk-src') ? 1 : 2; } }), n;
    while ((n = w.nextNode())) { var i = n.nodeValue.indexOf(target); if (i !== -1) { var r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + target.length); var m = document.createElement('mark'); m.className = 'dk-chg'; m.dataset.type = type; r.surroundContents(m); return true; } }
    return false;
  }
  p.querySelector('.dk-show').onchange = function (e) { clear(); if (e.target.checked) (vs[0].changes || []).forEach(function (c) { if (c.target && c.type !== 'del') mark(String(c.target), LBL[c.type] ? c.type : 'mod'); }); };
})();
