# Hypothesis Lab Handoff

This document is for the next session.

It describes:

- what already exists
- what does not exist yet
- what should be built next
- what should stay separate across `alpha-engine`, `gym-anything`, and `meta-optimizer`

The goal is to turn `Hypothesis Lab` from a design and packet contract into a runnable offline proving-ground layer.

## One-Sentence Summary

`alpha-engine` should discover hypotheses, `gym-anything` should prove or falsify them on replay data, and `meta-optimizer` should only govern which hypotheses are allowed to enter live shadow loops.

## Current Architecture

The intended stack is:

```text
alpha-engine / Hypothesis Explorer
  -> Hypothesis Lab (gym-anything)
  -> meta-optimizer candidate registry
  -> futures-flow / polymarket-edge / forecast-hub shadow loops
```

## What Already Exists

### In `gym-anything`

Forecasting and replay infrastructure already exists under:

```text
benchmarks/forecasting_world/
```

That includes:

- shared forecast schemas
- scoring helpers
- verifier helpers
- batch reporting
- train/test splits
- imported replay environments from local read-only finance projects

Current replay environments already available:

- `forecast_hub_env`
- `polymarket_edge_env`
- `futures_flow_env`
- `futures_walk_forward_env`
- `browser_research_env`
- `markets_env`

Relevant docs and contract files already created:

- [docs/content/docs/benchmarks/hypothesis-lab.mdx](C:/Users/jmj2z/Projects/build/gym-anything/docs/content/docs/benchmarks/hypothesis-lab.mdx)
- [benchmarks/forecasting_world/hypothesis_lab/README.md](C:/Users/jmj2z/Projects/build/gym-anything/benchmarks/forecasting_world/hypothesis_lab/README.md)
- [benchmarks/forecasting_world/hypothesis_lab/hypothesis_packet.example.json](C:/Users/jmj2z/Projects/build/gym-anything/benchmarks/forecasting_world/hypothesis_lab/hypothesis_packet.example.json)
- [benchmarks/forecasting_world/hypothesis_lab/replay_eval_result.example.json](C:/Users/jmj2z/Projects/build/gym-anything/benchmarks/forecasting_world/hypothesis_lab/replay_eval_result.example.json)

### In `meta-optimizer`

The live candidate loop already exists in:

- [run_loop.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/run_loop.py)
- [hypothesis_bridge.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/hypothesis_bridge.py)
- [candidate_runner.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/candidate_runner.py)
- [shadow_evaluator.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/shadow_evaluator.py)
- [promotion_gate.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/promotion_gate.py)

What `meta-optimizer` already does well:

- register candidate
- activate candidate
- write `active_candidate.json` into downstream systems
- evaluate shadow performance against baseline
- reject or promote after enough realized data

### In `alpha-engine`

Hypothesis generation already exists in:

- [hypothesis_engine.py](C:/Users/jmj2z/Projects/finance/alpha-engine/engine/hypothesis_engine.py)

Current modes:

- feature cross / informed generation
- error-pattern mining
- structured sweep

## What Does Not Exist Yet

This is the critical part.

The `Hypothesis Lab` execution path is not built yet.

Specifically, the following do not yet exist:

### 1. A runnable lab router

Missing:

```text
benchmarks/forecasting_world/hypothesis_lab/router.py
```

Needed behavior:

- read a `hypothesis_packet`
- determine which replay environments should evaluate it
- dispatch evaluation
- aggregate results into one `replay_eval_result`

### 2. Real evaluators for hypothesis packets

Missing:

```text
benchmarks/forecasting_world/hypothesis_lab/evaluators/
  forecast_eval.py
  futures_eval.py
  polymarket_eval.py
```

Needed behavior:

- map hypothesis claims to concrete replay tasks or task families
- score against hidden outcomes and source priors
- report pass/fail and failure modes

### 3. A command or API entrypoint

There is no current CLI command like:

