#!/usr/bin/env node
/**
 * export-walkthrough.js — smooth 9:16 mobile walkthrough video of the live site.
 *
 * Drives thedailybrief.co.uk in an emulated phone viewport (360x640 @3x = 1080x1920),
 * captures deterministic frame-by-frame PNGs (scripted eased scrolling + scrubbed CSS
 * transitions), then encodes with the bundled ffmpeg-static.
 *
 * Usage:
 *   node export-walkthrough.js [--url URL] [--output PATH] [--frames-dir DIR]
 */

const puppeteer = require('puppeteer');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const FPS = 30;

function argVal(flag, fallback) {
  const i = process.argv.indexOf(flag);
  return i !== -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const URL = argVal('--url', 'https://thedailybrief.co.uk');
const OUTPUT = argVal('--output', path.join(os.homedir(), 'Desktop', 'daily-brief-walkthrough.mp4'));
const FRAMES_DIR = argVal('--frames-dir', path.join(os.tmpdir(), 'daily-brief-walkthrough-frames'));

const CAPTION_ID = 'wt-caption';
const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

let frameIdx = 0;
let lastFramePath = null;
let page = null;

const framePath = (i) => path.join(FRAMES_DIR, `frame-${String(i).padStart(5, '0')}.png`);

async function capture() {
  const p = framePath(frameIdx);
  await page.screenshot({ path: p, type: 'png' });
  lastFramePath = p;
  frameIdx++;
}

// Duplicate the last captured frame — cheap static hold.
function hold(seconds) {
  const n = Math.round(seconds * FPS);
  for (let i = 0; i < n; i++) {
    fs.copyFileSync(lastFramePath, framePath(frameIdx));
    frameIdx++;
  }
}

async function scrollY() {
  return page.evaluate(() => window.scrollY);
}

async function animateScroll(targetY, seconds) {
  const startY = await scrollY();
  const n = Math.max(1, Math.round(seconds * FPS));
  for (let i = 1; i <= n; i++) {
    const y = startY + (targetY - startY) * easeInOut(i / n);
    await page.evaluate((v) => window.scrollTo(0, v), y);
    await capture();
  }
}

// Y position of a selector, offset so it sits below the sticky masthead.
async function yOf(selector, offset = -76) {
  return page.evaluate(
    (sel, off) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      return Math.max(0, el.getBoundingClientRect().top + window.scrollY + off);
    },
    selector,
    offset
  );
}

// Scrub any in-flight CSS transitions/animations frame by frame (deterministic).
async function scrub(seconds) {
  const n = Math.max(1, Math.round(seconds * FPS));
  await page.evaluate(() =>
    document.getAnimations().forEach((a) => {
      try { a.pause(); } catch (e) {}
    })
  );
  for (let i = 1; i <= n; i++) {
    const t = (i / n) * seconds * 1000;
    await page.evaluate((ms) =>
      document.getAnimations().forEach((a) => {
        try { a.currentTime = ms; } catch (e) {}
      }), t);
    await capture();
  }
  await page.evaluate(() =>
    document.getAnimations().forEach((a) => {
      try { a.finish(); } catch (e) { try { a.play(); } catch (e2) {} }
    })
  );
}

// Manual ticker motion — the JS scroll loop is paused, we translate the track ourselves.
async function tickerFrames(seconds, pxPerFrame = 1.4) {
  const n = Math.round(seconds * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate((px) => {
      const track = document.getElementById('marketsTrack');
      if (!track) return;
      const cs = getComputedStyle(track).transform;
      const tx = cs && cs !== 'none' ? new DOMMatrixReadOnly(cs).e : 0;
      track.style.transform = `translateX(${tx - px}px)`;
    }, pxPerFrame);
    await capture();
  }
}

// Crossfade the caption strip (manual per-frame opacity — deterministic).
async function setCaption(text) {
  const setOpacity = (o) =>
    page.evaluate((v) => {
      const c = document.getElementById('wt-caption-el');
      if (c) c.style.opacity = String(v);
    }, o);
  const current = await page.evaluate(() => {
    const c = document.getElementById('wt-caption-el');
    return c && c.textContent && parseFloat(c.style.opacity || '0') > 0 ? c.textContent : null;
  });
  const fadeN = 8;
  if (current) {
    for (let i = fadeN - 1; i >= 0; i--) {
      await setOpacity(i / fadeN);
      await capture();
    }
  }
  await page.evaluate((t) => {
    const c = document.getElementById('wt-caption-el');
    if (c) c.textContent = t;
  }, text);
  for (let i = 1; i <= fadeN; i++) {
    await setOpacity(i / fadeN);
    await capture();
  }
}

async function segment(name, fn) {
  const start = frameIdx;
  try {
    await fn();
    console.log(`  ✓ ${name} (${frameIdx - start} frames, ends at ${(frameIdx / FPS).toFixed(1)}s)`);
  } catch (err) {
    console.warn(`  ⚠ ${name} failed, skipping: ${err.message}`);
  }
}

