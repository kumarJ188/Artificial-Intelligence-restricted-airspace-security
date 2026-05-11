# Restricted Airspace Security — Adversarial Decision-Making (COMP-569)

An adversarial decision-making system for restricted airspace: a **defending agent** intercepts or deters an **intruding agent** (e.g., unauthorized drone) from reaching a protected region. The interaction is modeled as a two-player game and solved using **minimax**, **alpha–beta pruning**, and **expectimax** for uncertainty, with a shared utility function balancing security, time, and risk.

---

## 1. Project Overview

Autonomous systems in restricted airspace must decide under **adversaries**, **uncertainty**, and **limited time** (e.g., airport perimeter security, critical infrastructure, counter-UAS). This project implements:

- **Restricted region (target zone)** that the intruder must not reach  
- **Defending agent** that intercepts or delays the intruder  
- **Intruding agent** that tries to reach the zone with minimal cost/delay  
- **Environmental constraints** such as no-fly corridors  

The defender’s goal is to intercept or delay the intruder; the intruder seeks to reach the restricted zone.

---

## 2. Game-Theoretic Formulation

The problem is modeled as a **two-player turn-based game** (spec §4):

⟨**S**, **A**, **T**, **U**, **P**⟩

| Symbol | Meaning |
|--------|--------|
| **S** | Set of all possible states (positions, distances to zone, constraints) |
| **A** | Set of actions available to each agent |
| **T**(s, a) → s′ | Transition function |
| **U**(s) | Utility function (evaluates terminal/heuristic states) |
| **P**(s) | Agent whose turn it is (Defender = MAX, Intruder = MIN) |

Each state in **S** encodes defender position, intruder position, restricted zone, and no-fly zones.

---

## 3. Minimax Search (§5)

Minimax computes **optimal strategies** assuming both agents act rationally:

- **MAX (Defender):** \( V(s) = \max_{a \in A(s)} V(T(s, a)) \)
- **MIN (Intruder):** \( V(s) = \min_{a \in A(s)} V(T(s, a)) \)

Terminal states are evaluated with the utility function **U**(s).

---

## 4. Alpha–Beta Pruning (§6)

Alpha–beta improves **efficiency** by pruning branches that cannot affect the final decision:

- **α** = best value so far for MAX  
- **β** = best value so far for MIN  
- **Prune when** α ≥ β  

Deeper exploration is possible without sacrificing optimality.

---

## 5. Expectimax and Uncertainty (§7)

For **sensor noise and probabilistic outcomes**, expectimax adds **chance nodes**:

\[
V(s) = \sum_{s' \in S} P(s' \mid s, a) \cdot V(s')
\]

- **s′** = possible successor state  
- **P(s′ | s, a)** = transition probability  

This supports reasoning over **expected outcomes** instead of pure worst-case play.

---

## 6. Utility Function Design (§8)

The utility function (Defender perspective) has the form:

**U(s) = w₁ · Safety(s) − w₂ · Time(s) − w₃ · Risk(s)**

| Term | Meaning |
|------|--------|
| **Safety(s)** | Distance of intruder from restricted zone (maximize) |
| **Time(s)** | Penalty for long engagement (defender–intruder distance) |
| **Risk(s)** | Penalty for defender near no-fly zones |

Weights **w₁, w₂, w₃, w₄** in `heuristic_evaluation.py` can be tuned and justified for experiments. **w₄** is a pursuit bonus that rewards closing the smaller defender–intruder gap so the defender chases in both axes instead of only one (e.g. moving RIGHT toward the intruder, not only UP).

---

## 7. Project Structure

| File | Purpose |
|------|--------|
| `AirspaceState.py` | State **S**, actions **A**, transition **T**, terminal check, **P** (via agent_index). |
| `heuristic_evaluation.py` | Utility **U(s)** = w₁·Safety − w₂·Time − w₃·Risk. |
| `minimax_search.py` | Minimax value and best action for Defender. |
| `alpha_beta_search.py` | Alpha–beta value and best action (with pruning). |
| `expectimax_search.py` | Expectimax value and best action (chance nodes for intruder). |
| `test_run.py` | Example run: minimax, alpha–beta, expectimax. |

---

## 8. Requirements and Install

- **Python:** 3.8+  
- **Dependencies:** None (standard library only).

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .           # optional
```

---

## 9. Usage

Run from the project directory (or set `PYTHONPATH`):

```python
from AirspaceState import AirspaceState
from heuristic_evaluation import heuristic_evaluation
from minimax_search import minimax_search, get_best_action_minimax
from alpha_beta_search import alpha_beta_search, get_best_action_alpha_beta
from expectimax_search import expectimax_search, get_best_action_expectimax

# Build state: defender, intruder, restricted zone, no-fly zones
# Optional: grid_bounds=(x_min, x_max, y_min, y_max) to keep agents on a finite grid (e.g. (0, 20, 0, 20))
state = AirspaceState(
    defender_pos=(0, 0),
    intruder_pos=(6, 8),
    restricted_zone=[(10, 10), (12, 12)],
    no_fly_zones=[(5, 5)],
    # grid_bounds=(0, 20, 0, 20),  # uncomment to prevent runaway moves
)

# Values only
v_minimax = minimax_search(state, depth=3, maximizing_player=True)
v_ab     = alpha_beta_search(state, depth=3, alpha=float('-inf'), beta=float('inf'), maximizing_player=True)
v_ex     = expectimax_search(state, depth=3, agent_index=0)

# Best action for Defender (for decision-making)
action_minimax, val_minimax = get_best_action_minimax(state, depth=3)
action_ab,     val_ab      = get_best_action_alpha_beta(state, depth=3)
action_ex,     val_ex      = get_best_action_expectimax(state, depth=3)
```

Run the provided test:

```bash
python test_run.py
```

---

## 10. Why the intruder can still win (and what we changed)

In the default simulation the defender starts at (0, 0) and the intruder at (4, 6) with the zone at (8, 8)–(10, 10). The search used to pick **UP** every time because (1) legal actions are tried in order and (2) when several actions had the same value (e.g. all bad at limited depth), the first one (UP) was kept. So the defender never moved RIGHT and could not intercept. Two changes fix this:

1. **Tie-breaking** in `get_best_action_*`: when two actions have the same value, we prefer the one that reduces the **smaller** of the two gaps (|Δx|, |Δy|) between defender and intruder, so the defender closes both dimensions instead of only one.
2. **Pursuit bonus (w₄)** in the heuristic: we add a term that rewards having a small min(|Δx|, |Δy|), so the search prefers moving toward the intruder in both axes (e.g. RIGHT as well as UP).

The intruder can still win if it starts closer to the zone and reaches it before the defender can intercept; outcome depends on depth, weights, and starting positions.

---

## 11. Computational Considerations (§9)

- **Exponential growth** of the search tree with depth and branching factor.  
- **Limited real-time** decision windows.  
- **Trade-offs** between search depth and accuracy; alpha–beta reduces nodes explored without changing the optimal value.

---

*Course project — COMP-569 Intro to AI (Dr. Reza Abdolee).*
