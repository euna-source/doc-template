from doc_template.render import render
h,_=render('---\ntitle: 테스트\n---\n## 설명 | 설명입니다\n첫 문장입니다.  \n같은 문단의 다음 의미입니다.\n\n새 문단입니다.\n이어 쓰는 문장입니다.\n')
assert '<br class="prose-break"' in h
assert '<p>새 문단입니다.\n이어 쓰는 문장입니다.</p>' in h
assert '@media(max-width:600px){br.prose-break{display:none}}' in h
print('PASS paragraph boundaries and optional mobile break')
