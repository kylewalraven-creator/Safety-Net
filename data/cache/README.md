# data/cache/

Holds the **real captured hero reconciliation responses** — the offline demo
fallback. These are generated from a good live run, not hand-authored:

```bash
python -m safety_net.sweep --write-cache
```

This writes `case_a.json` and `case_b.json` here (one per hero case), each a
list of serialized `RecommendationOutcome` objects. The UI and
`--use-cache` read from these so the demo runs with wifi off.

This directory is intentionally **not** gitignored so the captured responses
can be committed as the demo's safety net. Do not commit fabricated results —
only real captured output belongs here.