async function main() {
  fs.rmSync(FRAMES_DIR, { recursive: true, force: true });
  fs.mkdirSync(FRAMES_DIR, { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--force-device-scale-factor=3'],
  });
  page = await browser.newPage();
  await page.setViewport({ width: 360, height: 640, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  await page.setUserAgent(
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
  );

  console.log(`Loading ${URL} ...`);
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#day-editions .curated-edition', { timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, 2500)); // ticker + RSS settle

  // --- page prep (browser session only, nothing touches the repo) ---
  await page.evaluate(() => {
    // deterministic scrolling
    const style = document.createElement('style');
    style.textContent = 'html { scroll-behavior: auto !important; }';
    document.head.appendChild(style);

    // dismiss cookie banner
    const reject = document.getElementById('cookieReject');
    if (reject) reject.click();
    const banner = document.getElementById('cookieBanner');
    if (banner) banner.style.display = 'none';

    // freeze the JS ticker loop — we drive it manually per frame
    if (window._tickerPause) window._tickerPause();

    // neutralise the freshness self-reload poll for the capture session
    const origFetch = window.fetch.bind(window);
    window.fetch = (u, ...rest) =>
      typeof u === 'string' && u.includes('_nocache') ? new Promise(() => {}) : origFetch(u, ...rest);

    // caption strip (site typography, sharp corners per house style)
    const cap = document.createElement('div');
    cap.id = 'wt-caption-el';
    cap.style.cssText = [
      'position:fixed', 'left:50%', 'transform:translateX(-50%)', 'bottom:84px',
      'z-index:2147483647', 'background:rgba(12,18,32,0.9)', 'color:#fff',
      "font-family:'Inter',-apple-system,sans-serif", 'font-size:14px', 'font-weight:600',
      'letter-spacing:0.01em', 'padding:9px 16px', 'border-left:3px solid #8b1e2d',
      'opacity:0', 'pointer-events:none', 'white-space:nowrap',
      'box-shadow:0 4px 18px rgba(0,0,0,0.35)',
    ].join(';');
    document.body.appendChild(cap);
  });
  await new Promise((r) => setTimeout(r, 400));
  await page.evaluate(() => window.scrollTo(0, 0));
  await capture();

  console.log('Capturing segments:');

  // 1 — masthead hold with live ticker motion (~4s)
  await segment('1 masthead', async () => {
    await setCaption('Your daily news, curated');
    await tickerFrames(3.4);
  });

  // 2 — markets ticker + driver modal (~4s)
  await segment('2 markets ticker', async () => {
    await setCaption('Live markets — tap for the why');
    await tickerFrames(0.8);
    await page.evaluate(() => window.openMarketModal && window.openMarketModal('FTSE'));
    await scrub(0.4);
    hold(1.6);
    await page.evaluate(() => {
      const close = document.getElementById('marketModalClose');
      if (close) close.click();
      else document.getElementById('marketModal')?.classList.remove('open');
    });
    await scrub(0.35);
  });

  // 3 — edition header + impact box (~4s)
  await segment('3 impact box', async () => {
    await setCaption('What it means for you');
    const headerY = await yOf('#day-editions .edition-header');
    if (headerY !== null) await animateScroll(headerY, 1.1);
    await page.evaluate(() => {
      const d = document.querySelector('#day-editions details.impact-details');
      if (d) d.open = true;
    });
    const impactY = await yOf('#day-editions .impact-box, #day-editions details.impact-details');
    if (impactY !== null) await animateScroll(impactY, 0.9);
    hold(1.5);
  });

  // 4 — curated stories, accordion expand (~6s)
  await segment('4 top stories', async () => {
    await setCaption('Top 5 stories, morning & evening');
    const itemY = await yOf('#day-editions .curated-item');
    if (itemY !== null) await animateScroll(itemY, 1.0);
    const clicked = await page.evaluate(() => {
      const h4 = document.querySelector('#day-editions .curated-item.curated-item-collapsed h4');
      if (h4) { h4.click(); return true; }
      return false;
    });
    if (clicked) await scrub(0.7);
    hold(1.6);
    // read down through the expanded body
    const cur = await scrollY();
    await animateScroll(cur + 330, 1.6);
    hold(0.8);
  });

  // 5 — reveal the full column (~4s)
  await segment('5 full briefing', async () => {
    await setCaption('The full briefing, one tap away');
    await page.evaluate(() => {
      const btn = [...document.querySelectorAll('#day-editions button')].find((b) =>
        /read full briefing/i.test(b.textContent)
      );
      if (btn) btn.click();
    });
    await capture();
    const cur = await scrollY();
    await animateScroll(cur + 900, 2.6);
    hold(0.6);
  });

  // 6 — dive deeper + One To Read (~5s)
  await segment('6 dive deeper', async () => {
    await setCaption('Dive deeper on the big stories');
    const opened = await page.evaluate(() => {
      const d = [...document.querySelectorAll('#day-editions details.dive-deeper')].find(
        (el) => el.getBoundingClientRect().height > 0
      ) || document.querySelector('#day-editions details.dive-deeper');
      if (!d) return false;
      d.open = true;
      return true;
    });
    if (opened) {
      const dy = await yOf('#day-editions details.dive-deeper[open]');
      if (dy !== null) await animateScroll(dy, 0.9);
      await capture();
      hold(1.2);
      const cur = await scrollY();
      await animateScroll(cur + 260, 1.1);
    }
    const otrY = await yOf('#day-editions .one-to-read');
    if (otrY !== null) {
      await animateScroll(otrY, 0.9);
      hold(0.9);
    }
  });

  // 7 — day tabs / rolling week (~4s)
  await segment('7 rolling week', async () => {
    await setCaption('A full week of editions');
    const navY = await yOf('#dayNav', -60);
    if (navY !== null) await animateScroll(navY, 0.9);
    const yesterdayShort = new Date(Date.now() - 86400000).toLocaleDateString('en-GB', { weekday: 'short' });
    await switchDay(yesterdayShort);
    // past editions are shorter when collapsed — re-anchor on the edition header
    const hy = await yOf('#dayNav', -60);
    if (hy !== null) await animateScroll(hy, 0.5);
    hold(1.4);
  });

  // 8 — dark mode (~4s)
  await segment('8 dark mode', async () => {
    await setCaption('Easy on the eyes, day or night');
    const topY = await yOf('header.masthead', 0);
    if (topY !== null) await animateScroll(Math.max(0, topY), 0.7);
    await page.evaluate(() => document.getElementById('darkToggle')?.click());
    await scrub(0.4);
    await tickerFrames(1.4);
    await page.evaluate(() => document.getElementById('darkToggle')?.click());
    await scrub(0.4);
    await tickerFrames(0.9);
  });

  // 9 — live feeds (~4s)
  await segment('9 live feeds', async () => {
    await setCaption('Rolling headlines, all day');
    const feedY = await yOf('#live-feeds', -56);
    if (feedY !== null) await animateScroll(feedY, 1.1);
    hold(0.7);
    await page.evaluate(() => {
      const dom = document.getElementById('domTab');
      if (dom && !dom.classList.contains('active')) dom.click();
      else document.getElementById('geoTab')?.click();
    });
    await scrub(0.3);
    hold(0.6);
    const cur = await scrollY();
    await animateScroll(cur + 420, 1.2);
  });

  // 10 — finale back at the masthead (~2.5s)
  await segment('10 finale', async () => {
    await page.evaluate(() => {
      // restore today's tab while the day nav is offscreen
      const tabs = [...document.querySelectorAll('.day-tab')];
      const todayShort = new Date().toLocaleDateString('en-GB', { weekday: 'short' });
      let idx = tabs.findIndex((t) => /today/i.test(t.textContent));
      if (idx === -1) idx = tabs.findIndex((t) => t.textContent.includes(todayShort));
      // click the tab itself — the site's internal day index is ordered
      // newest-first (reverse of DOM order), so never call _showDay with a DOM index
      if (idx !== -1) tabs[idx].click();
    });
    await new Promise((r) => setTimeout(r, 500));
    const cur = await scrollY();
    if (cur > 900) await page.evaluate(() => window.scrollTo(0, 900));
    await animateScroll(0, 1.0);
    await setCaption('thedailybrief.co.uk');
    await tickerFrames(1.0);
  });

  await browser.close();

  const seconds = (frameIdx / FPS).toFixed(1);
  console.log(`\nCaptured ${frameIdx} frames (~${seconds}s). Encoding ...`);

  const ffmpegPath = require('ffmpeg-static');
  execSync(
    `"${ffmpegPath}" -y -framerate ${FPS} -i "${FRAMES_DIR}/frame-%05d.png" ` +
      `-c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -movflags +faststart "${OUTPUT}"`,
    { stdio: 'inherit' }
  );

  fs.rmSync(FRAMES_DIR, { recursive: true, force: true });
  console.log(`\nDone: ${OUTPUT} (${seconds}s, 1080x1920 @ ${FPS}fps)`);
}

// Switch the visible day by weekday label (e.g. 'Wed', 'Sun') and scrub the slide.
async function switchDay(weekdayShort) {
  const idx = await page.evaluate((wd) => {
    const tabs = [...document.querySelectorAll('.day-tab')];
    return tabs.findIndex((t) => t.textContent.includes(wd));
  }, weekdayShort);
  if (idx === -1) throw new Error(`no day tab matching "${weekdayShort}"`);
  // click the tab element — the site's internal day array is newest-first,
  // the reverse of DOM tab order, so _showDay(domIndex) selects the wrong day
  await page.evaluate((i) => document.querySelectorAll('.day-tab')[i].click(), idx);
  await scrub(0.3);
  await new Promise((r) => setTimeout(r, 350));
  await capture();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
