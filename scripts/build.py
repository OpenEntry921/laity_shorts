"""Build a clean, publication-filtered static output; standard Python only."""
import argparse
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex, nofollow"><title>영상</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/player.css"><script src="/player.js"></script></head><body>'''


def load_items(manifest=ROOT / 'media.json', root=ROOT):
    items = json.loads(Path(manifest).read_text())
    seen = set()
    files = set()
    for item in items:
        reel = item['reel_id']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', reel) or reel in seen:
            raise ValueError('Reel IDs must be unique lowercase slugs')
        seen.add(reel)
        if not isinstance(item.get('published', False), bool):
            raise ValueError('published must be a JSON boolean')
        for kind, extension, folder in [('video', '.mp4', 'videos'), ('poster', '.jpg', 'posters')]:
            name = item[kind]
            if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*', name) or not name.endswith(extension) or name in files:
                raise ValueError('Media filenames must be unique, local basenames')
            files.add(name)
            path = root / 'public' / folder / name
            if not path.is_file():
                raise ValueError(f'Missing original {name}')
        binary = root / 'public/videos' / item['video']
        if binary.stat().st_size != item['bytes'] or hashlib.sha256(binary.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f'{reel}: original MP4 integrity mismatch')
    return items


def render(items, single=False, root=ROOT, message=''):
    players = []
    for index, item in enumerate(items):
        digest = item['sha256']
        poster_hash = hashlib.sha256((root / 'public/posters' / item['poster']).read_bytes()).hexdigest()
        label = html.escape(item['label'], quote=True)
        reel = item['reel_id']
        players.append(f'''<section class="clip" data-reel="{reel}" data-order="{index}" aria-label="{label}">
<div class="player">
<video controls playsinline preload="none" tabindex="0" aria-label="{label}" poster="/posters/{item['poster']}?v={poster_hash[:16]}">
<source src="/videos/{item['video']}?v={digest[:16]}" type="video/mp4">
</video>
<button class="play" type="button" aria-label="{label} 재생" hidden><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M11 6v20l16-10z"/></svg></button>
<div class="failure" hidden><p role="status" aria-live="polite">영상을 불러오지 못했습니다. 다시 시도해 주세요.</p><button class="retry" type="button">다시 시도</button></div>
</div>
</section>''')
    mode = 'single' if single else 'feed'
    content = '\n'.join(players) if players else '<p class="empty">' + html.escape(message or '공개된 영상이 아직 없습니다.') + '</p>'
    chrome = f'<div class="reel-count" aria-hidden="true">1 / {len(items)}</div><p class="swipe-hint" hidden>위로 넘겨 다음 영상 보기</p>' if len(items) > 1 else ''
    return HEAD + f'<main id="feed" data-mode="{mode}" tabindex="0" aria-label="릴스 영상">' + content + '</main>' + chrome + '</body></html>\n'


def build(manifest=ROOT / 'media.json', output=ROOT / 'dist', root=ROOT):
    output, root = Path(output).resolve(), Path(root).resolve()
    # Never allow the cleanup target to contain source files or a parent checkout.
    if output == root or output in root.parents or output == root / 'public' or root / 'public' in output.parents:
        raise ValueError('Output must be separate from source')
    items = load_items(manifest, root)
    if output.exists():
        shutil.rmtree(output)
    site = output / 'site'
    site.mkdir(parents=True)
    for filename in ('player.css', 'player.js', 'favicon.svg'):
        shutil.copyfile(root / 'public' / filename, site / filename)
    published = [item for item in items if item.get('published', False)]
    (site / 'index.html').write_text(render(published, root=root))
    mapping = ['map $arg_reel $entry {', '    default index.html;']
    for number, item in enumerate(items, 1):
        reel = item['reel_id']
        page = render([item], single=True, root=root) if item.get('published', False) else render([], single=True, root=root, message='아직 공개되지 않은 영상입니다.')
        name = 'reel-' + reel + '.html'
        (site / name).write_text(page)
        # Preserve old static HTML links, but they follow the same publication gate.
        (site / f'video-{number}.html').write_text(page)
        mapping.append(f'    ~^{reel}$ {name};')
        if item.get('published', False):
            for field, folder in [('video', 'videos'), ('poster', 'posters')]:
                (site / folder).mkdir(exist_ok=True)
                shutil.copyfile(root / 'public' / folder / item[field], site / folder / item[field])
    mapping.append('}')
    (output / 'reel-map.conf').write_text('\n'.join(mapping) + '\n')
    return site


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, default=ROOT / 'media.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.manifest, args.output)
