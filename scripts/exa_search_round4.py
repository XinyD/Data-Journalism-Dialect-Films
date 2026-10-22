# -*- coding: utf-8 -*-
"""第四轮：继续挖剩余存活 key——短视频/说唱、博物馆声景、国际声音档案库、
政策统计、语言活力理论、中国语言地图集数字版、更多技术教程等新角度。"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from exa_py import Exa

from exa_keys import load_keys

BASE = r"F:\Data-Journalism-Dialect-Films\references\exa"

# 由环境变量提供本次可用的 key；探测只用于剔除本次失效的。
ALL_KEYS = load_keys()

def try_key(key):
    try:
        Exa(api_key=key).search(query="dialect", type="neural", num_results=1)
        return True
    except Exception:
        return False

print(f"探测 {len(ALL_KEYS)} 个 key:")
with ThreadPoolExecutor(max_workers=14) as pool:
    alive = [key for key, ok in zip(ALL_KEYS, pool.map(try_key, ALL_KEYS)) if ok]
print(f"仍可用：{len(alive)} 个\n")
if not alive:
    sys.exit("没有可用 key 了")

QUERIES = [
    # 平台与内容生态
    {"q": "方言 短视频 抖音 快手 主播 传承 内容生态 研究", "num": 5, "tag": "生态-短视频方言"},
    {"q": "方言说唱 说唱歌手 地域认同 音乐数据 分析", "num": 5, "tag": "生态-方言说唱"},
    {"q": "dialect TikTok creator language revitalization social media gen z", "num": 5, "tag": "生态-TikTok"},
    {"q": "方言表情包 梗 传播 网络语言 年轻人 论文", "num": 5, "tag": "生态-表情包"},
    # 声音档案与博物馆
    {"q": "British Library sound archive endangered languages recordings collection", "num": 5, "tag": "档案-大英图书馆"},
    {"q": "ELAR PARADISEC language archive documentation digital preservation platform", "num": 5, "tag": "档案-ELAR"},
    {"q": "museum interactive sound installation dialect voices exhibit multimedia design", "num": 5, "tag": "展陈-博物馆声景"},
    {"q": "声音博物馆 声音地图 城市 声音遗产 项目", "num": 5, "tag": "展陈-声音地图"},
    # 政策与统计数据
    {"q": "台湾 国家语言发展法 语言保存 成效 报告 数据", "num": 5, "tag": "政策-台湾语发法"},
    {"q": "香港 统计 惯用语言 比例 粤语 普通话 人口普查", "num": 5, "tag": "政策-香港语言统计"},
    {"q": "中国语言地图集 汉语方言分区 数字版 交互 在线", "num": 5, "tag": "数据-中国语言地图集"},
    {"q": "国家语委 语言文字 信息化 平台 开放数据 方言", "num": 5, "tag": "数据-语委平台"},
    # 理论与深度研究
    {"q": "ethnolinguistic vitality dialect vitality measurement framework sociolinguistics", "cat": "research paper", "num": 5, "tag": "论文-语言活力"},
    {"q": "documentary linguistics archival accountability language documentation theory", "cat": "research paper", "num": 5, "tag": "论文-纪录语言学"},
    {"q": "第六代导演 地域空间 方言 城市影像 研究", "num": 5, "tag": "论文-第六代导演"},
    {"q": "dialect comedy sketch satire regional identity television China", "num": 5, "tag": "论文-方言喜剧"},
    # AI 延伸
    {"q": "voice cloning last speaker dying language ethics documentary", "num": 5, "tag": "AI-声音克隆伦理"},
    {"q": "huggingface cantonese shanghainese minnan tts asr model open source", "num": 5, "tag": "AI-方言开源模型"},
    # 技术深水区（给 universe_canvas / 动效升级用）
    {"q": "Web Audio API waveform visualization canvas real time microphone tutorial", "num": 5, "tag": "技术-WebAudio"},
    {"q": "GSAP ScrollTrigger pinned section cinematic storytelling web animation best", "num": 5, "tag": "技术-GSAP滚动"},
    {"q": "WebGL shader fluid ripple audio reactive creative coding example", "num": 5, "tag": "技术-音频响应shader"},
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
         f"共 {len(base_items)} 条（四轮搜索去重后）。", ""]
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
    json.dump(fails, open(os.path.join(BASE, "failures_round4.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

print("\n—— 本轮新增高分条目 ——")
for it in sorted(new_all, key=lambda x: -(x["score"] or 0))[:30]:
    print(f"{it['score']:.2f} [{it['tag']}] {it['title']} | {it['url']}")
print(f"\n总计 {len(base_items)} 条；本轮新增 {len(new_all)}；失败 {len(fails)} 组")
