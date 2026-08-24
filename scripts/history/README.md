# Historical one-shot scripts

These files are kept for audit traceability. They are **not** part of the publication pipeline.

Do not run them against the current v4.5 snapshot. Many still hard-code `Path(__file__).parent.parent` as the repo root (true only when the file lived in `scripts/`), and some import siblings that now also live here.

Replay and rebuild use the scripts remaining in `scripts/` plus `rebuild.py`. The v4.4/v4.5 patch chain is `scripts/replay_v44_baseline.py`.
