import * as esbuild from 'esbuild';
import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync, unlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const outdir = join(root, 'frontend', 'build');
const siteUrl = (process.env.SITE_URL || '').replace(/\/$/, '');
const ogImageUrl = siteUrl ? `${siteUrl}/frontend/assets/og-cover.jpg` : 'assets/og-cover.jpg';

const fontDir = join(root, 'frontend', 'fonts');
mkdirSync(fontDir, { recursive: true });
const fontSource = join(root, 'node_modules', '@fontsource', 'outfit', 'files');
for (const [from, to] of [
    ['outfit-latin-400-normal.woff2', 'outfit-latin-400.woff2'],
    ['outfit-latin-700-normal.woff2', 'outfit-latin-700.woff2'],
    ['outfit-latin-900-normal.woff2', 'outfit-latin-900.woff2']
]) {
    copyFileSync(join(fontSource, from), join(fontDir, to));
}
copyFileSync(join(root, 'node_modules', '@fontsource', 'outfit', 'LICENSE'), join(fontDir, 'LICENSE'));

const serifSource = join(root, 'node_modules', '@fontsource', 'noto-serif-sc', 'files');
copyFileSync(
    join(serifSource, 'noto-serif-sc-chinese-simplified-400-normal.woff2'),
    join(fontDir, 'noto-serif-sc-400.woff2')
);
copyFileSync(
    join(root, 'node_modules', '@fontsource', 'noto-serif-sc', 'LICENSE'),
    join(fontDir, 'LICENSE-noto-serif-sc')
);

mkdirSync(outdir, { recursive: true });
for (const file of readdirSync(outdir)) {
    if (/\.(js|css|json)$/.test(file)) unlinkSync(join(outdir, file));
}
const hashedFontDir = join(outdir, 'fonts');
if (existsSync(hashedFontDir)) {
    for (const file of readdirSync(hashedFontDir)) {
        unlinkSync(join(hashedFontDir, file));
    }
}

async function bundle(entry, outfile, format = 'iife') {
    await esbuild.build({
        entryPoints: [join(root, entry)],
        bundle: true,
        minify: true,
        format,
        platform: 'browser',
        target: ['es2019'],
        outfile,
        logLevel: 'info',
    });
    const source = readFileSync(outfile);
    const hash = createHash('sha256').update(source).digest('hex').slice(0, 10);
    const hashed = outfile.replace(/\.js$/, `.${hash}.js`);
    writeFileSync(hashed, source);
    unlinkSync(outfile);
    return hashed.replace(/\\/g, '/').split('/frontend/')[1];
}

async function bundleCss() {
    const outfile = join(outdir, 'style.css');
    await esbuild.build({
        entryPoints: [join(root, 'frontend', 'style.css')],
        bundle: true,
        minify: true,
        outfile,
        logLevel: 'info',
        loader: { '.woff2': 'file' },
        assetNames: 'fonts/[name]-[hash]',
    });
    const source = readFileSync(outfile);
    const hash = createHash('sha256').update(source).digest('hex').slice(0, 10);
    const hashed = join(outdir, `style.${hash}.css`);
    writeFileSync(hashed, source);
    unlinkSync(outfile);
    return `build/style.${hash}.css`;
}

const assets = {
    style: await bundleCss(),
    echartsMain: await bundle('frontend/src/echarts-main.js', join(outdir, 'echarts-main.js')),
    app: await bundle('frontend/src/index-main.js', join(outdir, 'app.js')),
    echoChunk: await bundle('frontend/src/echo-universe-chunk.js', join(outdir, 'echo-universe-chunk.js'), 'esm')
};

writeFileSync(join(outdir, 'manifest.json'), `${JSON.stringify(assets, null, 2)}\n`);

function replaceBlock(htmlPath, marker, content) {
    const full = join(root, htmlPath);
    let html = readFileSync(full, 'utf8');
    const pattern = new RegExp(`<!-- ${marker} -->[\\s\\S]*?<!-- endbuild -->`);
    if (!pattern.test(html)) {
        throw new Error(`${htmlPath} is missing <!-- ${marker} --> block`);
    }
    html = html.replace(pattern, `<!-- ${marker} -->\n    ${content}\n    <!-- endbuild -->`);
    writeFileSync(full, html);
}

function replaceScripts(htmlPath, tags) {
    replaceBlock(htmlPath, 'build:js', tags.join('\n    '));
}

replaceBlock('frontend/index.html', 'build:css', `<link rel="stylesheet" href="${assets.style}">`);
replaceBlock('frontend/index.html', 'build:og', [
    `<meta property="og:image" content="${ogImageUrl}">`,
    `<meta name="twitter:image" content="${ogImageUrl}">`
].join('\n    '));
replaceScripts('frontend/index.html', [
    `<script defer src="${assets.echartsMain}"></script>`,
    `<script defer src="${assets.app}"></script>`
]);

console.log({ siteUrl: siteUrl || '(relative og:image)', ...assets });
