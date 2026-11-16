import copy
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
ITEMS = json.loads((ROOT / 'media.json').read_text())
ORIGINAL_HASHES = {
    'responsibility': 'd68992e2ac642092dee5deca8a167fc41f9509f523a678d8d1a24afc72cc2ae1',
    'offering': '4f4a5b2d377e129ee05d8cd009c97b0d60db2cc846dbab6c643d2fa952c450ae',
    'example': 'dc670f192f40e0c3d6a45af3ef1de542b1b54ece7de10bde7644ae5c19d058b6',
}


class SiteTests(unittest.TestCase):
    def test_upload_integrity(self):
        self.assertEqual([i['id'] for i in ITEMS[:3]], ['responsibility', 'offering', 'example'])
        for item in ITEMS:
            with self.subTest(video=item['id']):
                binary = ROOT / 'public/videos' / item['video']
                self.assertEqual(binary.stat().st_size, item['bytes'])
                digest = hashlib.sha256(binary.read_bytes()).hexdigest()
                self.assertEqual(digest, item['sha256'])
                if item['id'] in ORIGINAL_HASHES: self.assertEqual(digest, ORIGINAL_HASHES[item['id']])
                self.assertFalse(binary.read_bytes().startswith(b'version https://git-lfs'))
                self.assertTrue((ROOT / 'public/posters' / item['poster']).read_bytes().startswith(b'\xff\xd8'))

    def test_all_publication_states_and_no_stale_output(self):
        with tempfile.TemporaryDirectory() as d:
            manifest, output = Path(d) / 'media.json', Path(d) / 'dist'
            # Reuse one output through withdrawals and additions; stale files must disappear.
            for count in [3, 0, 2, 1]:
                items = copy.deepcopy(ITEMS[:3])
                for index, item in enumerate(items): item['published'] = index < count
                manifest.write_text(json.dumps(items))
                site = build.build(manifest, output)
                index = (site / 'index.html').read_text()
                self.assertEqual(index.count('<video '), count)
                if count == 0: self.assertIn('공개된 영상이 아직 없습니다.', index)
                self.assertEqual('class="reel-count"' in index, count > 1)
                for number, item in enumerate(items, 1):
                    single = (site / ('reel-' + item['reel_id'] + '.html')).read_text()
                    self.assertEqual(single, (site / f'video-{number}.html').read_text())
                    self.assertNotIn('class="reel-count"', single)
                    self.assertEqual(single.count('<video '), int(item['published']))
                    for other in items:
                        if other is not item:
                            for value in (other['label'], other['video'], other['poster']): self.assertNotIn(value, single)
                    if not item['published']:
                        for value in (item['label'], item['video'], item['poster']): self.assertNotIn(value, single)
                        self.assertIn('아직 공개되지 않은 영상입니다.', single)
                    for folder, field in [('videos', 'video'), ('posters', 'poster')]:
                        target = site / folder / item[field]
                        self.assertEqual(target.exists(), item['published'])
                        if item['published']: self.assertEqual(target.read_bytes(), (ROOT / 'public' / folder / item[field]).read_bytes())
                    self.assertIn('~^' + item['reel_id'] + '$', (output / 'reel-map.conf').read_text())
                self.assertFalse((site / 'media.json').exists())
                for page in site.glob('*.html'):
                    text = page.read_text()
                    self.assertIn('noindex, nofollow', text)
                    for token in (' autoplay', ' loop', '<iframe', '<nav', '<header', '<footer', '<form', 'laity.kr', 'https://', '/workspace', 'sandbox:'):
                        self.assertNotIn(token, text)
                    n = text.count('<video ')
                    self.assertEqual(text.count('controls playsinline preload="none"'), n)
                    self.assertEqual(text.count('class="play"'), n)
                    self.assertEqual(text.count('class="failure" hidden'), n)

    def test_omitted_publication_is_private_and_dates_do_not_release(self):
        with tempfile.TemporaryDirectory() as d:
            items = copy.deepcopy(ITEMS)
            for item in items:
                item.pop('published', None)
                item['send_date'] = '2000-01-01'
            manifest = Path(d) / 'media.json'; manifest.write_text(json.dumps(items))
            site = build.build(manifest, Path(d) / 'dist')
            self.assertNotIn('<video ', (site / 'index.html').read_text())
            self.assertFalse((site / 'videos').exists())

    def test_added_reel_defaults_to_private_and_preserves_old_links(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(ROOT / 'public', root / 'public')
            items = copy.deepcopy(ITEMS)
            extra = copy.deepcopy(items[0])
            extra.update(id='fixture-new', reel_id='fixture-new', label='Isolated routing fixture', video='fixture-new.mp4', poster='fixture-new.jpg')
            extra.pop('published', None)
            shutil.copyfile(root / 'public/videos' / items[0]['video'], root / 'public/videos/fixture-new.mp4')
            shutil.copyfile(root / 'public/posters' / items[0]['poster'], root / 'public/posters/fixture-new.jpg')
            items.append(extra)
            manifest = root / 'media.json'; manifest.write_text(json.dumps(items))
            output = root / 'dist'; site = build.build(manifest, output, root)
            self.assertNotIn(extra['label'], (site / 'index.html').read_text())
            self.assertFalse((site / 'videos/fixture-new.mp4').exists())
            old_pages = [(site / ('reel-' + i['reel_id'] + '.html')).read_text() for i in items[:3]]
            extra['published'] = True; manifest.write_text(json.dumps(items))
            site = build.build(manifest, output, root)
            self.assertTrue((site / 'videos/fixture-new.mp4').exists())
            self.assertIn('~^fixture-new$ reel-fixture-new.html;', (output / 'reel-map.conf').read_text())
            self.assertEqual(old_pages, [(site / ('reel-' + i['reel_id'] + '.html')).read_text() for i in items[:3]])

    def test_invalid_config_fails_before_output_cleanup(self):
        for change in [lambda x: x[0].update(published='true'), lambda x: x[1].update(reel_id=x[0]['reel_id']), lambda x: x[0].update(video='../escape.mp4'), lambda x: x[0].update(sha256='0' * 64)]:
            with tempfile.TemporaryDirectory() as d:
                items = copy.deepcopy(ITEMS); change(items)
                manifest = Path(d) / 'media.json'; manifest.write_text(json.dumps(items))
                output = Path(d) / 'out'; output.mkdir(); (output / 'sentinel').write_text('keep')
                with self.assertRaises(ValueError): build.build(manifest, output)
                self.assertEqual((output / 'sentinel').read_text(), 'keep')


if __name__ == '__main__': unittest.main()
