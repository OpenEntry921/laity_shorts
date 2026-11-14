const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.SHORTS_BASE_URL || 'http://127.0.0.1:18080';
const artifacts = process.env.SHORTS_ARTIFACTS || '/tmp/laity-shorts-artifacts';
const reels = ['responsibility', 'essence', 'prayer'];
fs.mkdirSync(artifacts, { recursive: true });

async function aligned(page, id) {
  await page.waitForFunction(id => {
    const clip = document.querySelector('.clip[data-reel="' + id + '"]');
    return document.getElementById('feed').dataset.ready === 'true' &&
      new URL(location.href).searchParams.get('reel') === id &&
      Math.abs(clip.getBoundingClientRect().top) < 2;
  }, id);
}

async function move(page, direction, touch) {
  const { width, height } = page.viewportSize();
  if (touch) {
    const session = await page.context().newCDPSession(page);
    const x = width * .5;
    const start = height * (direction > 0 ? .8 : .2);
    const end = height * (direction > 0 ? .2 : .8);
    await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y: start }] });
    for (let i = 1; i <= 10; i++) {
      await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y: start + (end - start) * i / 10 }] });
      await page.waitForTimeout(16);
    }
    await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await session.detach();
  } else {
    await page.mouse.move(width * .5, height * .45);
    await page.mouse.wheel(0, direction * height * .85);
  }
}

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
  const results = [];
  try {
    for (const [width, height] of [[360, 800], [390, 844], [1440, 1000], [844, 390]]) {
      const touch = width < 500 || height < 500;
      const context = await browser.newContext({ viewport: { width, height }, isMobile: touch, hasTouch: touch });
      for (const [query, expected] of [['', reels[0]], ...reels.map(id => ['?reel=' + id, id]), ['?reel=bad', reels[0]]]) {
        const page = await context.newPage();
        const errors = [], failures = [], mediaRequests = [];
        page.on('pageerror', e => errors.push(e.message));
        page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
        page.on('request', r => { assert.equal(new URL(r.url()).origin, new URL(base).origin); if (r.resourceType() === 'media') mediaRequests.push(r.url()); });
        page.on('response', r => { if (r.status() >= 400) failures.push([r.status(), r.url()]); });
        await page.addInitScript(() => {
          window.firstVisibleReel = null;
          function sample() {
            const feed = document.getElementById('feed');
            if (feed && getComputedStyle(feed).visibility !== 'hidden') {
              const clip = [...feed.querySelectorAll('.clip')].find(c => {
                const box = c.getBoundingClientRect(); return box.top <= innerHeight / 2 && box.bottom > innerHeight / 2;
              });
              if (clip) { window.firstVisibleReel = clip.dataset.reel; return; }
            }
            requestAnimationFrame(sample);
          }
          requestAnimationFrame(sample);
        });
        await page.goto(base + '/' + query);
        await aligned(page, expected);
        await page.waitForFunction(() => window.firstVisibleReel !== null);
        assert.equal(await page.evaluate(() => window.firstVisibleReel), expected, 'first visible frame must be the linked reel');
        assert.equal(await page.locator('video').count(), 3);
        assert.deepEqual(await page.locator('.clip').evaluateAll(nodes => [...nodes].sort((a, b) => a.offsetTop - b.offsetTop).map(n => n.dataset.reel)), reels);
        assert.equal(await page.locator('nav,header,footer,a,form,input,iframe').count(), 0);
        assert.equal(await page.locator('.failure:visible').count(), 0);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        const clip = page.locator('.clip[data-reel="' + expected + '"]');
        assert.equal(await clip.locator('video').evaluate(v => v.paused && v.currentTime === 0 && v.playsInline && v.preload === 'none' && !v.autoplay && !v.loop && getComputedStyle(v).objectFit === 'contain'), true);
        const box = await clip.locator('.play').boundingBox();
        assert.ok(box.width >= 64 && box.height >= 64 && box.y >= 0 && box.y + box.height <= height);
        assert.equal(mediaRequests.length, 0);
        await page.screenshot({ path: path.join(artifacts, width + '-' + height + '-' + expected + '.png') });
        await page.reload();
        await aligned(page, expected);
        await page.waitForFunction(() => window.firstVisibleReel !== null);
        assert.equal(await page.evaluate(() => window.firstVisibleReel), expected);
        assert.equal(mediaRequests.length, 0);
        assert.deepEqual(errors, []); assert.deepEqual(failures, []);
        await page.close();
      }
      const page = await context.newPage();
      const playbackErrors = [];
      page.on('pageerror', e => playbackErrors.push(e.message));
      page.on('console', m => { if (m.type() === 'error') playbackErrors.push(m.text()); });
      await page.goto(base + '/');
      await aligned(page, reels[0]);
      const historyLength = await page.evaluate(() => history.length);
      for (let index = 0; index < 3; index++) {
        const player = page.locator('.clip[data-reel="' + reels[index] + '"] .player');
        await player.locator('.play').focus(); await page.keyboard.press('Enter');
        await page.waitForFunction(i => { const v = document.querySelectorAll('video')[i]; return !v.paused && v.currentTime > 0 && v.readyState >= 3; }, index);
        const video = player.locator('video');
        assert.equal(await video.evaluate(v => v.controls), true);
        await video.evaluate(v => v.pause());
        await video.evaluate(v => new Promise((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('seek timeout')), 10000);
          v.addEventListener('seeked', () => { clearTimeout(timeout); resolve(); }, { once: true }); v.currentTime = 10;
        }));
        assert.equal(await video.evaluate(v => Math.abs(v.currentTime - 10) < .2), true);
        await video.evaluate(v => v.requestFullscreen());
        assert.equal(await page.evaluate(() => document.fullscreenElement?.tagName), 'VIDEO');
        await page.evaluate(() => document.exitFullscreen());
        await player.locator('.play').click();
        await page.waitForFunction(i => !document.querySelectorAll('video')[i].paused, index);
        if (index < 2) {
          await move(page, 1, touch);
          await aligned(page, reels[index + 1]);
          assert.equal(await video.evaluate(v => v.paused), true, 'scrolling away must pause the old video');
        }
      }
      assert.equal(await page.evaluate(() => history.length), historyLength, 'scroll must not add history entries');
      await move(page, -1, touch); await aligned(page, reels[1]);
      await move(page, -1, touch); await aligned(page, reels[0]);
      assert.equal(await page.evaluate(() => history.length), historyLength);
      assert.deepEqual(playbackErrors, []);
      await page.goto(base + '/?reel=essence');
      await aligned(page, reels[1]);
      await page.setViewportSize({ width: height, height: width });
      await aligned(page, reels[1]);
      await page.close();
      results.push({ width, height, firstFrameAndReload: 'pass', allThreeDistinct: true, navigation: touch ? 'simulated touch swipe pass' : 'mouse wheel pass', pauseOnLeave: 'pass', replaceStateNoHistoryGrowth: 'pass', playbackPauseSeekFullscreen: 'all three pass', resize: 'pass', initialMP4Requests: 0, consoleErrors: [] });
      await context.close();
    }
    const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const fallback = await nojs.newPage();
    await fallback.goto(base + '/?reel=prayer');
    assert.equal(await fallback.locator('video').count(), 3);
    assert.equal(await fallback.locator('.clip').first().getAttribute('data-reel'), 'prayer');
    assert.equal(await fallback.locator('video').first().evaluate(v => v.controls), true);
    await nojs.close();
    const page = await browser.newPage();
    await page.route('**/videos/responsibility.mp4*', r => r.fulfill({ status: 404, contentType: 'text/plain', body: 'test failure' }));
    await page.goto(base + '/'); await aligned(page, reels[0]);
    await page.locator('.clip').first().locator('.play').click();
    await page.locator('.clip').first().locator('.failure').waitFor({ state: 'visible' });
    await page.unroute('**/videos/responsibility.mp4*');
    await page.locator('.clip').first().locator('.retry').click();
    await page.waitForFunction(() => !document.querySelector('video').paused && document.querySelector('video').currentTime > 0);
    await page.close();
    fs.writeFileSync(path.join(artifacts, 'browser-results.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
    console.log('PASS: no-JS fallback and load-error retry');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
