# Code Review Summary

## Issues Found and Fixed

### 1. **Critical: Unbounded search when `depth <= 0` at root**
- **Problem:** `get_best_action_minimax`, `get_best_action_alpha_beta`, and `get_best_action_expectimax` call the search with `depth - 1`. When `depth == 0`, this becomes `-1`, so the recursive base case `depth == 0` is never hit and the tree is expanded until a terminal state (potentially very deep or infinite in theory).
- **Fix:** In all three `get_best_action_*` functions, if `depth <= 0` or there are no legal actions, we now return without recursing: choose the best action by one-step heuristic evaluation only. Also handle empty legal actions by returning `(None, -inf)`.

### 2. **Terminal states had no clear win/loss in the heuristic**
- **Problem:** Terminal states (defender caught intruder vs intruder breached zone) were evaluated with the same distance-based formula, so the search could not strongly prefer winning over losing.
- **Fix:** In `heuristic_evaluation`, at the start: if defender and intruder coincide → return `1e6`; if intruder is inside the restricted zone → return `-1e6`. Then continue with the usual Safety/Time/Risk formula for non-terminal states.

### 3. **Input validation and robustness**
- **Problem:** Malformed `restricted_zone` (e.g. not length 2) or `grid_bounds` (not length 4) could cause confusing failures later (unpack errors in `get_legal_actions` or center calculation).
- **Fix:** In `AirspaceState.__init__`: require `restricted_zone` to have exactly 2 points (raise `ValueError` otherwise); require `grid_bounds` to have exactly 4 values when provided. Store copies (tuples/lists) so callers cannot mutate internal state.

---

## Other Notes (no code change)

- **`generate_successor`** does not check that `action` is in `get_legal_actions`. The search code only ever passes legal actions, so this is fine. If you ever call it from elsewhere, pass only legal actions or add an assert.
- **Greedy intruder (test_run):** When two actions tie in distance to the zone, the first one in iteration order is chosen. Acceptable for testing.
- **Simulation outcome:** With the current setup (defender at (0,0), intruder closer to zone, grid 0–15), the defender often keeps moving UP and the intruder reaches the zone. That is a consequence of the heuristic and branching, not a bug; you can tune weights or try different starting positions.

---

## Files Modified

| File | Changes |
|------|--------|
| `minimax_search.py` | `get_best_action_minimax`: depth <= 0 and empty-actions handling |
| `alpha_beta_search.py` | `get_best_action_alpha_beta`: same |
| `expectimax_search.py` | `get_best_action_expectimax`: same |
| `heuristic_evaluation.py` | Terminal-state returns +1e6 / -1e6 |
| `AirspaceState.py` | Validation for `restricted_zone` length and `grid_bounds` length; store tuples/list |
