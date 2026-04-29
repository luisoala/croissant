# AbsenceBench Croissant Tasks Example

Croissant Tasks artifacts for **AbsenceBench** (Fu et al. 2025, [arXiv:2506.11440](https://arxiv.org/abs/2506.11440)) — a benchmark that asks LLMs to identify intentionally omitted information from a document, given access to both the original and the modified version.

This example is the first in `tasks/benchmark_examples/` that exercises **both** of Leo's runbooks end-to-end:

```
                    ┌── pdf2ct ──┐                    ┌── ct2code ──┐
                    ↓             ↓                    ↓             ↓
[paper PDF]  ──────►  TaskProblem JSON-LD     ───────► implementation.py
+ summary.md         + Paper-reported               + populated TaskSolution
+ validation_report  TaskSolutions                  + raw_outputs (per-instance preds)
                                                    + run manifest
```

The two stages produce **different kinds of TaskSolution**:
- **pdf2ct's TaskSolutions** carry the values *the paper reports* (extracted from Table 3); they document the literature.
- **ct2code's TaskSolution** carries values *we measured* by running the generated implementation; it documents our run.

## Files

### pdf2ct stage (paper → CT)

| File | Purpose |
|---|---|
| `absencebench_problem.jsonld` | The `croissant:TaskProblem` for AbsenceBench, with three `subTask`s (poetry, numerical, github_prs), an `OutputSpec` describing the predicted-omitted-elements schema (a repeated string field), and an `EvaluationSpec` declaring `F1-Score` and `Exact Match` as expected metrics. |
| `absencebench_solution_claude-3-7-sonnet.jsonld` | Paper-reported `TaskSolution` for `claude-3-7-sonnet-latest` without thinking mode. Values from Fu et al. 2025 Table 3 (poetry 73.5, numerical 91.4, github_prs 35.7, avg 66.9). |
| `absencebench_solution_claude-3-7-sonnet-thinking.jsonld` | Same model with inference-time compute enabled. Values from Table 3 (poetry 72.7, numerical 96.0, github_prs 40.0, avg 69.6). |
| `summary.md` | Executive summary per pdf2ct SKILL Step 8: extraction confidence, inferred fields, skipped fields, paper Table 3 selection rationale. |
| `validation_report.json` | Structured validation report per pdf2ct SKILL Step 9. Honest about the upstream SHACL bug. |

### ct2code stage (CT + baseline → code + populated solution + outputs)

| File | Purpose |
|---|---|
| `absencebench_implementation.py` | Generated Python baseline. Loads the HF dataset, builds the paper's exact default prompt templates (Appendix A), calls the Anthropic Messages API, parses responses, computes micro-F1 and per-instance exact-match, and updates the populated TaskSolution. |
| `absencebench_claude-4-sonnet_solution.jsonld` | Populated `TaskSolution` from running the implementation against `claude-4-sonnet` on a 5-instance-per-subset dry-run via Cursor subagents. The `instances_per_subset=5` hyperparameter and per-result descriptions make the dry-run nature explicit. |
| `raw_outputs/claude-4-sonnet/outputs_<domain>.jsonl` | Per-instance records (`id`, `domain`, `gold`, `pred`, `raw_response`, `metrics`, `model`, `ts`). One JSONL per subtask. |
| `raw_outputs/claude-4-sonnet/manifest_<date>_<flavor>.json` | Run metadata: model, hyperparameters, runner type, dataset version, structural-check status, summary metrics, paper-vs-this-run comparison table, agent_transcript path. Per ct2code SKILL §3.5. |

### Infra / docs

| File | Purpose |
|---|---|
| `README.md` | This file. |
| `_structural_check.py` | rdflib-only structural validator used as a workaround for the broken upstream SHACL validator. Delete when upstream shapes are fixed. |
| `.gitignore` | Excludes scratch (`_prompts/`, `_responses/`, `_dryrun_prompts.json`, `__pycache__/`). |

## Reproducing the ct2code run

### Path 1 — Direct Anthropic API run (recommended for real evaluations)

```bash
cd tasks/benchmark_examples/absencebench
export ANTHROPIC_API_KEY=...

# 5 per subset (matches the committed dry-run scope):
python absencebench_implementation.py --dry-run

# Full evaluation across all 3,278 instances (expensive):
python absencebench_implementation.py --max-per-subset 0

# Different Sonnet variant:
python absencebench_implementation.py --dry-run --model claude-sonnet-4-5
```

### Path 2 — Via Cursor subagents (the path used to produce the committed dry-run)

This is the route used to populate `absencebench_claude-4-sonnet_solution.jsonld`. It avoids the need for a local Anthropic API key by using Cursor's subagent infrastructure.

1. Build per-instance prompt files (5 per subset = 15 files) under `_prompts/<domain>_<id>.txt`. Each file embeds the paper Appendix A default template (system + user prompts) inside a roleplay preamble that tells the subagent to respond as the model with no commentary.
2. Launch one Cursor subagent per instance with `subagent_type=generalPurpose`, `model=claude-4-sonnet`. Each subagent reads its prompt file and writes its literal model response to `_responses/<domain>_<id>.txt`.
3. Run an ingestion step that reads each response, parses it, computes per-instance metrics, appends to `raw_outputs/claude-4-sonnet/outputs_<domain>.jsonl`, and rewrites the populated TaskSolution. (The orchestration logic for steps 1-3 lived in a one-off scaffold `_dryrun_ingest.py` that was used during the original run; it is not committed because the source of truth for normal runs is `absencebench_implementation.py`. The README describes the path; reconstructing the scaffold is mechanical.)

## Metrics

Per Fu et al. 2025 §3.1 (Evaluation Metric):

- **Exact Match** is element-level: for each gold element, check whether it is present in the model's response. Used as the building block for F1.
- **Micro F1-score** is the primary metric: aggregate TP/FP/FN across all instances, then compute precision, recall, and F1.

In the implementation:

- Predictions are obtained by splitting the model response on `\n` and stripping whitespace from each line.
- TP per instance is computed as a multiset intersection of `pred` and `gold` (so duplicate gold entries can each be matched at most once).
- The `Exact Match` reported in solution.jsonld is per-instance (1 iff predicted-set equals gold-set), averaged across instances.

The full metric chain is reproducible from the committed artifacts alone: `outputs_<domain>.jsonl` has every instance's `gold` + `pred` + `raw_response` + per-instance `metrics`, and `absencebench_implementation.py` defines the algorithm. An auditor can re-run `aggregate()` on the JSONL data and verify the values in `absencebench_claude-4-sonnet_solution.jsonld`.

## Validator note (read this before running tasks/validator.py)

The upstream SHACL validator in `tasks/validator.py` currently fails on every input — including `tasks/testdata/valid_problem.jsonld` — across all `pyshacl` versions tested (0.22 – 0.31). The root cause is in `tasks/croissant-tasks-shapes.ttl`: `TaskProblemShape`'s "must have at least one Spec" property uses an outer `sh:property` whose body is `sh:or` of alternative paths, but the outer property shape itself has no `sh:path`. Strict pyshacl raises:

```
'<NodeShape n...>' exists but is not a well-formed SHACL PropertyShape.
```

Until that's fixed at the shape level, this directory ships `_structural_check.py`, which uses `rdflib` alone to verify the JSON-LD parses, the expected types are present, required references exist (e.g., `schema:isBasedOn` on solutions), no Specs leak into solutions, and EvaluationTask/Result wiring is sane.

```bash
python _structural_check.py absencebench_problem.jsonld
python _structural_check.py absencebench_claude-4-sonnet_solution.jsonld
python _structural_check.py absencebench_solution_claude-3-7-sonnet.jsonld
python _structural_check.py absencebench_solution_claude-3-7-sonnet-thinking.jsonld
```

When the upstream shapes file is repaired, switch back to `python ../../validator.py <file>` and delete `_structural_check.py`.

## Headline numbers at a glance

| Source | poetry | numerical | github_prs | overall |
|---|---:|---:|---:|---:|
| Paper Table 3, claude-3-7-sonnet, no thinking | 73.5 | 91.4 | 35.7 | 66.9 |
| Paper Table 3, claude-3-7-sonnet, thinking | 72.7 | 96.0 | 40.0 | 69.6 |
| This dry-run (claude-4-sonnet, n=5/subset) | 85.4 | 100.0 | 9.8 | 66.0 |

The github_prs collapse (-26 vs paper) is heavily n=5-driven: the model emits diff context lines (empty `+` markers, brace-only lines) that aren't in the gold, which tanks precision (5%). Don't read into the comparison — the dry-run is a pipeline check, not a benchmark result.
