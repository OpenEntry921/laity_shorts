"""Inspect supplied MP4s and extract posters; never changes the MP4 bytes."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from build import build

ROOT = Path(__file__).resolve().parent.parent


def refresh(reel=None):
    items = json.loads((ROOT / 'media.json').read_text())
    selected = [i for i in items if reel is None or i['reel_id'] == reel]
    if not selected: raise ValueError('Unknown reel ID')
    for item in selected:
        binary = ROOT / 'public/videos' / item['video']
        metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(binary)]))
        video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
        item.update(duration=float(metadata['format']['duration']), bytes=binary.stat().st_size,
                    sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                    width=video['width'], height=video['height'], video_codec=video['codec_name'],
                    audio=[s['codec_name'] for s in metadata['streams'] if s['codec_type'] == 'audio'])
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '2', '-i', str(binary), '-frames:v', '1', '-q:v', '2', str(ROOT / 'public/posters' / item['poster'])], check=True)
    (ROOT / 'media.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n')
    build()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--reel')
    refresh(parser.parse_args().reel)
