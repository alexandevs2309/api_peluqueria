/**
 * prepare-marketing.mjs
 * Post-build script para el deploy del sitio de marketing.
 * Modifica el dist DESPUÉS del build para habilitar SEO sin afectar el app principal.
 *
 * Uso: node scripts/prepare-marketing.mjs
 * (ejecutado automáticamente por npm run deploy:marketing)
 */

import { readFileSync, writeFileSync, copyFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const distDir = resolve(__dirname, '../dist/auron-suite/browser');

console.log('🚀 Preparando sitio de marketing para deploy SEO...\n');

// ── 1. robots.txt — permitir indexación completa ──────────────────────────────
const marketingRobots = `User-agent: *
Allow: /

# Bloquear rutas internas del app
Disallow: /dashboard
Disallow: /dashboard/
Disallow: /auth/
Disallow: /pos/
Disallow: /admin/

Sitemap: https://auronsuite.com/sitemap.xml
`;

const robotsPath = resolve(distDir, 'robots.txt');
writeFileSync(robotsPath, marketingRobots, 'utf-8');
console.log('✅ robots.txt actualizado (SEO habilitado)');

// ── 2. index.html — remover noindex y agregar meta SEO completo ───────────────
const indexPath = resolve(distDir, 'index.html');
let html = readFileSync(indexPath, 'utf-8');

// Remover meta noindex
html = html.replace(
  /\s*<!-- Prevent Search Engine Indexing \(noindex\) -->\s*\n\s*<meta name="robots"[^>]*noindex[^>]*\/>\s*\n/,
  '\n'
);

// Agregar meta SEO completo después del <title>
const seoMeta = `
    <!-- SEO -->
    <meta name="robots" content="index, follow" />
    <meta name="description" content="Auron Suite — La plataforma de gestión todo-en-uno para barberías y salones de belleza en LatAm. Agenda online, POS, nómina, inventario y más. Empieza gratis 14 días." />
    <meta name="keywords" content="software barbería, gestión salón, agenda online, POS barbería, software peluquería, administración salón belleza" />
    <meta name="author" content="Auron Suite" />

    <!-- Open Graph (redes sociales) -->
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://auronsuite.com/" />
    <meta property="og:title" content="Auron Suite — Gestión inteligente para barberías y salones" />
    <meta property="og:description" content="Todo lo que tu barbería necesita en un solo lugar. Agenda, POS, nómina, inventario y reportes. Prueba gratis 14 días, sin tarjeta." />
    <meta property="og:image" content="https://auronsuite.com/assets/logos/logo-final.png" />
    <meta property="og:locale" content="es_DO" />
    <meta property="og:site_name" content="Auron Suite" />

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Auron Suite — Gestión para barberías y salones" />
    <meta name="twitter:description" content="Agenda online, POS, nómina e inventario. Todo en uno. Prueba gratis 14 días." />
    <meta name="twitter:image" content="https://auronsuite.com/assets/logos/logo-final.png" />

    <!-- Canonical -->
    <link rel="canonical" href="https://auronsuite.com/" />
`;

html = html.replace('<title>Auron Suite</title>', `<title>Auron Suite — Gestión para barberías y salones de belleza</title>${seoMeta}`);

writeFileSync(indexPath, html, 'utf-8');
console.log('✅ index.html actualizado (noindex removido, meta SEO agregado)');

// ── 3. sitemap.xml — generarlo en el dist ────────────────────────────────────
const today = new Date().toISOString().split('T')[0];
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://auronsuite.com/</loc>
    <lastmod>${today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://auronsuite.com/landing</loc>
    <lastmod>${today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://auronsuite.com/terms</loc>
    <lastmod>${today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>
  <url>
    <loc>https://auronsuite.com/privacy</loc>
    <lastmod>${today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>
</urlset>
`;

const sitemapPath = resolve(distDir, 'sitemap.xml');
writeFileSync(sitemapPath, sitemap, 'utf-8');
console.log('✅ sitemap.xml generado');

console.log('\n🎉 Sitio de marketing listo para deploy SEO-optimizado.');
console.log('   Ejecuta: npx wrangler deploy --config wrangler.marketing.jsonc\n');
