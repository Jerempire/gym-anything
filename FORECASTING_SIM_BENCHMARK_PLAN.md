# Forecasting Simulation Benchmark Plan

## Goal

Extend Gym-Anything from a general computer-use benchmark into a reusable
benchmark suite for forecasting and decision-making under uncertainty.

The core abstraction is:

`scenario -> forecast or action -> hidden outcome -> verifier`

This keeps the framework focused on measurable predictive skill rather than
general agent behavior alone.

## Why This Fits Gym-Anything

Gym-Anything already gives us the pieces we need:

- environments with controlled resets
- tasks with setup hooks
- agents that operate through GUI actions
- post-task export hooks
- programmable verifiers

The leverage is in benchmark design, not in rebuilding the runtime.

## Design Principles

1. Prefer frozen or simulated scenarios over live internet tasks.
2. Separate forecasting quality from UI manipulation skill.
3. Score calibration, not just point accuracy.
4. Keep tasks narrow enough to verify automatically.
5. Use hidden labels and holdout outcomes wherever possible.
6. Treat live trading or real money execution as out of scope.

## Proposed Repo Layout

Add a new benchmark family without disturbing the existing runtime:

```text
benchmarks/
  forecasting_world/
    registry/
      __init__.py
      splits.py
      task_splits.py
    shared/
      scoring.py
      schemas.py
      outcome_store.py
      verifier_utils.py
      scenario_loader.py
    environments/
      sports_env/
        env.json
        scripts/
        tasks/
      markets_env/
        env.json
        scripts/
        tasks/
      psychology_env/
        env.json
        scripts/
        tasks/
      browser_research_env/
        env.json
        scripts/
        tasks/
    datasets/
      sports/
      markets/
      psychology/
      synthetic/
```

## Recommended Environment Strategy

Do not force everything into one environment.

### 1. `sports_env`

Use a browser or lightweight dashboard environment for:

- matchup pages
- team statistics
- injury reports
- odds boards
- event timelines

Primary task types:

- binary win probability
- spread or total direction
- exact score bucket
- player prop direction
- live update after new information

### 2. `markets_env`

Use the existing finance patterns already present in the repo.

Base options:

- extend `ninja_trader_env` for replay-based futures tasks
- extend `chrome_env_all` for prediction-market and research workflows

Primary task types:

- next-session direction probability
- volatility regime classification
- event-driven scenario forecast
- trade plan with entry, stop, and target
- decision to act or abstain

### 3. `psychology_env`

This should be synthetic or anonymized. Avoid sensitive real-world subjects.

Primary task types:

- infer likely behavioral response from a case file
- predict survey outcome bucket
- predict decision under framing change
- identify confidence and uncertainty range
- update prediction after a new note or transcript excerpt

### 4. `browser_research_env`

Use this for general event forecasting that depends on collecting evidence from
documents, dashboards, or structured web pages.

Primary task types:

- collect evidence from multiple sources
- summarize relevant signals
- assign probability to one or more outcomes
- revise forecast after contradictory evidence

## Shared Task Contract

Each forecasting task should follow the existing Gym-Anything task structure:

```text
task folder/
  task.json
  setup_task.sh or .ps1
  export_result.sh or .ps1
  verifier.py
  scenario.json
  hidden_outcome.json
```

### `task.json`

Should define:

- visible task instruction
- time limit
- step limit
- task hooks
- success mode `program`
- metadata for scenario id, forecast schema, and scoring config

### `setup_task`

Should:

- load the scenario
- prepare the UI or files
- seed any visible evidence
- record task start metadata
- keep hidden outcomes unavailable to the agent

### `export_result`

Should extract:

- forecast file
- action taken or abstained
- confidence
- rationale path if required
- artifacts produced during the run

### `verifier.py`

Should:

- load the hidden outcome
- parse the submitted forecast
- score the forecast using shared scoring functions
- apply anti-gaming checks
- return `passed`, `score`, and `feedback`

## Shared Forecast Output Schema

Use one normalized output schema across domains.

```json
{
  "scenario_id": "sports.nba.2026-001",
  "task_type": "binary_probability",
  "forecast": {
    "target": "home_team_win",
    "probability": 0.63
  },
  "confidence": 0.74,
  "decision": "bet",
  "stake_fraction": 0.01,
  "notes": "Short rationale"
}
```

For multiclass or range tasks:

- use `class_probabilities`
- use `distribution`
- use `interval`

Keep the schema machine-readable and strict.

## Shared Scoring Library

Create `benchmarks/forecasting_world/shared/scoring.py` with domain-agnostic
metrics.

### Core metrics

- Binary events: Brier score, log loss, calibration bucket summary
- Multiclass events: cross-entropy, top-k accuracy
- Continuous outcomes: MAE, RMSE, interval coverage
- Ranked outcomes: NDCG or rank correlation

### Decision metrics

- expected value
- regret
- abstain quality
- risk-adjusted utility
- max drawdown on batched evaluation

### Batch metrics

- average score
- calibration error
- sharpness
- decision yield
- score by scenario family and difficulty

## Pass/Fail Philosophy

Do not make pass/fail depend on "guessed the winner."

