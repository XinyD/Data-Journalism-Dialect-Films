# -*- coding: utf-8 -*-
"""sync_preview_dialect_v43_20260819.py — preview_dialect.html 全量重算同步（v4.3 口径）

ℹ 2026-08-19 起，本脚本的全部聚合口径已固化进
scripts/data_aggregator.py 的 build_dialect_aggregates()（产出 data/frontend/dialect_aggregates.json）。
本脚本保留作历史与口径出处证据，不再作为取值来源。

背景：页面内嵌 AGG 的 byDecade/yearly/flopDecade/canto/diversity 等块转录自
archive/preview_aggregates.json（2026-08-17 16:03 生成，口径 3,090/7,789 的过渡态快照，
已不存在于任何冻结基线）。本脚本从 data/cleaned/derived_movies.csv（v4.3，指纹 3049f41485）
重算全部预计算数值，输出对照报告供人工核对后写入 frontend/preview_dialect.html。

口径定义（全部 Region=China，除非另注）：
- dialect  = Is_Dialect==1；mandarin = Is_Dialect==0
- below5   = 豆瓣评分<5 占比（烂片率）；high8 = >=8 占比
- yearly   = 逐年均分差（方言-普通话），双方 n>=5，范围 1990-2020
- canto    = 方言片中语言字段含/不含"粤语"
- diversity= 方言片按 dialect_defs.lang_parts 拆分语言标签，min n>=10（仅中国方言语言）
- global   = 六层烂片率对比；欧洲子层用 Language_Category 划分（全 Region 口径）
- director = 双栖导演（方言/普通话片各>=1 部），hist(round(方言均分-普通话均分))
- genreAvg = 方言片按"类型"字段标签展开，min n>=30，按均分取 top8，各配 top3 片单
"""
import json
import sys
import io
import os
from collections import defaultdict

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'scripts'))
from dialect_defs import lang_parts  # noqa: E402

df = pd.read_csv(os.path.join(BASE, 'data', 'cleaned', 'derived_movies.csv'), low_memory=False)
R, V = '豆瓣评分', '评价人数'
ch = df[df['Region'] == 'China']
d = ch[ch['Is_Dialect'] == 1]
m = ch[ch['Is_Dialect'] == 0]


def b5(s):
    return round((s[R] < 5).mean() * 100, 1)


def h8(s):
    return round((s[R] >= 8).mean() * 100, 1)


print('=' * 72)
print('byDecade（JS 字面量）')
print('=' * 72)
decades = ['Pre-1990s', '1990s', '2000s', '2010s', '2020s']
for dec in decades:
    dd = d[d['Decade'].astype(str) == dec]
    mm = m[m['Decade'].astype(str) == dec]
    delta = round(dd[R].mean() - mm[R].mean(), 2)
    print(f'    "{dec}": {{d: {{n:{len(dd)},mean:{dd[R].mean():.2f},below5:{b5(dd)}}}, '
          f'm:{{n:{len(mm)},mean:{mm[R].mean():.2f},below5:{b5(mm)}}}, delta:{delta}}},')

print('\nflopDecade（JS 字面量）')
rows = []
for dec in ['1990s', '2000s', '2010s', '2020s']:
    dd = d[d['Decade'].astype(str) == dec]
    mm = m[m['Decade'].astype(str) == dec]
    rows.append(f'"{dec}": {{d:{b5(dd)}, m:{b5(mm)}}}')
print('    ' + ', '.join(rows[:2]) + ',')
print('    ' + ', '.join(rows[2:]))

print('\nyearly（JS 字面量, 1990-2020, min n>=5）')
ys = {}
for y in range(1990, 2021):
    dy = d[d['年份'] == y]
    my = m[m['年份'] == y]
    if len(dy) >= 5 and len(my) >= 5:
        ys[y] = round(dy[R].mean() - my[R].mean(), 2)
print('    ' + json.dumps({str(k): v for k, v in ys.items()}, ensure_ascii=False))

print('\n文案关键值')
d10 = d[d['Decade'].astype(str) == '2010s']
m10 = m[m['Decade'].astype(str) == '2010s']
print(f'2010s: 方言 n={len(d10)} 烂片率={b5(d10)}% 关注度均值={round(d10[V].mean()):,}')
print(f'2010s: 普通话 n={len(m10)} 烂片率={b5(m10)}% 关注度均值={round(m10[V].mean()):,}')
print(f'产量倍数: {len(m10)/len(d10):.1f}x | 踩雷率倍数: {b5(m10)/b5(d10):.1f}x')
d90 = d[d['Decade'].astype(str) == '1990s']
m90 = m[m['Decade'].astype(str) == '1990s']
gap90 = round(m90[R].mean() - d90[R].mean(), 2)
gap10 = round(d10[R].mean() - m10[R].mean(), 2)
print(f'1990s 普通话领先 {gap90} | 2010s 方言反超 {gap10} | 摆幅 {round(gap90+gap10,2)}')
y2010d = d[d['年份'] == 2010]
y2010m = m[m['年份'] == 2010]
print(f'2010 断点: 方言 {y2010d[R].mean():.2f}(n={len(y2010d)}) vs 普通话 {y2010m[R].mean():.2f}(n={len(y2010m)})')
neg_after = [y for y in range(2011, 2021) if ys.get(y, 1) < 0]
print(f'2011-2020 反转年份(yearly<0): {neg_after or "无"}')
dr = ch[ch['Genre_Code'] == 0]
print(f'L215 纠偏卡(纯剧情 high8): 方言 {h8(dr[dr["Is_Dialect"]==1])}% vs 普通话 {h8(dr[dr["Is_Dialect"]==0])}%')

