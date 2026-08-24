"""Export the compact particle representation of the publication sample."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DERIVED_MOVIES_INFO, PARTICLES_DATASET, SAMPLE_MANIFEST


TITLE = "片名"
YEAR = "年份"
RATING = "豆瓣评分"
VOTES = "评价人数"
MOVIE_ID = "movie_id"


def main() -> None:
    frame = pd.read_csv(DERIVED_MOVIES_INFO, dtype={MOVIE_ID: "string"})
    manifest = json.loads(SAMPLE_MANIFEST.read_text(encoding="utf-8"))
    if len(frame) != manifest["publication_records"]:
        raise ValueError("Derived dataset and sample manifest have different record counts")

    columns = [
        TITLE, YEAR, RATING, "Region_Code", "Is_Dialect", "Genre_Code",
        "Language_Code", VOTES, MOVIE_ID,
    ]
    particles = []
    for values in frame[columns].itertuples(index=False, name=None):
        title, year, rating, region_code, is_dialect, genre_code, language_code, votes, movie_id = values
        particles.append([
            title,
            int(year),
            float(rating),
            int(region_code) + 1,
            1 if int(region_code) == 0 else 0,
            int(is_dialect),
            int(genre_code),
            int(language_code),
            int(votes),
            str(movie_id),
        ])

    payload = {
        "meta": {
            "schemaVersion": 2,
            "recordCount": len(particles),
            "minimumVoteCount": manifest["inclusion_criteria"]["minimum_vote_count"],
            "sampleFingerprint": manifest["sample_fingerprint_sha256"],
        },
        "records": particles,
    }
    PARTICLES_DATASET.parent.mkdir(parents=True, exist_ok=True)
    temporary = PARTICLES_DATASET.with_suffix(PARTICLES_DATASET.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    # Windows: Path.replace() fails if target is read-only; clear the flag first.
    try:
        temporary.replace(PARTICLES_DATASET)
    except PermissionError:
        if PARTICLES_DATASET.exists():
            os.chmod(PARTICLES_DATASET, stat.S_IWRITE | stat.S_IREAD)
            temporary.replace(PARTICLES_DATASET)
        else:
            raise
    print(f"Generated {len(particles):,} particles: {PARTICLES_DATASET}")


if __name__ == "__main__":
    main()
