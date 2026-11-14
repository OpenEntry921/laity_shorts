"""Run after copying replacement uploads; never encodes or modifies MP4 files."""
import hashlib
import json
import subprocess
from pathlib import Path
from build import build

ROOT = Path(__file__).resolve().parent.parent
items = json.loads((ROOT / 'media.json').read_text())
for item in items:
    binary = ROOT / 'public/videos' / (item['id'] + '.mp4')
    metadata = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(binary),
    ]))
    video = next(stream for stream in metadata['streams'] if stream['codec_type'] == 'video')
    item.update(duration=float(metadata['format']['duration']), bytes=binary.stat().st_size,
                sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                width=video['width'], height=video['height'], video_codec=video['codec_name'],
                audio=[s['codec_name'] for s in metadata['streams'] if s['codec_type'] == 'audio'])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '2', '-i', str(binary),
                    '-frames:v', '1', '-q:v', '2',
                    str(ROOT / 'public/posters' / (item['id'] + '.jpg'))], check=True)
(ROOT / 'media.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n')
build()
