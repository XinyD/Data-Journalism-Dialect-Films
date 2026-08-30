import { createGzip } from 'node:zlib';
import { createReadStream, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pipeline } from 'node:stream/promises';
import { Writable } from 'node:stream';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(root, 'frontend', 'build', 'manifest.json'), 'utf8'));

const budgets = {
    mainJsGzipBytes: 300 * 1024,
    lazyChunkGzipBytes: 200 * 1024
};

function gzipSize(relPath) {
    return new Promise((resolve, reject) => {
        let size = 0;
        const sink = new Writable({
            write(chunk, _enc, cb) {
                size += chunk.length;
                cb();
            }
        });
        pipeline(createReadStream(join(root, 'frontend', relPath)), createGzip({ level: 9 }), sink)
            .then(() => resolve(size))
            .catch(reject);
    });
}

const mainBytes = (await gzipSize(manifest.echartsMain)) + (await gzipSize(manifest.app));
const lazyChunkBytes = await gzipSize(manifest.echoChunk);

const report = {
    mainJsGzipKb: +(mainBytes / 1024).toFixed(1),
    lazyChunkGzipKb: +(lazyChunkBytes / 1024).toFixed(1),
    budgets: {
        mainJsGzipKb: budgets.mainJsGzipBytes / 1024,
        lazyChunkGzipKb: budgets.lazyChunkGzipBytes / 1024,
        lcpLocalSeconds: 2.5,
        clsCoverFontSwap: 'watch Outfit swap on #step-0'
    }
};

console.log(report);

if (mainBytes > budgets.mainJsGzipBytes) {
    throw new Error(`Main JS gzip ${report.mainJsGzipKb} KB exceeds ${report.budgets.mainJsGzipKb} KB`);
}
if (lazyChunkBytes > budgets.lazyChunkGzipBytes) {
    throw new Error(`Lazy chunk gzip ${report.lazyChunkGzipKb} KB exceeds ${report.budgets.lazyChunkGzipKb} KB`);
}
