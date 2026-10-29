# Wenxin / Baidu AI-card collector

This repository contains only the Wenxin collector that captures AI answer cards
from Baidu Search, its scheduling and quality helpers, and optional result sync.
It does not include the original project's dashboard, other model collectors,
browser profiles, credentials, or collected results.

## Setup

Use Python 3.11 or newer. From the repository root:

```bash
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements.txt
scrapling install
```

The collector uses Scrapling's persistent stealth browser. The first run may
download browser components. A visible browser can be requested for debugging
with `WENXIN_STEALTH_HEADLESS=0`.

## Run

```bash
python -m collectors.wenxin.wenxin_supervisor \
  --questions-file collectors/wenxin/product.txt \
  --rounds-per-question 15 \
  --question-mode interleaved \
  --tasks 1 \
  --restart-completed
```

Remove `--restart-completed` to run one finite batch. The supervisor supports
1–4 independent tasks. Results, logs, browser profiles, and resume state are
created under `runtime/remote_workers/` and are ignored by Git. The question
list is an example; replace `product.txt` or pass another path as needed.

For one direct collector run, see
`python -m collectors.wenxin.wenxin_loop --help`.

## Optional result sync

The collector always writes local JSONL records. To enable upload to a
compatible monitor receiver, create `runtime/remote_workers/wenxin_sync.json`
with `enabled`, `model`, `receiver_url`, and a receiver-issued `token`. This
configuration is deliberately not committed. Without it, sync stays disabled.
The included `transport/sync.py` is the original sender; the receiving server
is outside this repository.

## Checks

```bash
python -m unittest discover -s tests
```
