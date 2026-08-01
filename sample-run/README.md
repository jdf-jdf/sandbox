# sample-run/ — what one pass actually produced

A frozen copy of the machine's own output, committed so you can read what it
writes and what it stops **without running anything**, and without needing an
API key.

Nothing reads this directory. It is evidence, not input.

| | |
|---|---|
| `out/` | the drafts that passed the gate, as they would arrive |
| `quarantine/` | drafts the gate refused, kept so you can judge whether it was right |
| `logs/rejects.log` | every block, with the rule and the matched phrase |
| `logs/attribution.jsonl` | the send ledger: one line per send, `live` distinguishing real from dry |
| `state.json` | run history, the rejection-rate trend, and the learned constraints |
| `REVIEW_QUEUE.md` | the work order the last run wrote for a human |

## Why this isn't just left in place

The live `out/`, `quarantine/`, `logs/` and `state.json` are **not** committed,
because `state.json` carries the run counter and the cumulative rejection-rate
trend. Shipping it meant a fresh clone's first run was labelled "run 4" and its
trend table interleaved someone else's history with its own — which quietly
undermines the one number the machine exists to move.

So a clone starts empty and its first run is run 1. This directory keeps the
audit trail readable anyway.

To regenerate your own:

```bash
python run.py                 # dry: writes out/, sends nothing
python tools/gate_demo.py     # prove the gate, no API key needed
./reset.sh                    # wipe it all and start again at run 1
```
