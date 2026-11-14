import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('SHORTS_BASE_URL', 'http://127.0.0.1:18080')


class HTTPTests(unittest.TestCase):
    def test_routes_and_private_cache(self):
        ids = ['responsibility', 'offering', 'example']
        for query, selected in [('', ids), ('?v=1', ids[:1]), ('?v=2', ids[1:2]), ('?v=3', ids[2:]), ('?v=0', ids), ('?v=4', ids), ('?v=abc', ids), ('?v=', ids), ('?v=01', ids), ('?v=../../', ids)]:
            with self.subTest(query=query), urlopen(BASE + '/' + query) as response:
                html = response.read().decode()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers.get_content_type(), 'text/html')
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertEqual(response.headers['X-Robots-Tag'], 'noindex, nofollow')
                self.assertEqual(html.count('<video '), len(selected))
                for key in ids:
                    self.assertEqual(f'/videos/{key}.mp4?' in html, key in selected)

    def test_original_video_bytes_mime_ranges_and_version_cache(self):
        for item in json.loads((ROOT / 'media.json').read_text()):
            with self.subTest(video=item['id']):
                local = (ROOT / 'public/videos' / (item['id'] + '.mp4')).read_bytes()
                logical = '/videos/' + item['id'] + '.mp4'
                with urlopen(BASE + logical) as response:
                    self.assertEqual(response.headers.get_content_type(), 'video/mp4')
                    self.assertEqual(hashlib.sha256(response.read()).hexdigest(), item['sha256'])
                    self.assertEqual(response.headers['Cache-Control'], 'no-cache')
                    self.assertEqual(response.headers['Accept-Ranges'], 'bytes')
                with urlopen(Request(BASE + logical, headers={'Range': 'bytes=1000-2023'})) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), local[1000:2024])
                    self.assertEqual(response.headers['Content-Range'], f'bytes 1000-2023/{len(local)}')
                with urlopen(BASE + logical + '?v=' + item['sha256'][:16]) as response:
                    self.assertIn('immutable', response.headers['Cache-Control'])
                poster = (ROOT / 'public/posters' / (item['id'] + '.jpg')).read_bytes()
                with urlopen(BASE + '/posters/' + item['id'] + '.jpg') as response:
                    self.assertEqual(response.headers.get_content_type(), 'image/jpeg')
                    self.assertEqual(response.read(), poster)

    def test_missing_file_is_an_actual_404(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(BASE + '/videos/not-present.mp4')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
