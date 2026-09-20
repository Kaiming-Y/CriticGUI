# Release notes

This repository is a clean publication copy of the original local GUICritic work. The original repository and its uncommitted research changes were left untouched.

## Retained

- Mouse/keyboard log parsing and heuristic merging.
- Action normalization and PyAutoGUI-code translation.
- The original three-level plan semantics and instruction-by-instruction collection design.

## Changes in this release

- Strict standalone plan parsing, scoped-ID checks and a provider-independent draft prompt.
- CLI parameters instead of fixed task IDs and absolute machine paths.
- An isolated OBS recording per atomic instruction, exact returned-video copying, explicit before/after screenshots and cleaned-up input listeners.
- A single key-press log per event, rather than the original duplicated key-down writes.
- Plan hashes, immutable completed steps and separate named variants.
- Manual review/perturbation annotation and reviewed-only JSONL/media export.
- Unknown log-line filtering and safe escaping of generated text literals.
- No historical credentials, local caches, model weights, task documents or collected sessions.

The publication recorder uses boundary screenshots plus video instead of the original asynchronous event-by-event screenshots. OBS and GUI recording need a live desktop smoke test on the target collection machine. Offline tests validate parsing/export logic, not live capture.

The original MLLM planner was coupled to the broader agent environment. This release provides its three-level drafting instructions as a provider-independent prompt; drafting is performed in the user's chosen MLLM tool. Agent exploration remains an external WorldGUI dependency.
