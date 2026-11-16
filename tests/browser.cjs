const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.SHORTS_BASE_URL || 'http://127.0.0.1:18080';
const artifacts = process.env.SHORTS_ARTIFACTS || '/tmp/shorts-browser';
const items = JSON.parse(fs.readFileSync(process.env.SHORTS_MANIFEST || path.join(__dirname, '../media.json')));
const published = items.filter(i => i.published);
fs.mkdirSync(artifacts, { recursive: true });

async function move(page, direction, touch) {
  const { width, height } = page.viewportSize();
  if (touch) {
    const session = await page.context().newCDPSession(page);
    const x = width * .5, start = height * (direction > 0 ? .8 : .2), end = height * (direction > 0 ? .2 : .8);
    await session.send('Input.dispatchTouchEvent', { type:'touchStart', touchPoints:[{x,y:start}] });
    for (let i = 1; i <= 10; i++) {
      await session.send('Input.dispatchTouchEvent', { type:'touchMove', touchPoints:[{x,y:start+(end-start)*i/10}] });
      await page.waitForTimeout(16);
    }
    await session.send('Input.dispatchTouchEvent', { type:'touchEnd', touchPoints:[] });
    await session.detach();
  } else {
    await page.mouse.move(width*.5,height*.45);
    await page.mouse.wheel(0,direction*height*.85);
  }
}
async function playback(page, clip) {
  const video = clip.locator('video');
  await clip.locator('.play').focus(); await page.keyboard.press('Enter');
  await video.evaluate(v => new Promise((resolve,reject) => {
    if (!v.paused && v.currentTime > .05) return resolve();
    const timer = setTimeout(() => reject(new Error('play timeout')), 12000);
    v.addEventListener('timeupdate', () => { if (!v.paused && v.currentTime>.05) {clearTimeout(timer);resolve();} });
  }));
  assert.equal(await video.evaluate(v => v.controls), true);
  await video.evaluate(v => v.pause());
  assert.equal(await video.evaluate(v => v.paused), true);
  await video.evaluate(v => {v.currentTime=10;});
  await page.waitForFunction(v => Math.abs(v.currentTime-10)<.5 && !v.seeking, await video.elementHandle());
  await video.evaluate(v => v.play());
  await video.evaluate(v => v.requestFullscreen());
  await page.waitForFunction(() => !!document.fullscreenElement);
  await page.evaluate(() => document.exitFullscreen());
  assert.equal(await video.evaluate(v => getComputedStyle(v).objectFit), 'contain');
}
(async () => {
  const browser = await chromium.launch({ executablePath:process.env.CHROMIUM_PATH || '/usr/bin/chromium', headless:true, args:['--no-sandbox'] });
  const results = [];
  try {
    for (const [width,height] of [[360,800],[390,844],[1440,1000],[844,390]]) {
      const touch = width < 500 || height < 500;
      const context = await browser.newContext({viewport:{width,height}, isMobile:touch, hasTouch:touch});
      for (const query of ['', '?reel=invalid', ...items.map(i => '?reel='+i.reel_id)]) {
        const page = await context.newPage();
        const errors=[], failures=[], requests=[];
        page.on('pageerror',e=>errors.push(e.message));
        page.on('console',m=>{if(m.type()==='error') errors.push(m.text());});
        page.on('response',r=>{if(r.status()>=400) failures.push([r.status(),r.url()]);});
        page.on('request',r=>{assert.equal(new URL(r.url()).origin,new URL(base).origin); if(r.url().includes('.mp4')) requests.push(r.url());});
        const selected=items.find(i=>query==='?reel='+i.reel_id);
        const expected=selected ? (selected.published ? [selected] : []) : published;
        await page.goto(base+'/'+query);
        await page.waitForFunction(()=>document.getElementById('feed').dataset.ready==='true');
        for (let reload=0; reload<2; reload++) {
          const ids=await page.locator('.clip').evaluateAll(nodes=>nodes.map(n=>n.dataset.reel));
          assert.deepEqual(ids,expected.map(i=>i.reel_id));
          assert.equal(await page.locator('video').count(),expected.length);
          const text=await page.content();
          for(const item of items) if(!expected.includes(item)) for(const field of ['label','video','poster']) assert.ok(!text.includes(item[field]));
          if(!expected.length) assert.ok(text.includes(selected ? '아직 공개되지 않은 영상입니다.' : '공개된 영상이 아직 없습니다.'));
          assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
          assert.equal(await page.locator('nav,header,footer,form,a').count(),0);
          if(selected) assert.equal(await page.locator('.reel-count,.swipe-hint').count(),0);
          if(reload===0) {await page.reload();await page.waitForFunction(()=>document.getElementById('feed').dataset.ready==='true');}
        }
        assert.deepEqual(requests,[], 'initial MP4 fetches');
        await page.screenshot({path:path.join(artifacts,width+'-'+height+'-'+(selected?selected.reel_id:query?'invalid':'base')+'.png')});
        if(selected && selected.published) {
          await playback(page,page.locator('.clip'));
          await move(page,1,touch);
          assert.equal(await page.locator('.clip').count(),1);
          assert.equal(new URL(page.url()).searchParams.get('reel'),selected.reel_id);
        }
        if(!query && published.length) {
          const historyLength=await page.evaluate(()=>history.length);
          for(let i=0;i<published.length;i++) {
            const clip=page.locator('.clip').nth(i);
            await page.waitForFunction(id=>Math.abs(document.querySelector('[data-reel="'+id+'"]').getBoundingClientRect().top)<2,published[i].reel_id);
            await playback(page,clip);
            if(i+1<published.length) {
              await move(page,1,touch);
              await page.waitForFunction(v=>v.paused,await clip.locator('video').elementHandle());
            }
          }
          if(published.length>1) {
            await move(page,-1,touch);
            await page.waitForFunction(id=>Math.abs(document.querySelector('[data-reel="'+id+'"]').getBoundingClientRect().top)<2,published[published.length-2].reel_id);
          }
          assert.equal(await page.evaluate(()=>history.length),historyLength);
          assert.equal(new URL(page.url()).search,'');
          assert.equal(await page.locator('video').evaluateAll(videos=>videos.filter(v=>!v.paused).length)<=1,true);
        }
        assert.deepEqual(errors,[]); assert.deepEqual(failures,[]);
        results.push({width,height,query,published:published.length,pass:true});
        await page.close();
      }
      await context.close();
    }
    // Native fallback and realistic failure/retry, using a genuinely published clip.
    if(published.length) {
      const single='/?reel='+published[0].reel_id;
      const nojs=await browser.newContext({javaScriptEnabled:false});const page=await nojs.newPage();
      await page.goto(base+single);assert.equal(await page.locator('video[controls]').count(),1);await nojs.close();
      const context=await browser.newContext();const broken=await context.newPage();let fail=true;
      await broken.route('**/*.mp4?*',route=>fail?route.fulfill({status:404,body:''}):route.continue());
      await broken.goto(base+single);await broken.locator('.play').click();await broken.locator('.failure').waitFor({state:'visible'});
      assert.equal(await broken.locator('.failure p').innerText(),'영상을 불러오지 못했습니다. 다시 시도해 주세요.');
      fail=false;await broken.locator('.retry').click();await broken.waitForFunction(()=>!document.querySelector('video').paused && document.querySelector('video').currentTime>0);await context.close();
    }
    fs.writeFileSync(path.join(artifacts,'browser-results.json'),JSON.stringify(results,null,2));
    console.log('PASS: '+results.length+' routes/viewports, playback, scroll isolation, no-JS, retry');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
