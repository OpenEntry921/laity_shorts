import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('SHORTS_BASE_URL', 'http://127.0.0.1:18080')
ITEMS = json.loads(Path(os.environ.get('SHORTS_MANIFEST', ROOT / 'media.json')).read_text())
PUBLISHED = [i for i in ITEMS if i.get('published', False)]


class HTTPTests(unittest.TestCase):
    def test_routes_and_private_cache(self):
        queries = ['', '?reel=wrong', '?reel=', '?reel=ESSENCE', '?v=2']
        queries += ['?reel=' + i['reel_id'] for i in ITEMS]
        queries += ['/video-' + str(n) + '.html' for n in range(1, len(ITEMS) + 1)]
        for query in queries:
            with self.subTest(query=query), urlopen(BASE + (query if query.startswith('/') else '/' + query)) as response:
                text = response.read().decode()
                selected = next((i for i in ITEMS if query == '?reel=' + i['reel_id']), None)
                if query.startswith('/video-'): selected = ITEMS[int(query.split('-')[1].split('.')[0]) - 1]
                expected = [selected] if selected and selected.get('published', False) else ([] if selected else PUBLISHED)
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), 'text/html')
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
                self.assertEqual(text.count('<video '), len(expected))
                if selected and not expected: self.assertIn('아직 공개되지 않은 영상입니다.', text)
                if not selected and not expected: self.assertIn('공개된 영상이 아직 없습니다.', text)
                for item in ITEMS:
                    if item in expected: self.assertIn('/videos/' + item['video'] + '?', text)
                    else:
                        for value in (item['label'], item['video'], item['poster']): self.assertNotIn(value, text)

    def test_original_video_bytes_mime_ranges_and_version_cache(self):
        for item in ITEMS:
            with self.subTest(video=item['id']):
                logical = '/videos/' + item['video']
                if not item.get('published', False):
                    for url in [logical, logical + '?v=' + item['sha256'][:16], '/posters/' + item['poster']]:
                        with self.assertRaises(HTTPError) as error: urlopen(BASE + url)
                        self.assertEqual(error.exception.code, 404)
                    continue
                local = (ROOT / 'public/videos' / item['video']).read_bytes()
                with urlopen(BASE + logical) as response:
                    self.assertEqual(response.headers.get_content_type(), 'video/mp4')
                    self.assertEqual(hashlib.sha256(response.read()).hexdigest(), item['sha256'])
                    self.assertEqual(response.headers['Cache-Control'], 'no-cache')
                    self.assertEqual(response.headers['Accept-Ranges'], 'bytes')
                with urlopen(Request(BASE + logical, headers={'Range': 'bytes=1000-2023'})) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), local[1000:2024])
                    self.assertEqual(response.headers['Content-Range'], f'bytes 1000-2023/{len(local)}')
                with urlopen(BASE + logical + '?v=' + item['sha256'][:16]) as response: self.assertIn('immutable', response.headers['Cache-Control'])
                with urlopen(BASE + '/posters/' + item['poster']) as response:
                    self.assertEqual(response.headers.get_content_type(), 'image/jpeg')
                    self.assertEqual(response.read(), (ROOT / 'public/posters' / item['poster']).read_bytes())

    def test_missing_file_is_an_actual_404(self):
        for name in ['/videos/not-present.mp4', '/media.json']:
            with self.assertRaises(HTTPError) as error: urlopen(BASE + name)
            self.assertEqual(error.exception.code, 404)


if __name__ == '__main__': unittest.main()
