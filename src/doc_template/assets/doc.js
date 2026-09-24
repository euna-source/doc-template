(() => {
  'use strict';
  const root = document.documentElement;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const store = {
    get(k) { try { return localStorage.getItem('doc-tpl-' + k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem('doc-tpl-' + k, v); } catch { /* 저장 불가: 화면 상태만 유지 */ } }
  };

  // 알림
  const toast = $('#toast');
  let toastTimer;
  const say = (msg) => {
    if (!toast) return;
    toast.textContent = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.textContent = ''; }, 4000);
  };

  // 테마: 저장값 > 시스템 설정
  const themeBtn = $('#theme-btn');
  const themeMeta = $('meta[name="theme-color"]');
  const systemDark = matchMedia('(prefers-color-scheme: dark)');
  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    const dark = theme === 'dark';
    if (themeBtn) {
      $('.label', themeBtn).textContent = dark ? '라이트' : '다크';
      themeBtn.setAttribute('aria-label', dark ? '라이트 모드로 보기' : '다크 모드로 보기');
    }
    if (themeMeta) themeMeta.content = dark ? '#20231F' : '#F6F3EB';
  };
  const saved = store.get('theme');
  applyTheme(saved === 'light' || saved === 'dark' ? saved : (systemDark.matches ? 'dark' : 'light'));
  systemDark.addEventListener('change', (e) => { if (!store.get('theme')) applyTheme(e.matches ? 'dark' : 'light'); });
  themeBtn?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    store.set('theme', next);
  });

  // 강조 켜기/끄기
  const markBtn = $('#mark-btn');
  markBtn?.addEventListener('click', () => {
    const off = document.body.classList.toggle('marks-off');
    markBtn.setAttribute('aria-pressed', String(!off));
    say(off ? '노란 강조를 껐습니다.' : '노란 강조를 켰습니다.');
  });

  // 인쇄·PDF
  $('#print-btn')?.addEventListener('click', () => window.print());

  // 링크 복사·공유 (기본 기능)
  // 주소는 canonical이 있으면 그것, 없으면 지금 주소에서 # 뒤를 뗀 값. 문서 단위로 공유한다.
  // 남이 열 수 있는 웹 주소(http·https)만 쓴다. canonical이 file:이거나 로컬 기준 상대 주소면 버리고 지금 주소로,
  // 그것도 file:이면 공유할 주소가 없다 → null.
  const webUrl = (u) => {
    try { const x = new URL(u, location.href); return /^https?:$/.test(x.protocol) ? x.href.split('#')[0] : null; }
    catch { return null; }
  };
  const docUrl = () => {
    const c = $('link[rel="canonical"]')?.getAttribute('href');
    return (c && webUrl(c)) || webUrl(location.href);
  };
  const NO_URL = '아직 배포 전 파일이라 공유할 주소가 없습니다. 배포한 페이지에서 눌러 주세요.';
  const metaOf = (sel) => $(sel)?.content || '';
  const legacyCopy = (v) => {
    const ta = document.createElement('textarea');
    ta.value = v; ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:-9999px;opacity:0';
    document.body.appendChild(ta); ta.select();
    let ok = false;
    try { ok = document.execCommand('copy'); } catch { ok = false; }
    ta.remove();
    return ok;
  };
  const copyText = (v) => (navigator.clipboard && window.isSecureContext)
    ? navigator.clipboard.writeText(v).then(() => true, () => legacyCopy(v))
    : Promise.resolve(legacyCopy(v));
  $('#copy-btn')?.addEventListener('click', () => {
    if (!docUrl()) { say(NO_URL); return; }
    copyText(docUrl()).then((ok) => say(ok ? '링크를 복사했습니다.' : '복사하지 못했습니다. 주소창의 링크를 직접 복사해 주세요.'));
  });
  $('#share-btn')?.addEventListener('click', () => {
    if (!docUrl()) { say(NO_URL); return; }
    const data = {
      title: metaOf('meta[property="og:title"]') || document.title,
      text: metaOf('meta[property="og:description"]') || metaOf('meta[name="description"]'),
      url: docUrl()
    };
    if (navigator.share && (!navigator.canShare || navigator.canShare(data))) {
      // 공유 창을 연 뒤에는 사용자 동작이 소모돼 자동 복사가 막힐 수 있다(사파리). 실패하면 안내만 한다.
      navigator.share(data).catch((e) => say(e && e.name === 'AbortError'
        ? '공유 창이 닫혔습니다. 링크가 필요하면 링크 버튼을 눌러 주세요.'
        : '공유하지 못했습니다. 링크 버튼을 눌러 링크를 가져가 주세요.'));
    } else {
      copyText(data.url).then((ok) => say(ok
        ? '링크를 복사했습니다. 원하는 곳에 붙여 넣어 공유하세요.'
        : '공유하지 못했습니다. 주소창의 링크를 직접 복사해 주세요.'));
    }
  });

  // 표 → 모바일 카드: 머리글을 칸마다 이름표로 붙인다
  $$('.table.stack table').forEach((table) => {
    const heads = $$('thead th', table).map((th) => th.textContent.trim());
    $$('tbody tr', table).forEach((tr) => {
      $$('td', tr).forEach((td, i) => { if (!td.dataset.label && heads[i]) td.dataset.label = heads[i]; });
    });
  });

  // 읽기 진행 + 목차 현재 위치
  const bar = $('#progress');
  const sections = $$('.doc > section[id]');
  const tocLinks = $$('.toc a');
  let ticking = false;
  const update = () => {
    ticking = false;
    const max = root.scrollHeight - innerHeight;
    if (bar) bar.style.width = (max > 0 ? Math.min(1, Math.max(0, scrollY / max)) * 100 : 0) + '%';
    if (!sections.length) return;
    const line = parseFloat(getComputedStyle(root).getPropertyValue('--header-h')) + 80;
    let current = sections[0];
    for (const s of sections) if (s.getBoundingClientRect().top <= line) current = s;
    if (innerHeight + scrollY >= root.scrollHeight - 4) current = sections[sections.length - 1];
    tocLinks.forEach((a) => {
      if (a.hash === '#' + current.id) a.setAttribute('aria-current', 'true');
      else a.removeAttribute('aria-current');
    });
  };
  const toTop = $('#to-top');
  toTop?.addEventListener('click', () => { window.scrollTo({ top: 0 }); $('.skip')?.focus?.(); });
  const onScroll = () => {
    if (toTop) toTop.classList.toggle('show', scrollY > innerHeight * 2);
    if (!ticking) { ticking = true; requestAnimationFrame(update); }
  };
  addEventListener('scroll', onScroll, { passive: true });
  addEventListener('resize', onScroll);
  update();

  // 모바일 목차: 항목을 누르면 접는다
  const tocMobile = $('.toc-mobile');
  tocMobile?.addEventListener('click', (e) => { if (e.target.closest('a')) tocMobile.open = false; });
})();
