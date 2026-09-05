import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeDialectTag, buildDialectTags } from '../scripts/build_dialect_tags.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

test('normalizeDialectTag 合并同名变体', () => {
    assert.equal(normalizeDialectTag('粵語'), '粤语');
    assert.equal(normalizeDialectTag('閩南語'), '闽南语');
    assert.equal(normalizeDialectTag('台语'), '闽南语');
    assert.equal(normalizeDialectTag('蒙语'), '蒙古语');
    assert.equal(normalizeDialectTag('沪语'), '上海话');
});

test('normalizeDialectTag 混合语种取首位（与主站语言分组规则一致）', () => {
    assert.equal(normalizeDialectTag('粤语 / 上海话'), '粤语');
    assert.equal(normalizeDialectTag('粤语，台语，四川话'), '粤语');
    assert.equal(normalizeDialectTag('中文方言 – 常州话'), '');
});

test('normalizeDialectTag 统一方言后缀', () => {
    assert.equal(normalizeDialectTag('四川方言'), '四川话');
    assert.equal(normalizeDialectTag('湖南当地方言'), '湖南话');
    assert.equal(normalizeDialectTag('河南方言'), '河南话');
});

test('normalizeDialectTag 丢弃无辨别力的统称与空值', () => {
    assert.equal(normalizeDialectTag(''), '');
    assert.equal(normalizeDialectTag('方言'), '');
    assert.equal(normalizeDialectTag('中文话'), '');
});

test('buildDialectTags 跳过对照组并统计方言族', () => {
    const csv = [
        '组别,movie_id,片名,年份,豆瓣评分,评价人数,类型,Decade,语言字段原文,归一化语言,命中方言标签,方言大区,Tier层级,方言占比（推断）,占比推断依据,来源URL',
        '方言片,1,甲,1998,7.5,100,剧情,1990s,粤语,粤语,粤语,粤语,Tier 1,≈100%,x,https://a',
        '方言片,2,乙,2016,8.0,200,剧情,2010s,四川方言,四川方言,四川方言,四川话,Tier 1,≈100%,x,https://b',
        '非方言,3,丙,2016,6.0,300,剧情,2010s,普通话,普通话,,普通话,非方言,,x,https://c'
    ].join('\n');
    const { tags, families } = buildDialectTags(csv);
    assert.deepEqual(tags, { '1': '粤语', '2': '四川话' });
    // 同部数时按码点序排列，保证跨环境生成结果一致
    assert.deepEqual(families, [{ name: '四川话', n: 1 }, { name: '粤语', n: 1 }]);
});

test('生成的 dialect_tags.json 与发布数据集可连接', () => {
    const payload = JSON.parse(readFileSync(join(root, 'data', 'frontend', 'dialect_tags.json'), 'utf8'));
    const dataset = JSON.parse(readFileSync(join(root, 'data', 'frontend_dataset.json'), 'utf8'));
    const ids = new Set(dataset.records.map(row => String(row[0])));
    const taggedIds = Object.keys(payload.tags);
    assert.ok(taggedIds.length > 3000, `应有三千部以上标签，实际 ${taggedIds.length}`);
    assert.ok(taggedIds.every(id => ids.has(id)), '每个标签 movieId 都应存在于发布数据集');

    const counted = new Map();
    taggedIds.forEach(id => counted.set(payload.tags[id], (counted.get(payload.tags[id]) || 0) + 1));
    const families = payload.families;
    assert.equal(families.reduce((sum, f) => sum + f.n, 0), taggedIds.length, '方言族计数合计应等于标签总数');
    assert.deepEqual(families.map(f => f.n), [...families.map(f => f.n)].sort((a, b) => b - a), '方言族按部数降序');
    assert.ok(families.every(f => counted.get(f.name) === f.n), '每个方言族的部数与逐片标签一致');
});
