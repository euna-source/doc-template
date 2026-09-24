"""GitHub Pages 저장소에 문서 한 장을 올린다.
설정: 환경변수 DOC_TEMPLATE_PAGES_REPO=owner/repo (Pages가 켜진 저장소), gh 로그인 필요.
안전장치: doc-template이 만든 .html만(생성기 표식 확인·5MB 이하), 저장소별 잠금으로 동시 배포 직렬화, 공개 URL 응답 확인."""
import fcntl, os, re, shutil, subprocess, time, urllib.request
from contextlib import contextmanager
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024

def _slug(s):
    s = re.sub(r'[^a-z0-9-]+', '-', s.lower()).strip('-')
    if not s or len(s) > 80:
        raise ValueError('slug는 영문 소문자·숫자·하이픈, 80자 이하')
    return s

def _check_html(path):
    p = Path(path).expanduser().resolve()
    if p.suffix.lower() != '.html' or not p.is_file():
        raise ValueError('doc-template이 만든 .html 파일만 올립니다')
    if p.stat().st_size > MAX_BYTES:
        raise ValueError('5MB를 넘는 파일은 올리지 않습니다')
    head = p.read_text(encoding='utf-8', errors='replace')[:4000]
    if 'name="generator" content="doc-template' not in head:
        raise ValueError('doc-template 생성기 표식이 없는 파일입니다')
    return p

@contextmanager
def _lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)

def _run(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()

def _base_url(cache, owner, name):
    cname = cache / 'CNAME'
    if cname.exists() and cname.read_text().strip():
        return 'https://' + cname.read_text().strip().splitlines()[0]
    return f'https://{owner}.github.io' if name.lower() == f'{owner}.github.io'.lower() else f'https://{owner}.github.io/{name}'

def publish(html_path, slug, repo=None, message=None, wait=90):
    src = _check_html(html_path)
    repo = repo or os.environ.get('DOC_TEMPLATE_PAGES_REPO')
    if not repo or not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        raise RuntimeError('DOC_TEMPLATE_PAGES_REPO(owner/repo)가 없습니다. HTML 파일만 쓰거나 Pages 저장소를 지정하세요.')
    slug = _slug(slug)
    root = Path(os.environ.get('DOC_TEMPLATE_CACHE', Path.home() / '.cache' / 'doc-template'))
    cache = root / repo.replace('/', '__')
    with _lock(root / (repo.replace('/', '__') + '.lock')):
        if (cache / '.git').exists():
            _run('git', 'fetch', '-q', 'origin', cwd=cache)
            _run('git', 'reset', '-q', '--hard', '@{u}', cwd=cache)
        else:
            _run('gh', 'repo', 'clone', repo, str(cache), '--', '-q', '--depth', '1')
        dest = cache / slug
        dest.mkdir(exist_ok=True)
        shutil.copyfile(src, dest / 'index.html')
        _run('git', 'add', '--', f'{slug}/index.html', cwd=cache)
        changed = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=cache).returncode != 0
        if changed:
            _run('git', 'commit', '-q', '-m', message or f'doc-template: {slug}', cwd=cache)
            _run('git', 'push', '-q', 'origin', 'HEAD', cwd=cache)
        owner, name = repo.split('/')
        url = f'{_base_url(cache, owner, name)}/{slug}/'
    live = False
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + f'?v={int(time.time())}', timeout=10) as r:
                if r.status == 200 and b'doc-template' in r.read(6000):
                    live = True
                    break
        except Exception:
            pass
        time.sleep(8)
    return {'url': url, 'changed': changed, 'live': live}
