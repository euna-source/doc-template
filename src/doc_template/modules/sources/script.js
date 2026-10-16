(function () {
  var el = document.querySelector('script[data-dk-data="sources"]'); if (!el) return;
  var d; try { d = JSON.parse(el.textContent); } catch (e) { return; }
  var ss = (d && d.sources) || []; if (!ss.length) return;
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var ST = { '확인': 'ok', '일부': 'part', '미확인': 'no' };
  var box = document.createElement('footer'); box.className = 'dk-src';
  box.innerHTML = '<details><summary>출처 · ' + ss.length + '</summary><ol>' + ss.map(function (s) {
    var u = /^https?:\/\//.test(s.url || '') ? s.url : '', st = ST[s.state] ? s.state : '';
    return '<li>' + (u ? '<a href="' + esc(u) + '" rel="noopener" target="_blank">' + esc(s.title || u) + '</a>' : esc(s.title)) + (st ? '<span class="dk-st ' + ST[st] + '">' + st + '</span>' : '') + (s.note ? '<small>' + esc(s.note) + '</small>' : '') + '</li>';
  }).join('') + '</ol></details>';
  document.body.appendChild(box);
})();
