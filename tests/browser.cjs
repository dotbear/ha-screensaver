// Run against the local Flask server with Playwright installed. No HA calls:
// every browser context uses demo mode, with audio muted as an extra guard.
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_EXECUTABLE ? { executablePath: process.env.CHROMIUM_EXECUTABLE } : {}),
    args: ['--mute-audio'],
  });
  const base = process.env.SCREENSAVER_TEST_URL || 'http://127.0.0.1:18080/';
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  const realControls = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.method() === 'POST' && request.url().includes('/api/media/')) realControls.push(request.url());
  });
  await page.route('https://picsum.photos/**', route => route.fulfill({
    contentType: 'image/svg+xml',
    body: '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="800"><rect width="100%" height="100%" fill="#234038"/></svg>',
  }));

  try {
    await page.goto(`${base}?demo&night=1`);
    await page.waitForFunction(() => typeof app !== 'undefined' && app.isScreensaverActive && app.isNightActive);
    const ring = (id, seconds = 60) => page.evaluate(({ id, seconds }) => {
      app.handleDoorbell({ active: true, ring_id: id, expires_at: 1000 + seconds, server_time: 1000 });
    }, { id, seconds });

    await ring('night-ring');
    await page.waitForFunction(() => app.isDoorbellActive);
    await page.frameLocator('#doorbell-frame').getByText('Front door · demo camera').waitFor();
    assert.equal(await page.locator('#ha-iframe').getAttribute('src'), 'about:blank');
    assert.equal(await page.evaluate(() => document.getElementById('ha-iframe').inert), true);
    await page.screenshot({ path: '/tmp/screensaver-doorbell-tested.png' });
    const deadline = await page.evaluate(() => app.doorbellDeadline);
    await ring('night-ring');
    assert.equal(await page.evaluate(() => app.doorbellDeadline), deadline, 'unchanged polling must not extend a ring');
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    assert.equal(await page.evaluate(() => app.isNightActive && app.isScreensaverActive), true);
    assert.equal(await page.locator('#doorbell-frame').getAttribute('src'), 'about:blank');
    await ring('night-ring');
    assert.equal(await page.evaluate(() => app.isDoorbellActive), false, 'dismissed ring stays closed');

    await ring('second-ring', 5);
    const firstDeadline = await page.evaluate(() => app.doorbellDeadline);
    await ring('third-ring', 10);
    assert.ok(await page.evaluate(() => app.doorbellDeadline) > firstDeadline + 4000);
    await page.evaluate(() => { app.doorbellDeadline = performance.now() + 100; });
    await page.waitForFunction(() => !app.isDoorbellActive);
    assert.equal(await page.evaluate(() => app.isNightActive), true, 'expiry recomputes night mode');

    await page.evaluate(() => {
      app.stopScreensaver();
      app.config.idle_timeout_seconds = 30;
      app.setupIdleDetection();
    });
    await ring('dashboard-ring');
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    assert.equal(await page.evaluate(() => app.isScreensaverActive), false, 'interactive dashboard is preserved');

    await page.evaluate(() => {
      app.config.night_mode_enabled = false;
      app.startScreensaver();
    });
    await page.waitForFunction(() => app.isMediaMode);
    await page.evaluate(async () => {
      await app.controlMedia('volume', { volume_level: 1 });
      await app.controlMedia('play_pause');
    });
    assert.deepEqual(realControls, [], 'demo controls must never affect real HA');
    await ring('music-ring');
    await page.getByRole('button', { name: 'Close', exact: true }).click();
    await page.waitForFunction(() => app.isMediaMode);

    const race = await page.evaluate(async () => {
      const original = window.fetch;
      let release;
      window.fetch = url => url.includes('/media') ? new Promise(resolve => { release = resolve; }) : original(url);
      try {
        const loading = app.loadMedia();
        app.stopScreensaver();
        release(new Response(JSON.stringify({ state: 'playing', title: 'Late result' })));
        await loading;
        return app.isMediaMode;
      } finally { window.fetch = original; }
    });
    assert.equal(race, false, 'late media response cannot restart music mode after exit');

    const photoCount = await page.evaluate(async () => {
      app.config.media_player_entity = '';
      app.photos = Array.from({ length: 30 }, (_, i) => ({ url: `https://picsum.photos/seed/${i}/1280/800`, exif: {} }));
      app.startScreensaver();
      const initial = document.querySelectorAll('.slide img[src]').length;
      app.nextSlide();
      const during = document.querySelectorAll('.slide img[src]').length;
      await new Promise(resolve => setTimeout(resolve, 1200));
      const after = document.querySelectorAll('.slide img[src]').length;
      return { initial, during, after };
    });
    assert.deepEqual(photoCount, { initial: 1, during: 2, after: 1 }, 'photo decoding remains bounded');

    const ingressOrigin = await page.evaluate(() => {
      const url = window.location.href;
      app.demoMode = false;
      history.replaceState({}, '', '/api/hassio_ingress/test/');
      const resolved = app.homeAssistantUrl();
      history.replaceState({}, '', url);
      app.demoMode = true;
      return resolved;
    });
    assert.equal(ingressOrigin, new URL(base).origin, 'ingress uses the HA origin, including HTTPS');

    await page.reload();
    await page.waitForFunction(() => typeof app !== 'undefined' && app.config);
    await ring('music-ring');
    assert.equal(await page.evaluate(() => app.isDoorbellActive), false, 'dismissal survives reload');

    await page.setViewportSize({ width: 390, height: 844 });
    await ring('phone-width-ring');
    const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    assert.equal(horizontalOverflow, false);
    assert.deepEqual(errors, []);
    console.log('Browser checks passed: night/dashboard/music overrides, expiry, repeat/dismissal/reload, media race, demo isolation, bounded photos, ingress, narrow layout.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
