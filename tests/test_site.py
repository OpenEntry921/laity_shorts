import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class SiteTests(unittest.TestCase):
    def test_upload_integrity(self):
        items = json.loads((ROOT / 'media.json').read_text())
        self.assertEqual([item['id'] for item in items], ['responsibility', 'offering', 'example'])
        self.assertEqual(len({item['sha256'] for item in items}), 3)
        for item in items:
            with self.subTest(video=item['id']):
                binary = ROOT / 'public/videos' / (item['id'] + '.mp4')
                self.assertEqual(binary.stat().st_size, item['bytes'])
                self.assertEqual(hashlib.sha256(binary.read_bytes()).hexdigest(), item['sha256'])
                self.assertFalse(binary.read_bytes().startswith(b'version https://git-lfs'))
                self.assertTrue((ROOT / 'public/posters' / (item['id'] + '.jpg')).read_bytes().startswith(b'\xff\xd8'))

    def test_generated_pages_match_current_assets(self):
        items = json.loads((ROOT / 'media.json').read_text())
        self.assertEqual((ROOT / 'public/index.html').read_text(), build.render(items))
        for number, item in enumerate(items, 1):
            self.assertEqual((ROOT / f'public/video-{number}.html').read_text(), build.render(items, start=item['id']))

    def test_pages_keep_native_fallback_and_no_extra_ui(self):
        for page in (ROOT / 'public').glob('*.html'):
            html = page.read_text()
            self.assertIn('noindex, nofollow', html)
            for token in (' autoplay', ' loop', '<iframe', '<nav', '<header', '<footer', '<form', 'laity.kr', 'https://', '/workspace', 'sandbox:'):
                self.assertNotIn(token, html)
            count = html.count('<video ')
            self.assertEqual(html.count('controls playsinline preload="none"'), count)
            self.assertEqual(html.count('class="play"'), count)
            self.assertEqual(html.count('class="failure" hidden'), count)


if __name__ == '__main__':
    unittest.main()
