(function () {
  var root = document.documentElement, KEY = 'dk-theme:' + location.pathname;
  var own = false;   // 페이지가 [data-theme]로 자체 다크를 갖고 있나
  try { [].slice.call(document.styleSheets).forEach(function (s) { try { [].slice.call(s.cssRules || []).forEach(function (r) { if (/data-theme/.test(r.cssText)) own = true; }); } catch (e) {} }); } catch (e) {}
  var b = document.createElement('button'); b.type = 'button'; b.className = 'dk-tog';
  function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  function apply(t) {
    if (own) { root.dataset.theme = t; } else { root.classList.toggle('dk-invert', t === 'dark'); }
    b.textContent = t === 'dark' ? '라이트' : '다크'; b.setAttribute('aria-label', t === 'dark' ? '라이트 모드로 보기' : '다크 모드로 보기');
  }
  var cur = get() || (own && root.dataset.theme) || 'light';
  b.onclick = function () { cur = cur === 'dark' ? 'light' : 'dark'; set(cur); apply(cur); };
  document.body.appendChild(b); apply(cur);
})();
