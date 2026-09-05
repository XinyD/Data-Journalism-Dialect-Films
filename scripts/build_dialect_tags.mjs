// 从方言片明细报告生成「家乡话」筛选所需的 movieId -> 方言族映射。
// 术语归一遵循主站口径：混合语种按片名列首位归组（index.html 方法论一节）。
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const SOURCE = join(root, 'data', 'dialect_films', '方言片明细报告.csv');
const TARGET = join(root, 'data', 'frontend', 'dialect_tags.json');

// 变体合并只做无争议的同名归并；未列出的写法保持原样。
const TAG_ALIASES = {
    '粵語': '粤语',
    '閩南語': '闽南语',
    '闽南话': '闽南语',
    '台语': '闽南语',
    '潮州话': '潮汕话',
    '潮语': '潮汕话',
    '蒙语': '蒙古语',
    '维语': '维吾尔语',
    '沪语': '上海话'
};

// 归一后无辨别力的统称，直接丢弃（影片仍可经「方言」语言组筛到）。
const GENERIC_TAGS = new Set(['话', '汉语', '中文话', '中文', '方言', '当地话', '少数民族语言']);

function applyLatinAliases(tag) {
    const lower = tag.toLowerCase();
    if (/(hokkien|min\s*nan|taiwanese)/.test(lower)) return '闽南语';
    if (lower.includes('shanghainese')) return '上海话';
    if (lower.includes('cantonese')) return '粤语';
    if (lower.includes('mongolian')) return '蒙古语';
    return tag;
}

export function parseCsvLine(line) {
    const cells = [];
    let current = '';
    let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
        const ch = line[i];
        if (quoted) {
            if (ch === '"') {
                if (line[i + 1] === '"') {
                    current += '"';
                    i += 1;
                } else {
                    quoted = false;
                }
            } else {
                current += ch;
            }
        } else if (ch === '"') {
            quoted = true;
        } else if (ch === ',') {
            cells.push(current);
            current = '';
        } else {
            current += ch;
        }
    }
    cells.push(current);
    return cells;
}

export function normalizeDialectTag(rawTag) {
    const tag = String(rawTag || '').trim();
    if (!tag) return '';
    // 混合语种（如「粤语 / 上海话」「粤语，台语」）取首位，与主站语言分组规则一致。
    const primary = tag.split(/[/、，,–—]/)[0].trim().replace(/^中国/, '');
    let devariant = TAG_ALIASES[primary] || applyLatinAliases(primary);
    // 「四川方言」「湖南当地方言」->「四川话」「湖南话」；已是「话/语」结尾的保持不变。
    devariant = devariant.replace(/(当地)?方言$/, '');
    if (!devariant) return '';
    devariant = devariant.replace(/当地话$/, '话');
    if (!/[话语]$/.test(devariant)) devariant += '话';
    if (GENERIC_TAGS.has(devariant)) return '';
    return devariant;
}

export function buildDialectTags(csvText) {
    const lines = csvText.replace(/^\uFEFF/, '').split(/\r?\n/).filter(Boolean);
    const header = parseCsvLine(lines[0]);
    const col = name => header.indexOf(name);
    const groupIdx = col('组别');
    const idIdx = col('movie_id');
    const tagIdx = col('命中方言标签');

    const tags = {};
    const counts = {};
    for (const line of lines.slice(1)) {
        const cells = parseCsvLine(line);
        if (cells[groupIdx] === '非方言') continue;
        const tag = normalizeDialectTag(cells[tagIdx]);
        if (!tag) continue;
        const movieId = String(cells[idIdx]);
        tags[movieId] = tag;
        counts[tag] = (counts[tag] || 0) + 1;
    }
    const families = Object.entries(counts)
        .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
        .map(([name, n]) => ({ name, n }));
    return { tags, families };
}

if (process.argv[1] && process.argv[1].endsWith('build_dialect_tags.mjs')) {
    const { tags, families } = buildDialectTags(readFileSync(SOURCE, 'utf8'));
    const payload = {
        meta: {
            source: 'data/dialect_films/方言片明细报告.csv',
            rule: '组别=非方言 剔除；混合语种取首位；仅做同名变体归并',
            generatedAt: new Date().toISOString().slice(0, 10)
        },
        tags,
        families
    };
    writeFileSync(TARGET, `${JSON.stringify(payload)}\n`, 'utf8');
    console.log(`dialect_tags.json: ${Object.keys(tags).length} 部影片，${families.length} 个方言族`);
    console.log(families.slice(0, 12).map(f => `${f.name}=${f.n}`).join('  '));
}
