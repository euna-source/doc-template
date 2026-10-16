"""GitHub Pages 저장소에 문서 한 장을 올린다.
설정: 환경변수 DOC_TEMPLATE_PAGES_REPO=owner/repo (Pages가 켜진 저장소), gh 로그인 필요.
안전장치: doc-template이 만든 .html만(생성기 표식 확인·5MB 이하), 저장소별 잠금으로 동시 배포 직렬화, 공개 URL 응답 확인.
함께 올리는 파일: 문서가 상대 경로로 부르는 그림(png·jpg·gif·webp·avif·svg)과 생성기 표식이 있는 도식 HTML(Archify·doc-template)만,
문서 폴더 안에 있을 때만(밖·절대 경로·주소는 무시), 한 파일 10MB·합계 20MB 안."""
import fcntl, html as _html, os, re, shutil, subprocess, time, urllib.request
from urllib.parse import unquote, urlsplit
from contextlib import contextmanager
from pathlib import Path

MAX_BYTES = 5 * 1024 * 1024
ASSET_MAX = 10 * 1024 * 1024
ASSETS_TOTAL = 20 * 1024 * 1024
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.svg'}
DIAGRAM_MARKS = ('name="generator" content="archify', 'name="generator" content="doc-template')

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

def assets(html_path):
    """문서가 상대 경로로 부르는 함께 올릴 파일 [(원본 경로, 문서 폴더 기준 상대 경로)]. 조건에 맞지 않는 참조는 조용히 건너뛴다."""
    src = Path(html_path).expanduser().resolve()
    base = src.parent
    out, seen, total = [], set(), 0
    for ref in re.findall(r'(?:src|href)="([^"]+)"', src.read_text(encoding='utf-8', errors='replace')):
        ref = _html.unescape(ref)
        u = urlsplit(ref)
        if u.scheme or u.netloc or not u.path or u.path.startswith('/'):
            continue
        p = (base / unquote(u.path)).resolve()
        if p == src or p in seen or not p.is_file() or not p.is_relative_to(base):
            continue
        if p.relative_to(base).as_posix().lower() == 'index.html':
            continue   # 배포 본문 자리(index.html)는 문서 자신만 쓴다
        ext = p.suffix.lower()
        if ext == '.html':
            if not any(m in p.read_text(encoding='utf-8', errors='replace')[:4000] for m in DIAGRAM_MARKS):
                continue
        elif ext not in IMAGE_EXT:
            continue
        size = p.stat().st_size
        if size > ASSET_MAX or total + size > ASSETS_TOTAL:
            raise ValueError(f'함께 올릴 파일이 너무 큽니다: {p.name} (한 파일 10MB·합계 20MB)')
        seen.add(p); total += size
        out.append((p, p.relative_to(base).as_posix()))
    return out


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
        if dest.exists():
            shutil.rmtree(dest)   # 이 slug 폴더는 publish가 통째로 맡는다 — 이번에 뺀 그림이 공개 주소에 남지 않게
        dest.mkdir()
        shutil.copyfile(src, dest / 'index.html')
        files = [f'{slug}/index.html']
        for a_src, rel in assets(src):
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(a_src, dest / rel)
            files.append(f'{slug}/{rel}')
        _run('git', 'add', '-A', '--', slug, cwd=cache)
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
    return {'url': url, 'changed': changed, 'live': live, 'files': files}
