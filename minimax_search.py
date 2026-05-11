"""
Minimax search for the restricted airspace game.
Computes optimal strategies assuming both agents act rationally.

Value of state s (spec §5):
  V(s) = max_{a ∈ A(s)} V(T(s, a))   if s is MAX (defender)
  V(s) = min_{a ∈ A(s)} V(T(s, a))   if s is MIN (intruder)
Terminal states are evaluated using the utility function U(s).
"""

from heuristic_evaluation import heuristic_evaluation


def minimax_search(state, depth, maximizing_player):
    """
    Returns the minimax value of the state.
    maximizing_player: True for Defender (MAX), False for Intruder (MIN).
    """
    if depth == 0 or state.is_terminal():
        return heuristic_evaluation(state)

    if maximizing_player:  # Defender (MAX)
        v = float("-inf")
        for action in state.get_legal_actions(0):
            successor = state.generate_successor(0, action)
            v = max(v, minimax_search(successor, depth - 1, False))
        return v
    else:  # Intruder (MIN)
        v = float("inf")
        for action in state.get_legal_actions(1):
            successor = state.generate_successor(1, action)
            v = min(v, minimax_search(successor, depth - 1, True))
        return v


def get_best_action_minimax(state, depth):
    """
    Returns the best action for the Defender (MAX) at the root and its minimax value.
    If depth <= 0, returns best action by one-step heuristic (no recursion).
    """
    legal = state.get_legal_actions(0)
    if not legal:
        return None, float("-inf")
    if depth <= 0:
        best_action = legal[0]
        best_value = heuristic_evaluation(state.generate_successor(0, best_action))
        for action in legal[1:]:
            v = heuristic_evaluation(state.generate_successor(0, action))
            if v > best_value:
                best_value, best_action = v, action
        return best_action, best_value
    best_value = float("-inf")
    best_action = None
    for action in legal:
        successor = state.generate_successor(0, action)
        v = minimax_search(successor, depth - 1, maximizing_player=False)
        if v > best_value:
            best_value = v
            best_action = action
        elif v == best_value and best_action is not None:
            # Tie-break: prefer action that closes the smaller defender-intruder gap first
            # (so we chase in both dimensions instead of only one, e.g. RIGHT toward intruder)
            def min_gap(def_pos, int_pos):
                dx = abs(def_pos[0] - int_pos[0])
                dy = abs(def_pos[1] - int_pos[1])
                return min(dx, dy)
            if min_gap(successor.defender_pos, successor.intruder_pos) < min_gap(
                state.generate_successor(0, best_action).defender_pos, state.intruder_pos
            ):
                best_action = action
    return best_action, best_value
