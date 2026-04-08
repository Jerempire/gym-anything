# Session Handoff: Gym-Anything for Blender & TradingView

**Created**: 2026-04-08
**Status**: Ready for implementation session
**Repo**: `cmu-l3/gym-anything` → cloned to `Projects/build/gym-anything/`
**Paper**: arXiv:2604.06126

---

## What's Already Done

- [x] Cloned repo (72K files, 251 environments, includes ClaudeAgent)
- [x] Reviewed architecture: Core (runtime) + Benchmarks (CUA-World) + Agents
- [x] Confirmed `blender3d_env/` exists with 56 tasks
- [x] Confirmed NO TradingView environment exists (contribution opportunity)
- [x] Read verifier pattern (multi-signal scoring + VLM fallback)

---

## What Gym-Anything Is

A standardized Gymnasium-style API for testing AI agents on **real desktop software**:

```
Agent sees screenshots → sends mouse/keyboard actions → Environment runs in Docker → Verifier checks results
```

**Three independent pillars:**
- **Core** (`src/gym_anything/`) — runtime, environment lifecycle, action/observation contracts
- **Benchmarks** (`benchmarks/cua_world/`) — 251 real software environments, 10K+ tasks
- **Agents** (`agents/`) — Claude, Gemini, Qwen, Kimi reference implementations

