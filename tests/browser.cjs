const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.SHORTS_BASE_URL || 'http://127.0.0.1:18080';
const artifacts = process.env.SHORTS_ARTIFACTS || '/tmp/laity-shorts-artifacts';
fs.mkdirSync(artifacts, { recursive: true });
const ids = ['responsibility', 'offering', 'example'];
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
  const results = [];
  try {
    for (const [width, height] of [[360, 800], [390, 844], [1440, 1000], [844, 390]]) {
      const context = await browser.newContext({ viewport: { width, height } });
      for (const [query, wanted] of [['', ids], ['?v=1', ids.slice(0, 1)], ['?v=2', ids.slice(1, 2)], ['?v=3', ids.slice(2)], ['?v=nope', ids]]) {
        const page = await context.newPage();
        const errors = [], mediaRequests = [], failed = [];
        page.on('pageerror', e => errors.push(e.message));
        page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
        page.on('request', r => { assert.equal(new URL(r.url()).origin, new URL(base).origin); if (r.resourceType() === 'media') mediaRequests.push(r.url()); });
        page.on('response', r => { if (r.status() >= 400) failed.push(r.url()); });
        await page.goto(base + '/' + query);
        assert.equal(await page.locator('video').count(), wanted.length);
        const sources = await page.locator('source').evaluateAll(nodes => nodes.map(n => new URL(n.src).pathname));
        assert.deepEqual(sources, wanted.map(id => '/videos/' + id + '.mp4'));
        assert.equal(mediaRequests.length, 0, 'no initial MP4 downloads');
        assert.equal(await page.locator('nav,header,footer,a,form,input,iframe').count(), 0);
        assert.equal(await page.locator('.failure:visible').count(), 0);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        const video = page.locator('video').first();
        assert.equal(await video.evaluate(v => v.paused && v.playsInline && v.preload === 'none' && !v.autoplay && !v.loop && getComputedStyle(v).objectFit === 'contain'), true);
        const button = page.locator('.play').first();
        const box = await button.boundingBox();
        assert.ok(box.width >= 64 && box.height >= 64 && box.x >= 0 && box.y >= 0 && box.x + box.width <= width && box.y + box.height <= height);
        await page.screenshot({ path: path.join(artifacts, (width + '-' + height + '-' + (query || 'all') + '.png').replaceAll('?', '')) });
        assert.deepEqual(errors, []); assert.deepEqual(failed, []);
        await page.close();
      }
      const page = await context.newPage();
      await page.goto(base);
      for (let index = 0; index < 3; index++) {
        console.log('Playback check', width, height, index + 1);
        const player = page.locator('.player').nth(index);
        await player.locator('.play').focus(); await page.keyboard.press('Enter');
        try {
          await page.waitForFunction(i => { const v = document.querySelectorAll('video')[i]; return !v.paused && v.currentTime > 0 && v.readyState >= 3; }, index);
        } catch (error) {
          console.error(await page.locator('video').evaluateAll(vs => vs.map(v => ({ paused: v.paused, time: v.currentTime, ready: v.readyState, error: v.error?.message }))));
          throw error;
        }
        const video = player.locator('video');
        assert.equal(await video.evaluate(v => v.controls), true);
        assert.equal(await page.locator('video').evaluateAll((videos, active) => videos.every((v, i) => i === active || v.paused), index), true);
        await video.evaluate(v => v.pause());
        assert.equal(await video.evaluate(v => v.paused), true);
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
      }
      assert.equal(await page.locator('video').evaluateAll(videos => videos[0].paused && videos[1].paused && !videos[2].paused), true);
      await page.close();
      results.push({ width, height, routes: 'all, v=1/2/3 and invalid pass', initialMP4Requests: 0, playbackPauseSeekFullscreen: 'all three pass', pauseOthers: 'pass', overflow: false, consoleErrors: [] });
      await context.close();
    }
    const native = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
    const nojs = await native.newPage();
    await nojs.goto(base + '/?v=3');
    assert.equal(await nojs.locator('video').count(), 1);
    assert.equal(await nojs.locator('video').evaluate(v => v.controls && !v.autoplay && !v.loop), true);
    assert.equal(await nojs.locator('.play:visible').count(), 0);
    await native.close();
    const page = await browser.newPage();
    const broken = '**/videos/responsibility.mp4*';
    await page.route(broken, route => route.fulfill({ status: 404, contentType: 'text/plain', body: 'test missing media' }));
    await page.goto(base + '/?v=1');
    await page.locator('.play').click();
    await page.locator('.failure').waitFor({ state: 'visible' });
    assert.equal(await page.locator('.failure p').innerText(), '영상을 불러오지 못했습니다. 다시 시도해 주세요.');
    await page.unroute(broken);
    await page.locator('.retry').click();
    await page.waitForFunction(() => !document.querySelector('video').paused && document.querySelector('video').currentTime > 0);
    assert.equal(await page.locator('.failure').isVisible(), false);
    await page.close();
    fs.writeFileSync(path.join(artifacts, 'browser-results.json'), JSON.stringify({ layouts: results, noJavaScript: 'native controls and single route pass', failureAndRetry: 'pass' }, null, 2));
    console.log(JSON.stringify(results, null, 2));
    console.log('PASS: JavaScript disabled, failure-only message and successful retry');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