```bash
gym-anything hypothesis-lab run packet.json
```

Needed behavior:

- run the packet through the lab
- write a structured result JSON

### 4. A bridge from `alpha-engine` output into the packet format

Current state:

- hypotheses exist in Alpha Engine format
- `hypothesis_packet.example.json` exists in `gym-anything`

Missing:

- actual adapter code that converts real Alpha Engine hypotheses into packet format

### 5. A pre-shadow gate in `meta-optimizer`

Current `meta-optimizer` flow:

- hypothesis accepted
- bridge to candidate
- activate for shadow

Missing:

- a required pre-shadow lab check

Desired future flow:

```text
hypothesis accepted
  -> Hypothesis Lab replay evaluation
  -> only if lab result is acceptable:
       bridge to candidate
       activate for shadow
```

### 6. Any falsification-specific runtime logic

The design mentions falsification, but no implementation exists for:

- adversarial replay passes
- “break this hypothesis” prompts
- failure-cluster analysis
- regime-specific invalidation testing

### 7. Any novelty scoring implementation

The result contract mentions novelty and robustness conceptually, but there is no code yet for:

- duplicate-family detection inside the lab
- similarity against rejection history
- similarity against prior replay-evaluated hypotheses

### 8. Any persistent storage for lab runs

Right now there is no dedicated storage for:

- submitted hypothesis packets
- replay lab run history
- environment-level lab results
- lab-level failure modes

This could be a JSONL or SQLite layer later, but nothing is implemented yet.

## What Should Stay Separate

Do not collapse these responsibilities into one project.

### `alpha-engine`

Should own:

- idea generation
- signal exploration
- hypothesis proposal

Should not own:

- full replay proving ground
- live candidate governance

### `gym-anything`

Should own:

- offline proving ground
- replay evaluation
- hidden-outcome scoring
- cross-domain falsification

Should not own:

- live shadow execution
- promotion decisions

### `meta-optimizer`

Should own:

- candidate registry
- shadow activation
- live baseline comparison
- promotion or rejection

Should not own:

- the full replay experimentation system
- exploratory hypothesis generation

## Best Next Build

The best next build is a narrow end-to-end slice, not the full system.

### Recommended first runnable slice

Implement only:

- packet ingestion
- router
- one forecast evaluator
- one futures evaluator
- JSON result output

Use only:

- `forecast_hub_env`
- `futures_flow_env`

Do not start with Polymarket first.

That is enough to prove the architecture without too much branching complexity.

## Exact Files To Add Next

Inside `gym-anything`:

```text
benchmarks/forecasting_world/hypothesis_lab/router.py
benchmarks/forecasting_world/hypothesis_lab/models.py
benchmarks/forecasting_world/hypothesis_lab/evaluators/__init__.py
benchmarks/forecasting_world/hypothesis_lab/evaluators/forecast_eval.py
benchmarks/forecasting_world/hypothesis_lab/evaluators/futures_eval.py
benchmarks/forecasting_world/hypothesis_lab/result_writer.py
```

Optional but likely useful:

```text
benchmarks/forecasting_world/hypothesis_lab/cli.py
tests/test_hypothesis_lab_router.py
tests/test_hypothesis_lab_forecast_eval.py
tests/test_hypothesis_lab_futures_eval.py
```

Inside `meta-optimizer` later:

```text
lab_bridge.py
```

Or small changes in:

- [run_loop.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/run_loop.py)
- [hypothesis_bridge.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/hypothesis_bridge.py)

## First Functional Requirements

The first version should be boring and strict.

### Input

Accept a single `hypothesis_packet.json`.

### Routing

Simple rules only:

- if packet domains include `forecast` -> run `forecast_hub_env` evaluator
- if packet domains include `price_action` or `futures` -> run `futures_flow_env` evaluator
- if both, run both and aggregate

### Output

Emit one `replay_eval_result.json` containing:

- top-level recommendation
- environment result list
- baseline comparisons
- failure notes
- next action recommendation

