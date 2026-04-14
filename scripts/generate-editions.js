#!/usr/bin/env node
/**
 * generate-editions.js
 * Extracts individual edition pages from index.html into /editions/
 * Also updates sitemap.xml with edition URLs.
 *
 * Usage: node scripts/generate-editions.js
 */

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const ROOT = path.resolve(__dirname, '..');
const INDEX = path.join(ROOT, 'index.html');
const EDITIONS_DIR = path.join(ROOT, 'editions');
const SITEMAP = path.join(ROOT, 'sitemap.xml');
const SITE_URL = 'https://thedailybrief.co.uk';

async function main() {
  // Ensure editions directory exists
  if (!fs.existsSync(EDITIONS_DIR)) fs.mkdirSync(EDITIONS_DIR);

  // Extract CSS from index.html (between <style> and </style>)
  const indexHtml = fs.readFileSync(INDEX, 'utf-8');
  const styleMatch = indexHtml.match(/<style>([\s\S]*?)<\/style>/);
  if (!styleMatch) { console.error('Could not extract <style> block'); process.exit(1); }
  const css = styleMatch[1];

  // Extract dark-mode init script
  const darkScript = `var s = localStorage.getItem('theme');
    if (s === 'dark' || (!s && !window.matchMedia('(prefers-color-scheme: light)').matches)) {
      document.documentElement.setAttribute('data-theme', 'dark');
      document.querySelector('meta[name="theme-color"]').content = '#141414';
    }`;

  // Use Puppeteer to parse editions from the DOM
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('file://' + INDEX);

  const editions = await page.evaluate(() => {
    const container = document.getElementById('all-editions');
    if (!container) return [];
    const results = [];
    const eds = container.querySelectorAll('.curated-edition[data-date][data-time]');
    const seen = {};

    eds.forEach(ed => {
      const date = ed.getAttribute('data-date');
      const time = ed.getAttribute('data-time');
      const key = date + 'T' + time;
      if (seen[key]) return;
      seen[key] = true;

      const isMorning = ed.classList.contains('morning');
      const isEvening = ed.classList.contains('evening');
      const isWeekly = ed.classList.contains('weekly');
      const type = isMorning ? 'morning' : isEvening ? 'evening' : isWeekly ? 'weekly' : null;
      if (!type) return;

      const meta = ed.querySelector('.curated-meta');
      const metaText = meta ? meta.textContent.trim() : '';
      const dateLabel = metaText.split('\u2014')[0].trim();

      // Get first 3 headlines for description
      const headlines = [];
      ed.querySelectorAll('.curated-item h4').forEach(h => headlines.push(h.textContent.trim()));
      const desc = headlines.slice(0, 3).join('. ') + (headlines.length > 0 ? '.' : '');

      // Type label for title
      const typeLabel = type === 'morning' ? 'Morning Briefing'
        : type === 'evening' ? 'Evening Briefing'
        : 'Weekly Roundup';

      results.push({
        date,
        time,
        type,
        typeLabel,
        dateLabel: dateLabel || date,
        description: desc || 'Curated geopolitical and UK domestic news briefing.',
        outerHTML: ed.outerHTML,
        markets: ed.getAttribute('data-markets') || ''
      });
    });

    return results;
  });

  await browser.close();

  if (editions.length === 0) {
    console.log('No editions found in index.html');
    process.exit(0);
  }

  // Sort chronologically (newest first)
  editions.sort((a, b) => {
    const da = a.date + 'T' + a.time;
    const db = b.date + 'T' + b.time;
    return db.localeCompare(da);
  });

  // Generate each edition page
  let generated = 0;
  const editionUrls = [];

  for (let i = 0; i < editions.length; i++) {
    const ed = editions[i];
    const slug = `${ed.date}-${ed.type}`;
    const filename = `${slug}.html`;
    const filepath = path.join(EDITIONS_DIR, filename);
    const url = `${SITE_URL}/editions/${filename}`;
    const canonical = url;
    const title = `${ed.typeLabel} — ${ed.dateLabel} — The Daily Brief`;
    const iso = `${ed.date}T${ed.time}:00+01:00`;

    // Prev/next links
    const prev = i < editions.length - 1 ? editions[i + 1] : null;
    const next = i > 0 ? editions[i - 1] : null;
    const prevHref = prev ? `/editions/${prev.date}-${prev.type}.html` : null;
    const nextHref = next ? `/editions/${next.date}-${next.type}.html` : null;
    const prevLabel = prev ? prev.typeLabel : '';
    const nextLabel = next ? next.typeLabel : '';

    const html = `<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escHtml(title)}</title>
  <meta name="theme-color" content="#f5f2eb" id="themeColor" />
  <link rel="canonical" href="${canonical}" />
  <meta name="description" content="${escHtml(ed.description)}" />
  <meta property="og:title" content="${escHtml(ed.typeLabel + ' — ' + ed.dateLabel)}" />
  <meta property="og:description" content="${escHtml(ed.description)}" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="${canonical}" />
  <meta property="og:image" content="${SITE_URL}/og-image.png" />
  <meta property="og:locale" content="en_GB" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="${escHtml(ed.typeLabel + ' — ' + ed.dateLabel)}" />
  <meta name="twitter:description" content="${escHtml(ed.description)}" />
  <meta name="twitter:image" content="${SITE_URL}/og-image.png" />
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='4' fill='%231a1a2e'/><text x='16.8' y='21.5' text-anchor='middle' font-family='Georgia,Times,serif' font-weight='700' font-size='13' fill='%23f0ece4' letter-spacing='-0.5'>TDB</text></svg>" />
  <link rel="apple-touch-icon" href="/icon-192.png" />
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    "headline": "${escJson(ed.typeLabel + ' \u2014 ' + ed.dateLabel)}",
    "datePublished": "${iso}",
    "dateModified": "${iso}",
    "description": "${escJson(ed.description)}",
    "image": "${SITE_URL}/og-image.png",
    "author": { "@type": "Organization", "name": "The Daily Brief" },
    "publisher": {
      "@type": "Organization",
      "name": "The Daily Brief",
      "@id": "${SITE_URL}/#organization",
      "logo": { "@type": "ImageObject", "url": "${SITE_URL}/icon-512.png" }
    },
    "mainEntityOfPage": { "@type": "WebPage", "@id": "${canonical}" },
    "inLanguage": "en-GB",
    "isAccessibleForFree": true
  }
  </script>
  <script>${darkScript}</script>
  <style>
${css}

    /* ── Edition page overrides ── */
    body { padding: 0; }
    .edition-masthead {
      position: sticky; top: 0; z-index: 100;
      background: var(--bg); border-bottom: 1px solid var(--border-light);
      padding: 14px 24px; display: flex; align-items: center; justify-content: space-between;
    }
    .edition-back {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 20px; font-weight: 700; color: var(--text-primary);
      text-decoration: none; display: flex; align-items: center; gap: 8px;
    }
    .edition-back:hover { opacity: 0.7; }
    .edition-back svg { width: 18px; height: 18px; fill: var(--text-secondary); }
    .edition-nav {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 24px; border-bottom: 1px solid var(--border-light);
      font-family: 'Inter', sans-serif; font-size: 13px;
    }
    .edition-nav a {
      color: var(--text-secondary); text-decoration: none;
      transition: color 0.15s;
    }
    .edition-nav a:hover { color: var(--text-primary); }
    .edition-nav .home { font-weight: 500; }
    .edition-main {
      max-width: 900px; margin: 0 auto; padding: 0 24px 60px;
    }
    .edition-main .curated-edition {
      border-left: none; padding-left: 0; margin-top: 0; opacity: 1;
    }
    .edition-main .curated-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 40px; }
    .edition-footer {
      border-top: 1px solid var(--border-light); padding: 30px 24px;
      text-align: center; font-family: 'Inter', sans-serif;
      font-size: 13px; color: var(--text-muted);
    }
    .edition-footer a { color: var(--text-secondary); text-decoration: none; }
    @media (max-width: 700px) {
      .edition-main .curated-grid { grid-template-columns: 1fr; }
      .edition-nav { font-size: 12px; }
    }
  </style>
</head>
<body>

  <div class="edition-masthead">
    <a href="/" class="edition-back">
      <svg viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>
      The Daily Brief
    </a>
    <button class="legal-dark-toggle" id="darkToggle" aria-label="Toggle dark mode" style="background:none;border:1px solid var(--border);border-radius:4px;padding:6px 10px;cursor:pointer;font-size:14px;">
      <span class="toggle-icon">&#9789;</span>
    </button>
  </div>

  <nav class="edition-nav">
    ${prevHref ? `<a href="${prevHref}">&larr; ${escHtml(prevLabel)}</a>` : '<span></span>'}
    <a href="/" class="home">All Editions</a>
    ${nextHref ? `<a href="${nextHref}">${escHtml(nextLabel)} &rarr;</a>` : '<span></span>'}
  </nav>

  <main class="edition-main">
    ${ed.outerHTML}
  </main>

  <footer class="edition-footer">
    <a href="/">&copy; 2026 The Daily Brief</a> &nbsp;&middot;&nbsp;
    <a href="/privacy.html">Privacy</a> &nbsp;&middot;&nbsp;
    <a href="/terms.html">Terms</a>
  </footer>

  <script>
  // Dark mode toggle
  (function() {
    var btn = document.getElementById('darkToggle');
    if (!btn) return;
    btn.addEventListener('click', function() {
      var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        document.querySelector('meta[name="theme-color"]').content = '#f5f2eb';
      } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        document.querySelector('meta[name="theme-color"]').content = '#141414';
      }
    });
  })();

  // Expand all dive-deeper sections (no collapse on edition pages)
  document.querySelectorAll('.curated-edition').forEach(function(ed) {
    // Ensure edition is fully visible
    ed.style.opacity = '1';
    ed.style.display = 'block';
  });
  </script>

</body>
</html>`;

    fs.writeFileSync(filepath, html, 'utf-8');
    editionUrls.push({ url, date: ed.date });
    generated++;
  }

  // Update sitemap.xml
  updateSitemap(editionUrls);

  console.log(`Generated ${generated} edition pages in /editions/`);
  editions.forEach(ed => {
    console.log(`  /editions/${ed.date}-${ed.type}.html — ${ed.typeLabel}, ${ed.dateLabel}`);
  });
}

