# -*- coding: utf-8 -*-
"""第三轮：全新角度继续挖掘；复用上轮探明的存活 key，补测超时的 key#01。"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from exa_py import Exa

from exa_keys import load_keys

BASE = r"F:\Data-Journalism-Dialect-Films\references\exa"

# 由环境变量提供本次可用的 key；探测只用于剔除本次失效的。
ALL_KEYS = load_keys()

def try_key(key):
    try:
        Exa(api_key=key).search(query="dialect film", type="neural", num_results=1)
        return True
    except Exception as e:
        print(f"  补测失败: {str(e)[:60]}")
        return False

print(f"探测 {len(ALL_KEYS)} 个 key:")
alive = [key for key in ALL_KEYS if try_key(key)]
print(f"可用 key：{len(alive)} 个\n")
if not alive:
    sys.exit("没有可用 key 了")

QUERIES = [
    {"q": "The Pudding visual essay film dialogue movie data visualization", "num": 6, "tag": "标杆-Pudding"},
    {"q": "Wikitongues every language in the world video archive volunteer", "num": 4, "tag": "标杆-Wikitongues"},
    {"q": "Google Arts Culture language experiment endangered voice AI exhibit", "num": 5, "tag": "标杆-Google文化"},
    {"q": "UNESCO atlas world languages in danger ELCat catalogue data download", "num": 5, "tag": "数据-UNESCO语言"},
    {"q": "中国方言纪录片 影像志 央视 乡愁 消失的语言 抢救记录", "num": 5, "tag": "中文-方言纪录片"},
    {"q": "吴语 保留 卫星 杭州话 上海话 保护 组织 社群 网站", "num": 5, "tag": "中文-吴语社群"},
    {"q": "粤语 客家话 闽南语 保育 运动 香港 台湾 年轻人", "num": 5, "tag": "中文-南方方言情愿"},
    {"q": "heritage language attrition second generation immigrant linguistic shift research", "cat": "research paper", "num": 5, "tag": "论文-继承语流失"},
    {"q": "place name toponymy etymology interactive map dialect region naming", "num": 5, "tag": "作品-地名地图"},
    {"q": "data humanism hand drawn illustration infographic editorial design trend 2025", "num": 5, "tag": "设计-数据人文主义"},
    {"q": "chinese character variable font generative typography code design system", "num": 5, "tag": "设计-汉字字体"},
    {"q": "scrollama intersection observer scrollytelling boilerplate template github starter", "num": 5, "tag": "技术-scrolly模板"},
    {"q": "korsakow interactive documentary database narrative interview archive software", "num": 4, "tag": "电影-i-doc工具"},
    {"q": "口述历史 影像 数据库 中国 城市 村庄 记忆 工程 档案馆", "num": 5, "tag": "中文-口述史工程"},
    {"q": "regional inequality china cinema box office city tier data analysis", "num": 5, "tag": "数据-院线地域"},
    {"q": "collective memory digital humanities local history mapping project academic", "num": 5, "tag": "论文-集体记忆地图"},
    {"q": "eye tracking reading engagement scrollytelling comprehension multimedia journalism study", "cat": "research paper", "num": 5, "tag": "论文-眼动研究"},
    {"q": "speech corpus phonetics prosody audio visualization Praat linguistic sound map", "num": 5, "tag": "工具-语音库可视化"},
    {"q": "deck.gl kepler.gl flow map large scale visualization storytelling example github", "num": 5, "tag": "技术-deck.gl案例"},
    {"q": "annotated line chart step by step storytelling data visualization principles moneyball", "num": 4, "tag": "方法-注释叙事图"},
]

def norm_url(u):
    return re.sub(r"[?#].*$", "", u.rstrip("/"))

def run(iq, ki):
    q, num, tag = iq["q"], iq["num"], iq["tag"]
    cat = iq.get("cat")
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

new_all, fails = [], []
with ThreadPoolExecutor(max_workers=7) as pool:
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
            seen.add(k); base_items.append(it); new_all.append(it); n += 1
        print(f"[OK] {iq['tag']}: {len(items)} 条 / 新增 {n}")

json.dump(base_items, open(os.path.join(BASE, "exa_results.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

lines = ["# Exa 搜索结果：可借鉴的数据新闻作品与文献", "",
         f"共 {len(base_items)} 条（三轮搜索去重后）。", ""]
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
    json.dump(fails, open(os.path.join(BASE, "failures_round3.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

print("\n—— 本轮新增高分条目 ——")
for it in sorted(new_all, key=lambda x: -(x["score"] or 0))[:30]:
    print(f"{it['score']:.2f} [{it['tag']}] {it['title']} | {it['url']}")
print(f"\n总计 {len(base_items)} 条；本轮新增 {len(new_all)}；失败 {len(fails)} 组")
