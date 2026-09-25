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
    const cs = getComputedStyle(root);
    const line = parseFloat(cs.getPropertyValue('--header-h')) + (parseFloat(cs.getPropertyValue('--band-h')) || 0) + 80;
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

  const hashId = (h) => { try { return decodeURIComponent(h.slice(1)); } catch { return h.slice(1); } };
  // 목차·절 링크로 이동한 뒤 도착점이 밀렸으면 제자리로 다시 맞춘다. 가장 최근 이동에만 걸고, 손으로 스크롤하면 취소한다
  let navId = 0;
  const cancelSettle = () => { navId++; };
  ['wheel', 'touchstart', 'keydown'].forEach((ev) => addEventListener(ev, cancelSettle, { passive: true }));
  const settle = (id) => {
    const el = id && document.getElementById(id);
    if (!el || el.closest('.drawer')) return;  // 서랍 안은 서랍이 따로 연다
    const mine = ++navId;
    let done = false;
    const fix = () => {
      if (done || mine !== navId) return;
      done = true;
      const want = parseFloat(getComputedStyle(root).scrollPaddingTop) || 0;
      const off = el.getBoundingClientRect().top - want;
      const room = root.scrollHeight - innerHeight - scrollY;
      if (Math.abs(off) > 4 && (off < 0 || room > 4)) window.scrollBy({ top: off, behavior: 'instant' });
      update();
    };
    const y0 = scrollY;
    if ('onscrollend' in window) {
      addEventListener('scrollend', fix, { once: true });
      setTimeout(() => { if (scrollY === y0) fix(); }, 200); // 이미 제자리라 스크롤이 일어나지 않으면 scrollend도 오지 않는다
    } else setTimeout(fix, 1200);
  };
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (a && a.hash.length > 1) settle(hashId(a.hash));
  });

  // 결정 모음: 주소가 가리키는 항목은 펼친다(표지 줄·절 머리 '정할 것'에서 올 때)
  const openTarget = (id) => {
    const el = id && document.getElementById(id);
    const d = el && (el.tagName === 'DETAILS' ? el : el.closest('details'));
    if (d) d.open = true;
  };
  addEventListener('hashchange', () => openTarget(hashId(location.hash)));
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (a) openTarget(hashId(a.hash));
  });
  openTarget(hashId(location.hash));
  // 결정 항목이 셋 이상인 절에는 '모두 펼치기'를 둔다
  $$('.doc > section').forEach((sec) => {
    const items = $$(':scope > details.decide', sec);
    if (items.length < 3) return;
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'hub-toggle';
    const sync = () => { btn.textContent = items.every((d) => d.open) ? '모두 접기' : '모두 펼치기'; };
    btn.addEventListener('click', () => { const open = !items.every((d) => d.open); items.forEach((d) => { d.open = open; }); sync(); });
    items.forEach((d) => d.addEventListener('toggle', sync));
    // 소제목(h3)으로 묶었으면 첫 묶음 제목 앞에 둔다
    const prev = items[0].previousElementSibling;
    (prev && prev.tagName === 'H3' ? prev : items[0]).before(btn); sync();
  });
  // 인쇄할 때는 접힌 내용도 모두 싣는다
  let closedForPrint = [];
  addEventListener('beforeprint', () => { closedForPrint = $$('details:not([open])'); closedForPrint.forEach((d) => { d.open = true; }); });
  addEventListener('afterprint', () => { closedForPrint.forEach((d) => { d.open = false; }); closedForPrint = []; });

  // 고정 달력 띠 높이 → 앵커 이동 여백(--band-h)
  const band = $('#calband');
  if (band) {
    const setBand = () => root.style.setProperty('--band-h', band.getBoundingClientRect().height + 'px');
    setBand();
    if ('ResizeObserver' in window) new ResizeObserver(setBand).observe(band); else addEventListener('resize', setBand);
  }

  // 오늘: 달력 칸·국면 카드에 표시(보는 사람 기기의 날짜)
  const pad = (n) => String(n).padStart(2, '0');
  const now = new Date();
  const today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const td = $(`.day[data-date="${today}"]`);
  if (td) { td.classList.add('today'); td.setAttribute('aria-current', 'date'); td.setAttribute('aria-label', `오늘, ${td.textContent.trim()}`); }
  $$('.phase-card[data-start], .pn[data-start]').forEach((el) => {
    const a = el.dataset.start, b = el.dataset.end;
    if (a && b && a <= today && today <= b) {
      el.classList.add('now');
      const tag = $('.pc-now', el); if (tag) tag.hidden = false;
    }
  });
  // 오늘이 달력 안이면 그 칸이 보이게 가로 스크롤
  if (td) { const cal = td.closest('.calgrid'); if (cal) cal.scrollLeft = td.offsetLeft - cal.clientWidth / 2 + td.clientWidth / 2; }
  // 오늘이 달력 밖이면 범례에 며칠 앞·뒤인지 적는다
  const days = $$('.day[data-date]');
  if (days.length && !td) {
    const first = days[0].dataset.date, last = days[days.length - 1].dataset.date;
    const diff = (a, b) => Math.round((new Date(a) - new Date(b)) / 864e5);
    const lg = $('.cal-legend');
    const md = `${now.getMonth() + 1}/${now.getDate()}`;
    const msg = today < first ? `오늘(${md})은 달력 시작 ${diff(first, today)}일 전` : today > last ? `오늘(${md})은 달력 끝 ${diff(today, last)}일 뒤` : '';
    if (lg && msg) { const s = document.createElement('span'); s.className = 'lg-away'; s.textContent = msg; lg.prepend(s); }
    $('.lg.today')?.classList.add('absent');
  }
  // 읽는 위치를 따라 날짜 칸을 표시하고 달력 줄을 그 칸으로 민다(휴대폰에서 줄이 멈춰 있지 않게)
  const tlRows = $$('.tl-row[id^="d"]');
  if (tlRows.length && days.length) {
    const byId = {}; days.forEach((d) => { const h = d.getAttribute('href'); if (h) (byId[h.slice(1)] = byId[h.slice(1)] || []).push(d); });
    let last = '';
    const spy = () => {
      const line = parseFloat(getComputedStyle(root).getPropertyValue('--header-h')) + (parseFloat(getComputedStyle(root).getPropertyValue('--band-h')) || 0) + 40;
      let curRow = null;
      for (const r of tlRows) { if (r.getBoundingClientRect().top <= line) curRow = r; else break; }
      const id = curRow ? curRow.id : '';
      if (id === last) return; last = id;
      $$('.day.reading').forEach((x) => x.classList.remove('reading'));
      const hit = byId[id] || [];
      hit.forEach((x) => x.classList.add('reading'));
      if (hit[0]) { const g = hit[0].closest('.calgrid'); if (g) g.scrollTo({ left: hit[0].offsetLeft - 8, behavior: 'smooth' }); }
    };
    let t2 = 0; addEventListener('scroll', () => { cancelAnimationFrame(t2); t2 = requestAnimationFrame(spy); }, { passive: true });
  }
  // 누른 날짜 칸 표시
  document.addEventListener('click', (e) => {
    const d = e.target.closest('.day');
    if (d) { $$('.day.sel').forEach((x) => x.classList.remove('sel')); d.classList.add('sel'); }
  });

  // 레이어(서랍): 버튼·목차·절 링크로 연다. Esc·바깥·닫기로 닫고, 연 자리로 초점을 돌린다
  const drawerBg = $('#drawer-bg');
  let openDrawer = null, opener = null;
  const closeLayer = () => {
    if (!openDrawer) return;
    openDrawer.hidden = true; if (drawerBg) drawerBg.hidden = true;
    document.body.classList.remove('drawer-open');
    openDrawer = null;
    if (opener && opener.focus) opener.focus();
  };
  const openLayer = (id, from) => {
    const d = document.getElementById(id);
    if (!d || !d.classList.contains('drawer')) return false;
    if (openDrawer && openDrawer !== d) { openDrawer.hidden = true; }
    opener = from || document.activeElement;
    d.hidden = false; if (drawerBg) drawerBg.hidden = false;
    document.body.classList.add('drawer-open');
    openDrawer = d;
    $('.drawer-body', d).scrollTop = 0;
    $('.drawer-close', d).focus();
    return true;
  };
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-layer]');
    if (b) { e.preventDefault(); openLayer(b.dataset.layer, b); return; }
    const a = e.target.closest('a[href^="#"]');
    if (a && a.hash.length > 1) {
      const id = hashId(a.hash);
      const target = document.getElementById(id);
      if (target && target.classList.contains('drawer')) { e.preventDefault(); openLayer(id, a); return; }
      // 레이어 안에서 본문으로 가는 링크: 레이어를 닫고 이동
      const inDrawer = target ? target.closest('.drawer') : null;
      if (openDrawer && !inDrawer && a.closest('.drawer')) closeLayer();
      if (inDrawer && target !== inDrawer) { e.preventDefault(); if (inDrawer !== openDrawer) openLayer(inDrawer.id, a); const dt = target.closest('details'); if (dt) dt.open = true; target.scrollIntoView({ block: 'start' }); }
    }
    if (e.target.closest('.drawer-close') || e.target === drawerBg) closeLayer();
  });
  addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && openDrawer) { closeLayer(); return; }
    if (e.key === 'Tab' && openDrawer) {   // 초점을 서랍 안에 가둔다
      const f = $$('a[href],button,[tabindex]:not([tabindex="-1"]),summary', openDrawer).filter((x) => x.offsetParent !== null);
      if (!f.length) return;
      if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
    }
  });
  if (location.hash) {
    const id = hashId(location.hash); const t0 = document.getElementById(id);
    const d0 = t0 && (t0.classList.contains('drawer') ? t0 : t0.closest('.drawer'));
    if (d0) { openLayer(d0.id); if (t0 !== d0) { const dt = t0.closest('details'); if (dt) dt.open = true; t0.scrollIntoView({ block: 'start' }); } }
  }

  // 탭
  $$('.tabs').forEach((box) => {
    const tabs = $$('[role="tab"]', box);
    const pick = (t) => tabs.forEach((x) => {
      const on = x === t;
      x.setAttribute('aria-selected', String(on)); x.tabIndex = on ? 0 : -1;
      document.getElementById(x.getAttribute('aria-controls')).hidden = !on;
    });
    tabs.forEach((t, i) => {
      t.addEventListener('click', () => pick(t));
      t.addEventListener('keydown', (e) => {
        const k = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        const n = k ? tabs[(i + k + tabs.length) % tabs.length] : e.key === 'Home' ? tabs[0] : e.key === 'End' ? tabs[tabs.length - 1] : null;
        if (n) { e.preventDefault(); pick(n); n.focus(); }
      });
    });
  });

  // 목록·필터형: 필터 줄(고정)·검색·건수·핵심 열만·그룹 접기
  const catbar = $('#catbar');
  const catTable = $('table.cat');
  if (catbar && catTable) {
    const setBar = () => root.style.setProperty('--catbar-h', catbar.getBoundingClientRect().height + 'px');
    setBar();
    if ('ResizeObserver' in window) new ResizeObserver(setBar).observe(catbar);
    const rows = $$('tr.row', catTable);
    const grps = $$('tr.grp', catTable);
    rows.forEach((r) => { r._t = r.textContent.toLowerCase(); });
    const groups = $$('.fgroup', catbar);
    const q = $('#cat-q');
    const openGroups = new Set(), closedGroups = new Set();   // 처음 접힌 그룹을 편 것 / 손으로 접은 것
    const matchOpt = (r, field, v) => {
      const t = r.getAttribute('data-f-' + field) || '';
      if (v === 'all') return true;
      if (v === 'any') return t.trim() !== '' && t.trim() !== '—';
      return v.split('|').some((p) => p && (p.startsWith('^') ? t.trim().startsWith(p.slice(1)) : t.includes(p)));  // ^는 '로 시작'
    };
    const cur = () => groups.map((g) => [g.dataset.field, ($('button[aria-pressed="true"]', g) || {}).dataset?.v || 'all']);
    // 선택지마다 건수(다른 필터와 상관없이)
    groups.forEach((g) => $$('button[data-v]', g).forEach((b) => {
      const n = $('.n', b); if (n) n.textContent = rows.filter((r) => matchOpt(r, g.dataset.field, b.dataset.v)).length;
    }));
    const apply = () => {
      const sel = cur();
      const query = (q && q.value.trim().toLowerCase()) || '';
      const per = {};
      let shown = 0;
      rows.forEach((r) => {
        let ok = sel.every(([f, v]) => matchOpt(r, f, v)) && (!query || r._t.includes(query));
        const g = document.getElementById(r.dataset.g);
        const folded = g && !query && (closedGroups.has(g.id) || (g.dataset.fold === '1' && !openGroups.has(g.id) && !sel.some(([f, v]) => v !== 'all' && v !== 'any' && matchOpt(r, f, v))));
        per[r.dataset.g] = (per[r.dataset.g] || 0) + (ok ? 1 : 0);
        if (ok) shown++;
        r.classList.toggle('hidden', !ok || folded);
      });
      grps.forEach((g) => {
        const n = per[g.id] || 0, c = $('.gcount', g), tot = +c.dataset.total;
        const folded = !query && (closedGroups.has(g.id) || (g.dataset.fold === '1' && !openGroups.has(g.id)));
        c.textContent = folded ? `${tot}행 · 접힘` : n === tot ? `${tot}행` : `${n} / ${tot}행`;
        g.classList.toggle('folded', folded);
        $('.gtog', g).setAttribute('aria-expanded', String(!folded));
        g.classList.toggle('hidden', n === 0 && !folded);
        const chip = $(`.gchip[data-g="${g.id}"]`); if (chip) chip.classList.toggle('empty', n === 0);
      });
      const cnt = $('#cat-count'); if (cnt) cnt.textContent = `표시 ${shown} / ${rows.length}행`;
      const tg = $('#cat-ftoggle');
      if (tg) { const active = sel.filter(([, v], i) => v !== groups[i].dataset.default).length; tg.textContent = active ? `필터 · ${active}` : '필터'; }
    };
    groups.forEach((g) => g.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-v]'); if (!b) return;
      $$('button[data-v]', g).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      apply();
    }));
    const reset = () => {
      groups.forEach((g) => $$('button[data-v]', g).forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.v === g.dataset.default))));
      if (q) q.value = ''; openGroups.clear(); closedGroups.clear(); apply();
    };
    $('#cat-reset')?.addEventListener('click', reset);
    q?.addEventListener('input', apply);
    catTable.addEventListener('click', (e) => {
      const t = e.target.closest('.gtog'); if (!t) return;
      const g = t.closest('tr.grp');
      if (g.classList.contains('folded')) { closedGroups.delete(g.id); if (g.dataset.fold === '1') openGroups.add(g.id); }
      else if (g.dataset.fold === '1' && openGroups.has(g.id)) openGroups.delete(g.id);
      else closedGroups.add(g.id);
      apply();
    });
    const more = $('#cat-more');
    more?.addEventListener('click', () => {
      const on = document.body.classList.toggle('cat-core');
      more.setAttribute('aria-pressed', String(on));
      $$('tr.hg th[data-span]', catTable).forEach((th) => { th.colSpan = on ? +th.dataset.spanCore || 1 : +th.dataset.span; });
    });
    const ft = $('#cat-ftoggle');
    ft?.addEventListener('click', () => { const o = catbar.classList.toggle('open'); ft.setAttribute('aria-expanded', String(o)); });
    // 그룹 칩: 접힌 그룹이면 펼치고 그 줄로
    $$('.gchip', catbar).forEach((c) => c.addEventListener('click', () => {
      const g = document.getElementById(c.dataset.g);
      if (g && g.dataset.fold === '1') { openGroups.add(g.id); apply(); }
    }));
    apply();
  }

  // 모바일 목차: 항목을 누르면 접는다
  const tocMobile = $('.toc-mobile');
  tocMobile?.addEventListener('click', (e) => { if (e.target.closest('a')) tocMobile.open = false; });
})();
