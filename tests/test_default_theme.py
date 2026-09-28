from doc_template.render import render

def test_default_and_explicit_theme():
    md = '# 제목\n\n## 결론\n본문'
    assert render(md)[1]['theme'] == 'mono'
    assert render(md, theme='t1')[1]['theme'] == 't1'
    assert render('---\ntheme: t2\n---\n' + md)[1]['theme'] == 't2'
