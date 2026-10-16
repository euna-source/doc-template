"""배포 때 함께 올리는 파일: 문서 폴더 안 상대 경로 그림·도식 HTML만, 로컬 bare 저장소로 실제 커밋까지."""
import os, subprocess, tempfile
from pathlib import Path
from doc_template.render import render
from doc_template.publish import assets, publish

t = Path(tempfile.mkdtemp())
doc = t / 'doc'; (doc / 'img').mkdir(parents=True)
(doc / 'img' / 'flow.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
(doc / 'shot one.png').write_bytes(b'\x89PNG\r\n')
(doc / 'flow.html').write_text('<!doctype html><meta name="generator" content="archify 3.1.0"><p>도식</p>')
(doc / 'other.html').write_text('<!doctype html><p>아무 페이지</p>')
(doc / 'note.txt').write_text('x')
(t / 'secret.png').write_bytes(b'\x89PNG')
md = ('---\ntitle: 그림 문서\n---\n## 그림 | 흐름도는 함께 올라간다\n\n![흐름도](img/flow.svg "캡션")\n\n![스크린샷](shot%20one.png)\n\n'
      '[크게 보기](flow.html) · [다른 페이지](other.html) · [메모](note.txt) · [밖](../secret.png) · [주소](https://ex.com/a.png) · [절대](/etc/passwd)\n')
h, _ = render(md)
src = doc / 'index.html'; src.write_text(h)
got = sorted(rel for _, rel in assets(src))
assert got == ['flow.html', 'img/flow.svg', 'shot one.png'], got

# 로컬 bare 저장소에 실제로 올려 본다(gh·네트워크 없이)
bare = t / 'pages.git'; subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True)
cache_root = t / 'cache'; cache = cache_root / 'me__pages'
subprocess.run(['git', 'clone', '-q', str(bare), str(cache)], check=True, capture_output=True)
for k, v in (('user.name', 't'), ('user.email', 't@t')): subprocess.run(['git', '-C', str(cache), 'config', k, v], check=True)
(cache / 'CNAME').write_text('127.0.0.1:9')
subprocess.run(['git', '-C', str(cache), 'add', 'CNAME'], check=True); subprocess.run(['git', '-C', str(cache), 'commit', '-qm', 'init'], check=True)
subprocess.run(['git', '-C', str(cache), 'push', '-q', 'origin', 'HEAD:main'], check=True, capture_output=True)
subprocess.run(['git', '-C', str(cache), 'branch', '-q', '--set-upstream-to=origin/main'], check=True)
os.environ['DOC_TEMPLATE_CACHE'] = str(cache_root)
res = publish(src, 'figure-doc', repo='me/pages', wait=0)
listed = subprocess.run(['git', '--git-dir', str(bare), 'ls-tree', '-r', '--name-only', 'main'], capture_output=True, text=True, check=True).stdout.splitlines()
assert sorted(x for x in listed if x.startswith('figure-doc/')) == ['figure-doc/flow.html', 'figure-doc/img/flow.svg', 'figure-doc/index.html', 'figure-doc/shot one.png'], listed
assert res['changed'] and len(res['files']) == 4
print('PASS publish assets: relative images and diagram html only, committed to pages repo')