A good forecaster can make a high-quality 62 percent prediction and still lose
the event. The verifier should reward calibrated probabilistic forecasts.

Suggested scoring pattern:

- 70 percent from forecast quality
- 20 percent from schema correctness and task completion
- 10 percent from evidence-use or process checks when justified

## Anti-Gaming Rules

Every verifier should check for:

- invalid probability ranges
- probabilities that do not sum correctly
- missing required fields
- copied hidden answers
- stale pre-existing output files
- empty or generic rationale when rationale is required
- wrong scenario id

For simulated markets or sports tasks, also reject:

- impossible timestamps
- references to hidden labels
- files created before task start

## Four Initial Benchmark Tracks

### Track A: Sports Forecasting

First 10 tasks:

1. NBA moneyline probability from frozen pregame dashboard
2. NFL total-over-under direction from stats pack
3. MLB starter duel forecast after lineup announcement
4. Soccer draw probability from match dossier
5. Tennis match winner after surface and fatigue update
6. Live basketball win probability after halftime
7. Player prop direction after injury news
8. Rank three most likely score buckets
9. Revise forecast after unexpected scratch
10. Abstain when evidence is contradictory

### Track B: Markets and Futures Forecasting

First 10 tasks:

1. ES next-session up/down probability from replay setup
2. NQ volatility regime classification
3. CL breakout probability after inventory release
4. Treasury futures directional forecast after macro data
5. Build a trade plan and export risk-reward parameters
6. Decide whether there is enough edge to trade
7. Revise forecast after correlated asset move
8. Compare two setups and rank higher expected value
9. Predict whether target or stop is hit first in replay
10. Detect regime shift and abstain from trading

### Track C: Event Market / Polymarket-Style Forecasting

First 10 tasks:

1. Extract current market probability and liquidity
2. Produce an independent probability estimate from frozen evidence
3. Compare market price to agent estimate and classify edge
4. Stage a buy or no-trade decision without submission
5. Detect inconsistency across related contracts
6. Revise probability after new article or filing
7. Rank correlated markets by mispricing
8. Produce a calibrated probability interval
9. Detect low-quality evidence and abstain
10. Explain forecast drift between two timestamps

### Track D: Psychology / Human Behavior Forecasting

First 10 tasks:

1. Predict response option from synthetic survey profile
2. Predict compliance likelihood after message framing
3. Predict attrition risk from anonymized case notes
4. Predict choice under gain vs loss framing
5. Predict trust score bucket after dialogue history
6. Revise prediction after contradictory follow-up
7. Rank likely behaviors from a case vignette
8. Estimate uncertainty interval, not just class
9. Detect insufficient evidence and abstain
10. Compare two interventions by predicted effect

## Best First Build Order

Build in this order:

1. Shared scoring and schema layer
2. `markets_env` replay tasks using existing NinjaTrader patterns
3. `sports_env` with frozen browser dashboards
4. `browser_research_env` for event-market tasks
5. `psychology_env` after the synthetic dataset policy is clear

This sequence gives the fastest path to measurable results.

## Recommended Reuse From Current Repo

Reuse these patterns rather than inventing new ones:

- existing `task.json` contract
- Windows task patterns from `ninja_trader_env`
- browser task patterns from `chrome_env_all` and `firefox_env`
- export plus verifier design from current benchmark tasks

The current repo already shows both sides:

- GUI finance workflows in NinjaTrader, JStock, and Portfolio Performance
- browser workflows with CDP-backed verification in Chrome tasks

## Suggested First Milestone

Target a private v0 with 12 tasks:

- 4 futures replay tasks
- 4 sports pregame tasks
- 4 event-market probability tasks

Deliverables:

- shared forecast schema
- shared scoring module
- one new benchmark family registry
- one batch evaluation report with calibration metrics

## Suggested Second Milestone

Target v1 with 40 to 60 tasks:

- 20 markets
- 15 sports
- 10 event-market
- 5 psychology

Add:

- difficulty splits
- calibration plots
- domain-level report cards
- abstention-aware evaluation

## Risks

### 1. Live data fragility

If tasks depend on live sites, verifiers will rot quickly.

Mitigation:

- freeze pages
- mirror structured datasets locally
- use replay files and snapshots

### 2. Overfitting to UI instead of forecasting

An agent can learn click paths without real predictive skill.

Mitigation:

- vary scenario content
- keep outcomes hidden
- emphasize scoring on outputs, not only UI actions

### 3. Weak verifier design

If verifiers mostly check file existence, the benchmark is shallow.

Mitigation:

- centralize scoring logic
- require normalized forecast outputs
- add anti-gaming checks

### 4. Psychology benchmark misuse

This domain can drift into sensitive inference quickly.

Mitigation:

- use synthetic cases
- avoid protected-class targeting
- keep tasks framed as abstract behavior prediction

## Concrete Next Step

Implement `forecasting_world/shared/` first, with:

- `schemas.py`
- `scoring.py`
- `verifier_utils.py`

Then add the first environment-specific task pack:

- `markets_env/tasks/es_next_session_probability`
- `markets_env/tasks/nq_volatility_regime`
- `markets_env/tasks/trade_or_abstain`

That will prove the scoring model and task contract before scaling into sports
and psychology.
