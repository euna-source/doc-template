from pathlib import Path
from .themes import resolve, audit, ROOT

def theme_ids():
    return sorted(p.stem for p in (ROOT / 'themes').glob('*.json')) + ['mono', 'one:<#HEX 또는 t1~t6>']

def describe(spec):
    th = resolve(spec)
    return {'id': spec, 'name': th['meta'].get('name', spec), 'note': th['meta'].get('note', ''),
            'light': {k: th['light'][k] for k in ('bg', 'text', 'mark', 'accent', 'link')},
            'dark': {k: th['dark'][k] for k in ('bg', 'text', 'mark', 'accent', 'link')},
            'contrast_min': min(r[3] for r in audit(th))}

def all_themes():
    return [describe(s) for s in [p.stem for p in sorted((ROOT / 'themes').glob('*.json'))] + ['mono', 'one:t1']]
