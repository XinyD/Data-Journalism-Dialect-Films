# -*- coding: utf-8 -*-
"""用 Exa 并行搜索可供借鉴的数据新闻作品与文献，存到 references/exa/。"""
import json, os, re, sys, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from exa_py import Exa

from exa_keys import load_keys

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "references", "exa")
os.makedirs(OUT_DIR, exist_ok=True)

KEYS = load_keys()

QUERIES = [
    # —— 可借鉴的交互数据新闻作品（英文）——
    {"q": "interactive data journalism endangered languages dialects visualization scrollytelling", "cat": None, "num": 6, "tag": "作品-濒危语言"},
    {"q": "New York Times Guardian interactive story language loss multimedia", "cat": None, "num": 6, "tag": "作品-媒体大屏"},
    {"q": "award winning data visualization cultural heritage film cinema interactive", "cat": None, "num": 6, "tag": "作品-文化/电影"},
    {"q": "data sonification sound in data journalism audio storytelling dialect", "cat": None, "num": 5, "tag": "作品-可听化"},
    {"q": "dialect map interactive linguistic atlas visualization project", "cat": None, "num": 6, "tag": "作品-方言地图"},
    {"q": "scrollytelling best practices narrative visualization journalism case study", "cat": None, "num": 5, "tag": "方法-scrollytelling"},
    # —— 可借鉴的中文作品 ——
    {"q": "数据新闻 方言 保护 交互作品 可视化", "cat": None, "num": 6, "tag": "中文-方言数据新闻"},
    {"q": "方言电影 中国电影 方言使用 研究", "cat": None, "num": 6, "tag": "中文-方言电影研究"},
    {"q": "乡音 方言 融媒体 H5 交互 新闻作品", "cat": None, "num": 5, "tag": "中文-H5作品"},
    {"q": "中国语言资源保护工程 方言 数据 可视化", "cat": None, "num": 5, "tag": "中文-语保工程"},
    # —— 学术文献 ——
    {"q": "dialect in Chinese cinema language identity film studies", "cat": "research paper", "num": 5, "tag": "论文-方言与电影"},
    {"q": "language endangerment documentation revitalization digital tools", "cat": "research paper", "num": 5, "tag": "论文-濒危语言数字化"},
    {"q": "data journalism scrollytelling audience engagement research", "cat": "research paper", "num": 5, "tag": "论文-数据新闻"},
    {"q": "linguistic landscape dialect perception attitudes survey China", "cat": "research paper", "num": 5, "tag": "论文-语言态度"},
    {"q": "multimodal storytelling cultural memory visualization humanities", "cat": "research paper", "num": 5, "tag": "论文-文化记忆"},
]

def norm_url(u):
    return re.sub(r"[?#].*$", "", u.rstrip("/"))

def run(iq, key_offset=0):
    q, cat, num, tag = iq["q"], iq["cat"], iq["num"], iq["tag"]
    last_err = None
    for attempt in range(len(KEYS)):
        key = KEYS[(hash(tag) + key_offset + attempt) % len(KEYS)]
        exa = Exa(api_key=key)  # 每次调用新建实例，避免连接冲突
        kw = {"query": q, "type": "neural", "num_results": num,
              "contents": {"text": {"maxCharacters": 4000}}}
        if cat:
            kw["category"] = cat
        try:
            resp = exa.search(**kw)
            break
        except Exception as e:
            msg = str(e)
            if "401" in msg or "403" in msg or "429" in msg or "timeout" in msg.lower():
                last_err = e
                continue
            raise
    else:
        raise last_err or RuntimeError("all keys failed")
    out = []
    for r in resp.results:
        out.append({"title": r.title, "url": r.url, "score": getattr(r, "score", None),
                    "published": getattr(r, "published_date", None),
                    "text": (r.text or "")[:4000], "tag": tag, "query": q})
    return tag, out

def main():
    seen, all_items, failures = set(), [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(run, iq): iq for iq in QUERIES}
        for f in as_completed(futs):
            iq = futs[f]
            try:
                tag, items = f.result()
            except Exception as e:
                failures.append({"query": iq["q"], "error": str(e)})
                print(f"[FAIL] {iq['tag']}: {e}")
                continue
            new = 0
            for it in items:
                k = norm_url(it["url"])
                if k in seen:
                    continue
                seen.add(k)
                all_items.append(it)
                new += 1
            print(f"[OK] {iq['tag']}: {len(items)} 条 / 新增 {new}")

    with open(os.path.join(OUT_DIR, "exa_results.json"), "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    # 生成可读的 Markdown 索引，按 tag 分组
    lines = ["# Exa 搜索结果：可借鉴的数据新闻作品与文献", "",
             f"共 {len(all_items)} 条（{len(QUERIES)} 组查询，去重后）。", ""]
    by_tag = {}
    for it in all_items:
        by_tag.setdefault(it["tag"], []).append(it)
    for tag in sorted(by_tag):
        lines.append(f"## {tag}\n")
        for it in sorted(by_tag[tag], key=lambda x: -(x["score"] or 0)):
            pub = f"（{it['published'][:10]}）" if it.get("published") else ""
            lines.append(f"### [{it['title']}]({it['url']}){pub}")
            lines.append(f"相关度 {it['score']:.3f} | 查询: {it['query']}")
            excerpt = (it["text"] or "").strip().replace("\n", " ")[:300]
            if excerpt:
                lines.append("")
                lines.append(f"> {excerpt}")
            lines.append("")
    with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    if failures:
        with open(os.path.join(OUT_DIR, "failures.json"), "w", encoding="utf-8") as f:
            json.dump(failures, f, ensure_ascii=False, indent=2)
    print(f"\n完成：{len(all_items)} 条已存至 {os.path.abspath(OUT_DIR)}，失败 {len(failures)} 组")

if __name__ == "__main__":
    main()
