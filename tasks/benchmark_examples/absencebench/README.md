# AbsenceBench Croissant Tasks Example

This directory holds Croissant Tasks artifacts for **AbsenceBench** (Fu et al. 2025, [arXiv:2506.11440](https://arxiv.org/abs/2506.11440)) — a benchmark that asks LLMs to identify intentionally omitted information from a document, given access to both the original and the modified version.

This example is the first in `tasks/benchmark_examples/` that exercises **both** of Leo's runbooks end-to-end:

- `tasks/SKILL_pdf2ct.md`: paper PDF → Croissant Tasks `TaskProblem` (+ paper-reported `TaskSolution`s, summary, validation report).
- `tasks/SKILL_ct2code.md`: `TaskProblem` + a baseline spec → implementation code + populated `TaskSolution` + per-instance raw outputs + run manifest.

## Layout convention: snapshot per run

Unlike `mmlu/` and `xlsum/` (which are flat), this example treats each end-to-end execution of `pdf2ct → ct2code` as an immutable snapshot. Each run lives under `runs/<parent_commit>_<utc_timestamp>_<flavor>/`, contains everything needed to audit and reproduce that specific run, and is never modified after creation.

```
runs/<parent_commit>_<utc_timestamp>_<flavor>/
├── README.md             ← per-run TL;DR, results, layout, reproduction
├── pdf2ct/               ← outputs of SKILL_pdf2ct (TaskProblem + paper-reported solutions + meta)
├── ct2code/              ← outputs of SKILL_ct2code (impl + populated solution + raw outputs + manifest + prompts)
└── infra/                ← workaround / helper scripts scoped to this run
```

The directory naming convention `<parent_commit>_<utc_timestamp>_<flavor>` decomposes as:

- `<parent_commit>`: short SHA of the upstream commit the run was performed against. Tells anyone reading the dir name which versions of the SKILLs / shapes / framework underpin the snapshot.
- `<utc_timestamp>`: ISO 8601 UTC, `YYYY-MM-DDTHH-MMZ` (filesystem-safe — colon replaced with hyphen). The `Z` is the Zulu / UTC marker.
- `<flavor>`: free-form label describing the run kind. Currently used: `dryrun_n<N>` (small N-per-subset sanity run) and (planned) `fullrun_n<N>` (full validation split).

A new run never overwrites or modifies an existing run's files. Re-runs against an updated upstream / SKILL / paper should produce a sibling `runs/<new_parent_commit>_<new_ts>_<flavor>/`.

## Runs in this directory

| Run | Started | Parent commit | Flavor | Stage status | Headline |
|---|---|---|---|---|---|
| [`02b87497_2026-04-29T14-58Z_dryrun_n5`](runs/02b87497_2026-04-29T14-58Z_dryrun_n5/) | 2026-04-29 | `02b87497` (Leo: ct2code skill + updated pdf2ct skill) | `dryrun_n5` | pdf2ct: complete; ct2code: 5/subset dry run | overall F1 65.98 (claude-4-sonnet via Cursor subagent) |

## Quick navigation

- The most recent run's full report: [`runs/02b87497_2026-04-29T14-58Z_dryrun_n5/README.md`](runs/02b87497_2026-04-29T14-58Z_dryrun_n5/README.md).
- The TaskProblem (definition of the benchmark, latest snapshot): [`runs/02b87497_2026-04-29T14-58Z_dryrun_n5/pdf2ct/absencebench_problem.jsonld`](runs/02b87497_2026-04-29T14-58Z_dryrun_n5/pdf2ct/absencebench_problem.jsonld).
- The implementation script (latest): [`runs/02b87497_2026-04-29T14-58Z_dryrun_n5/ct2code/absencebench_implementation.py`](runs/02b87497_2026-04-29T14-58Z_dryrun_n5/ct2code/absencebench_implementation.py).

## A note on the snapshot convention vs. `mmlu/` and `xlsum/`

The flat layout used by `mmlu/` and `xlsum/` is fine for examples that won't be re-run as the framework evolves. AbsenceBench is the first example built end-to-end after both `pdf2ct` and `ct2code` were available, and we expect to iterate (more baselines, full evals, paper updates), so we adopt the snapshot layout. If Leo prefers, this can be flattened back to match the existing examples — every file maps cleanly to its flat-layout location.
