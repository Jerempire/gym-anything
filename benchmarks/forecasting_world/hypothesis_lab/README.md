# Hypothesis Lab

This folder defines the handoff contract between idea generation and live shadow execution.

It is intentionally small in the first slice.

The goal is to let external systems such as:

- `alpha-engine`
- `meta-optimizer`

submit structured hypothesis packets into `gym-anything` for replay evaluation before any candidate is activated in a live shadow loop.

The initial artifacts are:

- `hypothesis_packet.example.json`
- `replay_eval_result.example.json`

The intended control flow is:

1. `alpha-engine` or another generator emits a `hypothesis_packet`
2. `gym-anything` routes it to one or more replay environments
3. replay evaluation produces a `replay_eval_result`
4. `meta-optimizer` uses that result to decide:
   - `skip`
   - `send_to_lab`
   - `approve_for_shadow`
   - `reroute_for_revision`

This folder is a contract definition, not yet the full runtime implementation.