**Key contract** (don't break):
- `contracts.py` — `SessionInfo`, `RunnerRuntimeInfo`
- `specs.py` — `EnvSpec`, `TaskSpec`, observation/action types
- Task folder shape: `task.json` + `setup_task.sh` + `verifier.py` + `export_result.sh`

---

## Part 1: Blender3D Environment (EXISTING — 56 tasks)

### How It Maps To Your Blender AI Artist

| Your Current Setup (Mar 15 session) | Gym-Anything Equivalent |
|---|---|
| Claude orchestrates Blender Python API | `ClaudeAgent` sends mouse/keyboard to Blender GUI |
| Gemini judges rendered output | `verifier.py` + VLM checks (built-in) |
| Self-improving loop via iteration | `gym-anything benchmark` with scoring + trajectory recording |
| Blender 5.2 installed locally | Docker container with Blender + Ubuntu GNOME + GPU passthrough |

### What To Do

```bash
# 1. Install gym-anything
cd Projects/build/gym-anything
uv venv --python 3.12
source .venv/bin/activate  # or: .venv/Scripts/activate on Windows
uv pip install -e .[all]

# 2. Check system readiness
gym-anything doctor

# 3. Run a Blender task interactively (watch via VNC)
gym-anything run blender3d_env --task add_sphere_to_scene -i --open-vnc

# 4. Benchmark Claude on all Blender tasks
gym-anything benchmark blender3d_env --agent ClaudeAgent --model claude-opus-4-6 --split test
```

### Existing Blender Tasks (56 total, examples):
- `add_sphere_to_scene` (easy) — add UV sphere at coordinates, save blend file
- `audio_reactive_visualizer` — build audio-reactive animation
- `boolean_wall_openings` — CSG boolean operations
- `asset_append_scene_assembly` — import and assemble assets
- `bouncing_ball_animation` — physics-based animation

### Integration Ideas
1. **Benchmark your Blender AI Artist**: Run Claude against all 56 tasks, measure pass rate
2. **Add your own tasks**: Your Mar 15 session built 4 models (Track-To constraints, camera framing, lighting). Each could become a Gym-Anything task with programmatic verifiers
3. **Self-improving agent**: Use benchmark results to identify failure modes, improve agent prompts
4. **Compare agents**: Run Gemini, Qwen, Claude side-by-side on Blender tasks

### System Requirements
- Docker with `sysbox-runc` runtime (for systemd in containers)
- GPU passthrough (`/dev/dri` device mount)
- 8 CPU, 16GB RAM per Blender environment instance
- VNC for interactive viewing (port 5961)

---

## Part 2: TradingView Environment (NEW — you'd build this)

### Why This Is Worth Building

You already have the infrastructure:
- `tv` CLI on CDP port 9223 (installed 2026-04-01)
- Pine Script dev loop: write → set → compile → read errors → fix
- Session Levels + VWAP indicator as proof of concept
- Chart-Advisor weekly ensemble capturing 11 indicators via CDP

A `tradingview_env/` would formalize all of this into a benchmarkable agent environment.

### Task Ideas for TradingView

**Easy tasks:**
- `add_indicator_to_chart` — Add RSI/MACD/Bollinger Bands to a chart
- `change_timeframe` — Switch from 1H to daily
- `draw_trendline` — Draw a trendline between two swing points
- `save_chart_layout` — Create and save a custom layout

**Medium tasks:**
- `create_pine_indicator` — Write a Pine Script indicator from description
- `set_alerts` — Configure price/indicator alerts
- `backtest_strategy` — Run a Pine strategy backtest, export results

**Hard tasks:**
- `multi_chart_layout` — Build a 4-panel layout with correlated instruments
- `replay_and_annotate` — Use bar replay to identify and annotate patterns
- `build_screener_filter` — Create a custom stock screener with multiple conditions

### How To Build It

Each environment needs:

```
benchmarks/cua_world/environments/tradingview_env/
├── env.json              # Environment spec (base image, resources, VNC config)
├── scripts/
│   ├── install_tradingview.sh   # Install TradingView Desktop
│   └── setup_tradingview.sh     # Launch, login, configure
├── tasks/
│   └── add_indicator_to_chart/
│       ├── task.json            # Task description, difficulty, timeout
│       ├── setup_task.sh        # Prepare initial chart state
│       ├── export_result.sh     # Extract chart state for verification
│       ├── verifier.py          # Check indicator was added correctly
│       └── vlm_checklist.json   # VLM visual verification prompts
```

**Key design decisions:**
- Base image: `ubuntu-gnome-systemd_highres` (same as Blender)
- TradingView Desktop v3.0.0 (not web — avoids auth/captcha complexity)
- CDP port 9223 for programmatic verification (leverage your `tv` CLI work)
- Verifier can use CDP to query chart state (indicators, timeframe, objects) rather than relying solely on VLM

### Contribution Path
This could be a PR to `cmu-l3/gym-anything` — TradingView is a major financial tool with no existing environment. Start with 3-5 easy tasks, submit PR, expand later.

---

## Part 3: Other Relevant Environments Already in CUA-World

Worth exploring — these 251 environments include software relevant to your other projects:

| Environment | Your Project Connection |
|---|---|
| `blender3d_env` (56 tasks) | Blender AI Artist (`creative-art/blender/`) |
| `anaconda_env` | Your conda-heavy workflow |
| `android_studio_env` | Mobile app testing |
| Various medical envs (`care2x_env`, `bahmni_env`) | PHI/hospital work |
| `autopsy_env` (forensics) | Intelligence projects |

---

## Recommended Session Order

1. **Install & doctor check** (~15 min)
   - Install gym-anything, run `gym-anything doctor`
   - Resolve any Docker/sysbox requirements

2. **Run one Blender task interactively** (~20 min)
   - `gym-anything run blender3d_env --task add_sphere_to_scene -i --open-vnc`
   - Watch the agent work via VNC, understand the feedback loop

3. **Benchmark Claude on Blender** (~1-2 hours, runs autonomously)
   - `gym-anything benchmark blender3d_env --agent ClaudeAgent --model claude-opus-4-6 --split test`
   - Analyze results: which tasks pass, which fail, what patterns emerge

4. **Scaffold TradingView environment** (~1 session)
   - Create `tradingview_env/` structure
   - Start with `add_indicator_to_chart` as first task
   - Leverage your existing `tv` CLI for the verifier

---

## Prerequisites to Check

- [ ] Docker Desktop installed and running
- [ ] `sysbox-runc` runtime available (or check if standard Docker works)
- [ ] GPU passthrough configured (`/dev/dri`) — needed for Blender
- [ ] Python 3.12 available (gym-anything requirement)
- [ ] `uv` package manager installed (`pip install uv` if not)

**Note**: On Windows, Docker Desktop with WSL2 backend should work. GPU passthrough requires WSL2 GPU support (NVIDIA drivers in WSL). The `sysbox-runc` runtime may need Linux — check `gym-anything doctor` output for Windows-specific guidance.
