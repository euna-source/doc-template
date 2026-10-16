(() => {
  const status = document.getElementById('action-status');
  let toastTimer;
  const say = text => { status.textContent = text; status.classList.add('on'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>status.classList.remove('on'),4000); };
  let original = null, canonicalUrl = null;
  try {
    const data = JSON.parse(document.getElementById('meeting-copy-data').textContent);
    original = data.transcript;
    canonicalUrl = data.url || (/^https?:$/.test(location.protocol) ? location.origin + location.pathname : null);
  } catch (_) { say('복사할 데이터를 불러오지 못했습니다.'); }
  document.getElementById('copy-original').disabled = typeof original !== 'string';
  document.getElementById('share-url').disabled = !canonicalUrl;
  const minutesText = () => {
    const main = document.querySelector('main').cloneNode(true);
    const sources = document.querySelector('footer.tray');
    if (sources) main.append(sources.cloneNode(true));
    main.querySelectorAll('.hbtns,.meeting-actions,.action-help,#action-status,script,style,[data-f],[data-n]').forEach(el => el.remove());
    main.querySelectorAll('details').forEach(el => el.open = true);
    main.querySelectorAll('[hidden]').forEach(el => el.removeAttribute('hidden'));
    const host = document.createElement('div');
    host.style.cssText = 'position:absolute;left:-100000px;width:1000px';
    host.append(main); document.body.append(host);
    const result = main.innerText.trim(); host.remove(); return result;
  };
  async function copy(text, done) {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
      await navigator.clipboard.writeText(text);
      say(done); return;
    } catch (_) {
      const box = document.createElement('textarea');
      box.value = text; box.style.cssText = 'position:fixed;top:0;left:-10000px';
      document.body.append(box); box.focus(); box.select();
      let ok = false;
      try { ok = document.execCommand('copy'); } catch (_) {}
      box.remove();
      if (ok) { say(done); return; }
      const dialog = document.getElementById('copy-dialog');
      const field = dialog.querySelector('textarea'); field.value = text;
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
      field.focus(); field.select(); field.setSelectionRange(0, text.length);
      say('자동 복사가 제한되어 전체 텍스트를 열었습니다. 텍스트를 선택해 복사해 주세요.');
    }
  }
  document.getElementById('share-url').addEventListener('click', () => copy(canonicalUrl, '회의록 URL을 복사했습니다.'));
  document.getElementById('copy-minutes').addEventListener('click', () => copy(minutesText(), '회의록 텍스트 전체를 복사했습니다.'));
  document.getElementById('copy-original').addEventListener('click', () => copy(original, '음성 원문 전체를 복사했습니다.'));
  document.getElementById('close-copy-dialog').addEventListener('click', () => {
    const dialog = document.getElementById('copy-dialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  });
})();
