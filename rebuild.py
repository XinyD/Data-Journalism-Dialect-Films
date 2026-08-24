"""Rebuild publication artifacts from the bundled canonical snapshot."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-source",
        type=Path,
        help="Optionally rebuild the canonical sample from an upstream movies_info.csv first.",
    )
    return parser.parse_args()


def run(script: str, *arguments: str) -> None:
    command = [sys.executable, str(SCRIPTS / script), *arguments]
    print(f"\n> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    if args.from_source:
        source = args.from_source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Upstream source not found: {source}")
        print(
            "\n--from-source rebuilds derived_movies.csv and drops Dialect_Evidence.\n"
            "This command stops after data_processor so publication artifacts stay on the\n"
            "current patched snapshot. Restore the frozen baseline, then rebuild:\n"
            f"  {sys.executable} scripts/replay_v44_baseline.py --full-rebuild --source {source}\n",
            flush=True,
        )
        run("data_processor.py", "--source", str(source), "--overwrite-tier2b")
        print(
            "Canonical CSV rebuilt. Run scripts/replay_v44_baseline.py next, then python rebuild.py.",
            flush=True,
        )
        return

    run("data_aggregator.py")
    run("extract_narrative.py")
    run("generate_particles.py")
    run("build_geo_enrichment.py")
    run("build_story_universe.py")
    run("gen_report_strict.py")
    print("\nPublication artifacts rebuilt successfully.", flush=True)


if __name__ == "__main__":
    main()