### Recommendation values

Allow only:

- `approve_for_shadow`
- `reroute_for_revision`
- `skip`

Do not add more states in the first slice.

## First Scoring Philosophy

Keep the first rules explicit.

### Forecast evaluator

Pass if:

- sample size meets minimum
- candidate beats baseline Brier
- question win rate >= 0.5

Fail otherwise.

### Futures evaluator

Pass if:

- minimum replay sample met
- candidate beats baseline on average PnL or Sharpe
- no obvious regime concentration failure in the first pass

Fail otherwise.

Do not try to solve full robustness science in v1.

## What Not To Build In The Next Session

Avoid these in the first implementation:

- full novelty scoring engine
- full rejection-history similarity engine inside the lab
- Polymarket integration
- heavy UI
- persistent lab database
- automatic modifications to `meta-optimizer`
- LLM-heavy formalization or falsification prompts

Those can come after the first runnable path is working.

## Acceptance Criteria For Next Session

The next session should be considered successful if all of these are true:

1. A real `hypothesis_packet.json` can be passed into a lab runner.
2. The router selects one or two evaluators based on domains.
3. `forecast_hub_env` evaluation returns a structured result.
4. `futures_flow_env` evaluation returns a structured result.
5. The system writes a valid `replay_eval_result.json`.
6. There are tests covering:
   - packet parsing
   - routing behavior
   - forecast evaluator
   - futures evaluator
7. No changes are required yet in live shadow code paths.

## Practical Build Order

Use this exact order:

1. `models.py`
   Create dataclasses or typed dicts for packet/result shape.

2. `router.py`
   Make domain-to-evaluator routing deterministic and simple.

3. `forecast_eval.py`
   Use `forecast_hub_env` first because the scoring logic is already very clear.

4. `futures_eval.py`
   Use `futures_flow_env` second.

5. `result_writer.py`
   Serialize one clean output packet.

6. tests
   Verify packet parse, route selection, and output structure.

7. optional CLI wrapper
   Only after the internal path works.

## Important Design Reminder

The purpose of `Hypothesis Lab` is not to replace `meta-optimizer`.

It exists to filter and falsify higher-risk or more novel ideas before they consume shadow capacity.

The clean architecture remains:

```text
alpha-engine discovers
gym-anything proves or falsifies
meta-optimizer governs shadow and promotion
```

## Reference Files

Use these as the current source of truth:

- [docs/content/docs/benchmarks/hypothesis-lab.mdx](C:/Users/jmj2z/Projects/build/gym-anything/docs/content/docs/benchmarks/hypothesis-lab.mdx)
- [benchmarks/forecasting_world/hypothesis_lab/README.md](C:/Users/jmj2z/Projects/build/gym-anything/benchmarks/forecasting_world/hypothesis_lab/README.md)
- [benchmarks/forecasting_world/hypothesis_lab/hypothesis_packet.example.json](C:/Users/jmj2z/Projects/build/gym-anything/benchmarks/forecasting_world/hypothesis_lab/hypothesis_packet.example.json)
- [benchmarks/forecasting_world/hypothesis_lab/replay_eval_result.example.json](C:/Users/jmj2z/Projects/build/gym-anything/benchmarks/forecasting_world/hypothesis_lab/replay_eval_result.example.json)
- [run_loop.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/run_loop.py)
- [hypothesis_bridge.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/hypothesis_bridge.py)
- [shadow_evaluator.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/shadow_evaluator.py)
- [promotion_gate.py](C:/Users/jmj2z/Projects/intelligence/meta-optimizer/promotion_gate.py)

## Final Note For The Next Session

Do not redesign the whole system again.

The design decision is already made:

- keep `Hypothesis Lab` separate
- make it a proving ground
- start with forecast and futures only
- connect `meta-optimizer` later, after the lab path is real

The next session should build the first runnable slice, not reopen architecture debates.
