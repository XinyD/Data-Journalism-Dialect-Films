"""F7 修正：《平壤之约》Region China -> East_Asia（2026-08-15 决定，重建后回退需重应用）。

只读检查模式：--check（默认）；--apply 落地修正并重算指纹。
Is_Dialect=0，不影响方言口径；仅影响 Region 分布。
"""
import json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd
from config import DERIVED_MOVIES_INFO, SAMPLE_MANIFEST
from data_processor import publication_fingerprint, REGION_CODES

MOVIE_ID = "10478122"  # 平壤之约（中朝合拍朝鲜语题材，Region 应为 East_Asia）

df = pd.read_csv(DERIVED_MOVIES_INFO, encoding="utf-8-sig", low_memory=False,
                 dtype={"movie_id": "str"})
rows = df[df["movie_id"] == MOVIE_ID]
if len(rows) != 1:
    print(f"ERROR: movie_id {MOVIE_ID} found {len(rows)} times")
    sys.exit(1)

i = rows.index[0]
print(f"当前状态: Region={df.at[i, 'Region']} Is_Dialect={df.at[i, 'Is_Dialect']} "
      f"制片={df.at[i, '制片国家/地区']}")

if "--apply" not in sys.argv:
    print("(--check 模式，未修改)")
    sys.exit(0)

if df.at[i, "Region"] == "East_Asia":
    print("已是 East_Asia，无需修改")
    sys.exit(0)

BACKUP = ROOT / "data" / "derived_movies_f7_region_backup_20260818.csv"
shutil.copy2(DERIVED_MOVIES_INFO, BACKUP)

df.at[i, "Region"] = "East_Asia"
df.at[i, "Region_Code"] = REGION_CODES["East_Asia"]

# 不变量：Is_Dialect 不变（应为 0）。China D1 计数由后续补丁链决定，不在此冻结。
assert int(df.at[i, "Is_Dialect"]) == 0, "平壤之约应为非方言片"

df.to_csv(DERIVED_MOVIES_INFO, index=False, encoding="utf-8-sig")

fp = publication_fingerprint(df)
manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
manifest["sample_fingerprint_sha256"] = fp
manifest["counts"]["region"] = df["Region"].value_counts().sort_index().to_dict()
manifest["f7_region_fix_20260818"] = {
    "applied_by": "scripts/apply_f7_region_fix_20260818.py",
    "movie_id": MOVIE_ID,
    "change": "Region China -> East_Asia（平壤之约，中朝合拍朝鲜语题材，2026-08-15 决定重应用）",
    "dialect_impact": "无（Is_Dialect=0，China 方言计数不变 3090）",
}
SAMPLE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"已修正并写入 manifest，新指纹: {fp[:12]}...")
