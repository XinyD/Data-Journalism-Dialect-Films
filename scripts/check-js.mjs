import { execFileSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const files = [];

function walk(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const full = join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.name.endsWith('.js')) files.push(full);
    }
}

walk(join(root, 'frontend', 'js'));
walk(join(root, 'frontend', 'src'));

for (const file of files.sort()) {
    execFileSync(process.execPath, ['--check', file], { stdio: 'inherit' });
}
