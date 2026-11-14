"""Generate static pages and content-versioned URLs; standard Python only."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render(items):
    players = []
    for item in items:
        key = item['id']
        video = ROOT / 'public/videos' / (key + '.mp4')
        poster = ROOT / 'public/posters' / (key + '.jpg')
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        if digest != item['sha256']:
            raise ValueError(f'{key}: update media.json after verifying the replacement upload')
        poster_hash = hashlib.sha256(poster.read_bytes()).hexdigest()
        label = html.escape(item['label'], quote=True)
        players.append(f'''<section class="clip" aria-label="{label}">
<div class="player">
<video controls playsinline preload="none" tabindex="0" aria-label="{label}" poster="/posters/{key}.jpg?v={poster_hash[:16]}">
<source src="/videos/{key}.mp4?v={digest[:16]}" type="video/mp4">
</video>
<button class="play" type="button" aria-label="{label} 재생" hidden><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M11 6v20l16-10z"/></svg></button>
<div class="failure" hidden><p role="status" aria-live="polite">영상을 불러오지 못했습니다. 다시 시도해 주세요.</p><button class="retry" type="button">다시 시도</button></div>
</div>
</section>''')
    return '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex, nofollow"><title>영상</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/player.css"><script defer src="/player.js"></script></head>
<body><main>''' + '\n'.join(players) + '</main></body></html>\n'


def build():
    items = json.loads((ROOT / 'media.json').read_text())
    (ROOT / 'public/index.html').write_text(render(items))
    for number, item in enumerate(items, 1):
        (ROOT / f'public/video-{number}.html').write_text(render([item]))


if __name__ == '__main__':
    build()
