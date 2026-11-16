"""Build/run four isolated release fixtures; never changes repository publication flags."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def verify(browser=False):
    artifacts = Path(os.environ.get('SHORTS_ARTIFACTS', '/tmp/shorts-publication'))
    artifacts.mkdir(parents=True, exist_ok=True)
    results = []
    for count in range(4):
        with tempfile.TemporaryDirectory(prefix='shorts-publication-') as d:
            context = Path(d)
            for filename in ('Dockerfile', '.dockerignore', 'nginx.conf', 'nginx-main.conf'):
                shutil.copyfile(ROOT / filename, context / filename)
            shutil.copytree(ROOT / 'public', context / 'public')
            (context / 'scripts').mkdir()
            shutil.copyfile(ROOT / 'scripts/build.py', context / 'scripts/build.py')
            items = json.loads((ROOT / 'media.json').read_text())
            for index, item in enumerate(items): item['published'] = index < count
            manifest = context / 'media.json'; manifest.write_text(json.dumps(items))
            tag = 'laity-shorts:publication-test-' + str(count)
            name = 'shorts-publication-' + str(os.getpid()) + '-' + str(count)
            port = 18280 + count
            with (artifacts / ('docker-' + str(count) + '.log')).open('w') as log:
                run('docker', 'build', '-t', tag, str(context), stdout=log, stderr=subprocess.STDOUT)
            run('docker', 'run', '--rm', '--read-only', '--tmpfs', '/tmp:rw,nosuid,noexec,uid=101,gid=101,mode=0700', tag, '-t')
            try:
                run('docker', 'run', '-d', '--name', name, '--user', '12345:23456', '--read-only', '--tmpfs', '/tmp:rw,nosuid,noexec,uid=12345,gid=23456,mode=0700', '--cap-drop=ALL', '--security-opt=no-new-privileges', '-p', '127.0.0.1:' + str(port) + ':8080', tag)
                base = 'http://127.0.0.1:' + str(port)
                for attempt in range(30):
                    try:
                        with urlopen(base, timeout=1) as response:
                            if response.status == 200: break
                    except OSError: time.sleep(.25)
                else: raise AssertionError('Nginx did not become ready')
                env = dict(os.environ, SHORTS_BASE_URL=base, SHORTS_MANIFEST=str(manifest), SHORTS_ARTIFACTS=str(artifacts / str(count)))
                run(sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_http.py', '-v', cwd=ROOT, env=env)
                # Files must be absent from the final image, including outside the document root.
                inventory = subprocess.check_output(['docker', 'exec', name, 'find', '/usr/share/nginx/html', '-type', 'f', '-name', '*.mp4'], text=True, stderr=subprocess.DEVNULL).splitlines()
                run('docker', 'exec', name, 'test', '!', '-d', '/build')
                assert sorted(inventory) == sorted('/usr/share/nginx/html/videos/' + i['video'] for i in items if i['published']), inventory
                posters = subprocess.check_output(['docker', 'exec', name, 'find', '/usr/share/nginx/html/posters', '-type', 'f'], text=True, stderr=subprocess.DEVNULL).splitlines() if count else []
                assert sorted(posters) == sorted('/usr/share/nginx/html/posters/' + i['poster'] for i in items if i['published'])
                if browser: run('node', 'tests/browser.cjs', cwd=ROOT, env=env)
                status = subprocess.check_output(['docker', 'inspect', '--format', '{{.State.Running}}/{{.RestartCount}}', name], text=True).strip()
                uid = subprocess.check_output(['docker', 'exec', name, 'id', '-u'], text=True).strip()
                assert status == 'true/0' and uid == '12345', (status, uid)
                results.append(dict(published=count, nginx='pass', http='pass', finalImageInventory='pass', numericUID=uid, running=status, browser='pass' if browser else 'not run'))
            finally:
                run('docker', 'rm', '-f', name, stdout=subprocess.DEVNULL)
    (artifacts / 'publication-results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--browser', action='store_true')
    verify(parser.parse_args().browser)
