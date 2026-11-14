"""Generate static pages and content-versioned URLs; standard Python only."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


REELS = {'responsibility': 'responsibility', 'offering': 'essence', 'example': 'prayer'}


def render(items, start=None):
    players = []
    start = start or items[0]['id']
    start_index = next(i for i, item in enumerate(items) if item['id'] == start)
    ordered = items[start_index:] + items[:start_index]
    order = {item['id']: i for i, item in enumerate(items)}
    for item in ordered:
        key = item['id']
        video = ROOT / 'public/videos' / (key + '.mp4')
        poster = ROOT / 'public/posters' / (key + '.jpg')
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        if digest != item['sha256']:
            raise ValueError(f'{key}: update media.json after verifying the replacement upload')
        poster_hash = hashlib.sha256(poster.read_bytes()).hexdigest()
        label = html.escape(item['label'], quote=True)
        reel = REELS[key]
        players.append(f'''<section class="clip" data-reel="{reel}" data-order="{order[key]}" aria-label="{label}">
<div class="player">
<video controls playsinline preload="none" tabindex="0" aria-label="{label}" poster="/posters/{key}.jpg?v={poster_hash[:16]}">
<source src="/videos/{key}.mp4?v={digest[:16]}" type="video/mp4">
</video>
<button class="play" type="button" aria-label="{label} 재생" hidden><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M11 6v20l16-10z"/></svg></button>
<div class="failure" hidden><p role="status" aria-live="polite">영상을 불러오지 못했습니다. 다시 시도해 주세요.</p><button class="retry" type="button">다시 시도</button></div>
</div>
</section>''')
    return '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><meta name="robots" content="noindex, nofollow"><title>영상</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/player.css"><script src="/player.js"></script></head>
<body>''' + f'<main id="feed" data-start="{REELS[start]}" tabindex="0" aria-label="릴스 영상">' + '\n'.join(players) + f'</main><div class="reel-count" aria-hidden="true">{start_index + 1} / 3</div><p class="swipe-hint" hidden>위로 넘겨 다음 영상 보기</p></body></html>\n'


def build():
    items = json.loads((ROOT / 'media.json').read_text())
    (ROOT / 'public/index.html').write_text(render(items))
    for number, item in enumerate(items, 1):
        (ROOT / f'public/video-{number}.html').write_text(render(items, start=item['id']))


if __name__ == '__main__':
    build()
