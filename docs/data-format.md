# Data format

A reviewed plan is a list of records with `id`, zero-based `step_id`, `high-level`, `low-level` and `atomic-level`. IDs concatenate scoped indices, e.g. `h0l1a0`. See `examples/plan.json`.

## Raw collection

```text
recordings/<task-id>/<variant>/
  session.json                 # plan hash, task, software, variant
  plan.json                    # exact plan used
  h0l0a0/
    sample.json                # hierarchy, UID, selected capture folder
    complete.json              # present only after capture/parsing succeeds
    annotation.json            # manual judgment, reason, perturbation, parent, reviewer
    <timestamp>/
      events.log
      actions.json
      before.png
      after.png
      video.mkv                # actual suffix follows OBS output
```

A variant is an attempt, not a label. An attempted negative can still succeed. Failed/incomplete captures remain in timestamp folders for inspection, but are not exported. A resumed step selects a new capture only after it completes.

## Reviewed export

```text
exports/reviewed/
  samples.jsonl
  media/<uid>/before.png
  media/<uid>/after.png
  media/<uid>/video.mkv
```

Each JSONL row includes:

- `uid`, `source: human_demonstration`, `meta` (including the plan hash).
- `instructions`: all three levels.
- `actions`: normalized interaction representations.
- `action_code`: PyAutoGUI code text, never executed by export.
- `media`: paths relative to the export directory.
- `review`: `label` (`success`/`failure`), `reason`, `perturbation`, `parent_uid`, `reviewer`.

The label answers whether the **atomic instruction** was achieved given its parent context. It is not necessarily whole-task success. Keep paired variants and neighboring steps from the same original task in the same evaluation split to avoid leakage. Review both successful and unsuccessful examples rather than assuming a demonstration is correct.