function updateSitemap(editionUrls) {
  // Read existing sitemap and keep non-edition entries
  let xml = fs.readFileSync(SITEMAP, 'utf-8');

  // Remove existing edition entries
  xml = xml.replace(/\s*<url>\s*<loc>https:\/\/thedailybrief\.co\.uk\/editions\/[^<]*<\/loc>[\s\S]*?<\/url>/g, '');

  // Remove closing tag
  xml = xml.replace('</urlset>', '').trimEnd();

  // Update homepage lastmod to today
  const today = new Date().toISOString().split('T')[0];
  xml = xml.replace(
    /(<loc>https:\/\/thedailybrief\.co\.uk\/<\/loc>\s*<lastmod>)[^<]*/,
    `$1${today}`
  );

  // Add edition entries
  for (const { url, date } of editionUrls) {
    xml += `
  <url>
    <loc>${url}</loc>
    <lastmod>${date}</lastmod>
    <changefreq>never</changefreq>
    <priority>0.7</priority>
  </url>`;
  }

  xml += '\n</urlset>\n';
  fs.writeFileSync(SITEMAP, xml, 'utf-8');
  console.log(`Updated sitemap.xml with ${editionUrls.length} edition URLs`);
}

function escHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escJson(s) {
  return s.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, '\\n');
}

main().catch(err => { console.error(err); process.exit(1); });
