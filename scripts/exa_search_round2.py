# -*- coding: utf-8 -*-
"""第二轮：先探测存活 key，再用更多角度批量搜索，追加到 references/exa/。"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from exa_py import Exa

from exa_keys import load_keys

BASE = r"F:\Data-Journalism-Dialect-Films\references\exa"

KEYS = load_keys()

# —— 第 1 步：探测存活 key（每 key 只花 1 次调用）——
def probe(key):
    try:
        Exa(api_key=key).search(query="dialect", type="neural", num_results=1)
        return key, "alive"
    except Exception as e:
        m = str(e)
        if "402" in m: return key, "credits"
        if "401" in m: return key, "invalid"
        if "403" in m: return key, "blocked"
        return key, f"other:{m[:40]}"

alive = []
with ThreadPoolExecutor(max_workers=11) as pool:
    for key, status in pool.map(probe, KEYS):
        i = KEYS.index(key)
        print(f"key#{i:02d}: {status}")
        if status == "alive":
            alive.append(key)
print(f"\n存活 key：{len(alive)} 个")
if not alive:
    sys.exit("没有可用 key 了")

# —— 第 2 步：第二轮查询（更新颖的角度）——
QUERIES = [
    # 获奖作品库 / 年度精选
    {"q": "Information is Beautiful Awards winning visualization language culture", "cat": None, "num": 6, "tag": "奖-IIB获奖"},
    {"q": "Sigma Awards data journalism best small newsroom visual story", "cat": None, "num": 5, "tag": "奖-Sigma"},
    {"q": "Malofiej infographics world best design newspaper culture", "cat": None, "num": 4, "tag": "奖-Malofiej"},
    {"q": "Peabody SXSW interactive documentary immersive journalism award winner", "cat": None, "num": 4, "tag": "奖-互动纪录"},
    # 中文主流媒体数据新闻栏目
    {"q": "澎湃新闻 美数课 数据新闻 传统文化 方言 地域", "cat": None, "num": 6, "tag": "中文-美数课"},
    {"q": "网易数读 新京报数说 澎湃 数据可视化 电影 市场", "cat": None, "num": 5, "tag": "中文-电影数据"},
    {"q": "端传媒 FT中文网 数据新闻 互动 城市 语言", "cat": None, "num": 5, "tag": "中文-港台数据新闻"},
    {"q": "回乡记 春节 返乡 报道 数据新闻 家乡 记忆", "cat": None, "num": 5, "tag": "中文-故乡记忆"},
    # 语言/方言细分题材
    {"q": "Cantonese Shanghainese Hokkien endangered overseas diaspora community", "cat": None, "num": 5, "tag": "方言- diaspora"},
    {"q": "immigrant grandmother oral history voice recording project interactive", "cat": None, "num": 5, "tag": "方言-口述史"},
    {"q": "accent bias discrimination linguistics journalism story", "cat": None, "num": 5, "tag": "方言-口音歧视"},
    {"q": "普通话推广 方言衰落 代际 传承 调查", "cat": None, "num": 5, "tag": "方言-代际流失"},
    # 电影 / 声音交叉
    {"q": "film dialogue dataset analysis screen time race language", "cat": None, "num": 5, "tag": "电影-台词数据"},
    {"q": "interactive documentary i-doc webdoc film participatory storytelling", "cat": None, "num": 5, "tag": "电影-i-doc"},
    {"q": "podcast audio series dialect voice of a place soundscape city", "cat": None, "num": 4, "tag": "电影-声音地标"},
    # AI 与语言保护（前沿角度）
    {"q": "AI large language model low-resource dialect preservation speech synthesis", "cat": None, "num": 5, "tag": "AI-低资源语言"},
    {"q": "Whisper ASR fine-tune regional accent transcription project github", "cat": None, "num": 5, "tag": "AI-语音识别"},
    {"q": "大模型 方言 语音 数字人 非遗 保护 应用", "cat": None, "num": 5, "tag": "AI-方言大模型"},
    # 技术：WebGL canvas 大屏实现
    {"q": "WebGL particle flow field globe visualization storytelling three.js tutorial", "cat": None, "num": 5, "tag": "技术-粒子地球"},
    {"q": "ECharts custom animation scrollytelling china map province tutorial", "cat": None, "num": 5, "tag": "技术-ECharts地图"},
]

def norm_url(u):
    return re.sub(r"[?#].*$", "", u.rstrip("/"))

def run(iq, ki):
    q, cat, num, tag = iq["q"], iq["cat"], iq["num"], iq["tag"]
    last = None
    for off in range(len(alive)):
        key = alive[(ki + off) % len(alive)]
        try:
            kw = dict(query=q, type="neural", num_results=num,
                      contents={"text": {"maxCharacters": 4000}})
            if cat:
                kw["category"] = cat
            resp = Exa(api_key=key).search(**kw)
            return tag, [{"title": r.title, "url": r.url,
                          "score": getattr(r, "score", None),
                          "published": getattr(r, "published_date", None),
                          "text": (r.text or "")[:4000],
                          "tag": tag, "query": q} for r in resp.results]
        except Exception as e:
            last = e
            continue
    raise last or RuntimeError("no key")

base_items = json.load(open(os.path.join(BASE, "exa_results.json"), encoding="utf-8"))
seen = {norm_url(x["url"]) for x in base_items}

new_all = []
fails = []
with ThreadPoolExecutor(max_workers=8) as pool:
    futs = {pool.submit(run, iq, i): iq for i, iq in enumerate(QUERIES)}
    for f in as_completed(futs):
        iq = futs[f]
        try:
            tag, items = f.result()
        except Exception as e:
            fails.append({"query": iq["q"], "error": str(e)[:200]})
            print(f"[FAIL] {iq['tag']}: {str(e)[:80]}")
            continue
        n = 0
        for it in items:
            k = norm_url(it["url"])
            if k in seen:
                continue
            seen.add(k)
            base_items.append(it)
            new_all.append(it)
            n += 1
        print(f"[OK] {iq['tag']}: {len(items)} 条 / 新增 {n}")

json.dump(base_items, open(os.path.join(BASE, "exa_results.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# 重建 README
lines = ["# Exa 搜索结果：可借鉴的数据新闻作品与文献", "",
         f"共 {len(base_items)} 条（两轮搜索去重后）。", ""]
by_tag = {}
for it in base_items:
    by_tag.setdefault(it["tag"], []).append(it)
for tag in sorted(by_tag):
    lines.append(f"## {tag}\n")
    for it in sorted(by_tag[tag], key=lambda x: -(x["score"] or 0)):
        pub = f"（{it['published'][:10]}）" if it.get("published") else ""
        lines.append(f"### [{it['title']}]({it['url']}){pub}")
        lines.append(f"相关度 {it['score']:.3f} | 查询: {it['query']}")
        ex = (it["text"] or "").strip().replace("\n", " ")[:300]
        if ex:
            lines.append("")
            lines.append(f"> {ex}")
        lines.append("")
open(os.path.join(BASE, "README.md"), "w", encoding="utf-8").write("\n".join(lines))
if fails:
    json.dump(fails, open(os.path.join(BASE, "failures_round2.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

print("\n—— 本轮新增高分条目 ——")
for it in sorted(new_all, key=lambda x: -(x["score"] or 0))[:25]:
    print(f"{it['score']:.2f} [{it['tag']}] {it['title']} | {it['url']}")
print(f"\n总计 {len(base_items)} 条；本轮新增 {len(new_all)}；失败 {len(fails)} 组")