print('\ncanto（JS 字面量）')
canto = d[d['语言'].astype(str).str.contains('粤语')]
non = d[~d['语言'].astype(str).str.contains('粤语')]
print(f'    {{name:"非粤语方言", value:{non[R].mean():.2f}, below5:{b5(non)}, n:{len(non)}, color:"#5cc8a1"}},')
print(f'    {{name:"粤语", value:{canto[R].mean():.2f}, below5:{b5(canto)}, n:{len(canto)}, color:"#ffc24b"}}')

print('\ndiversity top10（仅中国方言语言, min n>=10）')
CHINESE_DIALECT_TAGS = {'粤语', '闽南语', '台语', '上海话', '四川话', '重庆话', '客家话', '晋语',
                        '维吾尔语', '藏语', '东北话', '河南话', '陕西话', '湖南话', '山东话',
                        '吴语', '赣语', '湘语', '蒙语', '哈萨克语', '彝语', '壮语', '潮汕话',
                        '南京话', '武汉话', '广州话', '方言', '唐山话', '天津话', '贵州话',
                        '云南话', '山西话', '河北话', '江淮官话', '手语'}
vals = defaultdict(list)
for _, row in d.iterrows():
    lang = row['语言'] if pd.notna(row['语言']) else ''
    for p in lang_parts(str(lang)):
        if p in CHINESE_DIALECT_TAGS:
            vals[p].append(row[R])
rows = sorted(((k, sum(v) / len(v), len(v)) for k, v in vals.items() if len(v) >= 10),
              key=lambda x: -x[1])[:10]
for k, mean, n in rows:
    print(f'    {{name:"{k}", mean:{mean:.2f}, n:{n}}},')

print('\nglobal 六层（below5% / n，全 Region 子层 + China 层）')
eu = df[df['Region'] == 'Europe']
na = df[df['Region'] == 'North_America']
jk = df[df['Region'] == 'East_Asia']
layers = [
    ('欧洲 · 非主导语言', eu[eu['Language_Category'] == 'European_Languages']),
    ('欧洲 · 英语', eu[eu['Language_Category'] == 'English']),
    ('日韩', jk),
    ('华语 · 方言', d),
    ('北美 · 英语', na[na['Language_Category'] == 'English']),
    ('华语 · 普通话', m),
]
for name, s in layers:
    print(f'    {{name:"{name}", value:{b5(s)}, n:{len(s)}}},')
nf = json.load(open(os.path.join(BASE, 'data', 'narrative_facts.json'), encoding='utf-8'))
ne = nf['europe']
print(f"交叉验证 narrative europe: n={ne['n']} below5={ne['below_five_share']:.2f}% | "
      f"欧洲全量实算: n={len(eu)} below5={b5(eu)}%")

print('\ndirectorHist + 5B 指标')
gd = d.groupby('导演')[R].agg(['mean', 'count'])
gm = m.groupby('导演')[R].agg(['mean', 'count'])
both = gd.index.intersection(gm.index)
diff = gd.loc[both, 'mean'] - gm.loc[both, 'mean']
rd = diff.round(0)
bins = {'≤−2': int((rd <= -2).sum()),
        '−1': int((rd == -1).sum()),
        '0': int((rd == 0).sum()),
        '+1': int((rd == 1).sum()),
        '+2': int((rd == 2).sum()),
        '+3': int((rd == 3).sum()),
        '≥+4': int((rd >= 4).sum())}
total = sum(bins.values())
print(f'    {json.dumps(bins, ensure_ascii=False)}')
print(f'5B: 双栖导演 {total} 位 | 方言更高占比 {round((diff > 0).mean() * 100)}% | 平均分差 {diff.mean():+.2f}')

print('\ngenreAvg（min n>=30, top8 by mean, 含 top3 片单）')
gvals = defaultdict(list)
for _, row in d.iterrows():
    tags = str(row['类型']) if pd.notna(row['类型']) else ''
    for tag in tags.replace('/', ',').replace('，', ',').split(','):
        tag = tag.strip()
        if tag and tag != 'nan':
            gvals[tag].append(row)
rows = sorted(((k, sum(r[R] for r in v) / len(v), v) for k, v in gvals.items() if len(v) >= 30),
              key=lambda x: -x[1])[:8]
for k, mean, films in rows:
    top = sorted(films, key=lambda r: -r[R])[:3]
    tops = ', '.join(
        f'{{title:"{t["片名"]}", year:{int(t["年份"])}, rating:{t[R]}, id:"{t["movie_id"]}"}}'
        for t in top)
    print(f'    {{name:"{k}", mean:{mean:.2f}, n:{len(films)}, top:[{tops}]}},')
allg = sorted(((k, sum(r[R] for r in v) / len(v), len(v)) for k, v in gvals.items() if len(v) >= 30),
              key=lambda x: -x[1])
print('全部类型(n>=30): ' + ' | '.join(f'{k}:{mean:.2f}/{n}' for k, mean, n in allg))
