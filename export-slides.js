const puppeteer = require('puppeteer');
const path = require('path');

async function exportSlides(file, prefix) {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const filePath = 'file://' + path.resolve(file);
  await page.goto(filePath, { waitUntil: 'networkidle2', timeout: 30000 });

  await page.addStyleTag({ content: '.slide { transform: none !important; margin: 0 !important; margin-bottom: 0 !important; margin-right: 0 !important; }' });
  await new Promise(r => setTimeout(r, 2000));

  const count = await page.evaluate(() => document.querySelectorAll('.slide').length);
  console.log(prefix + ': ' + count + ' slides');

  for (let i = 0; i < count; i++) {
    await page.setViewport({ width: 1080, height: 1350, deviceScaleFactor: 1 });
    
    await page.evaluate((idx) => {
      const slides = document.querySelectorAll('.slide');
      // Hide all slides
      slides.forEach(s => s.style.display = 'none');
      // Show only the target slide
      const el = slides[idx];
      el.style.display = 'flex';
      el.style.position = 'fixed';
      el.style.top = '0';
      el.style.left = '0';
      el.style.width = '1080px';
      el.style.height = '1350px';
      el.style.zIndex = '99999';
    }, i);

    await new Promise(r => setTimeout(r, 500));

    const filename = '/Users/ed/Desktop/' + prefix + '-' + (i + 1) + '.png';
    await page.screenshot({ path: filename, type: 'png', clip: { x: 0, y: 0, width: 1080, height: 1350 } });
    console.log('  ' + filename);
  }

  await browser.close();
}

(async () => {
  try {
    await exportSlides('instagram-geo.html', 'geo');
    await exportSlides('instagram-uk.html', 'uk');
    await exportSlides('instagram-weekly.html', 'weekly');
    console.log('Done — all PNGs on Desktop');
  } catch(e) {
    console.error(e);
    process.exit(1);
  }
})();
