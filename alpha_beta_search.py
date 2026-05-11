"""
Alpha–beta pruning for the restricted airspace game (spec §6).
Improves on minimax by pruning branches when α ≥ β.
"""

from heuristic_evaluation import heuristic_evaluation


def alpha_beta_search(state, depth, alpha, beta, maximizing_player):
    """
    Returns the minimax value of the state using alpha–beta pruning.
    Pruning occurs when beta <= alpha.
    """
    if depth == 0 or state.is_terminal():
        return heuristic_evaluation(state)

    if maximizing_player:  # Defender (MAX)
        v = float("-inf")
        for action in state.get_legal_actions(0):
            v = max(
                v,
                alpha_beta_search(
                    state.generate_successor(0, action),
                    depth - 1,
                    alpha,
                    beta,
                    False,
                ),
            )
            alpha = max(alpha, v)
            if beta <= alpha:
                break
        return v
    else:  # Intruder (MIN)
        v = float("inf")
        for action in state.get_legal_actions(1):
            v = min(
                v,
                alpha_beta_search(
                    state.generate_successor(1, action),
                    depth - 1,
                    alpha,
                    beta,
                    True,
                ),
            )
            beta = min(beta, v)
            if beta <= alpha:
                break
        return v


def get_best_action_alpha_beta(state, depth):
    """
    Returns the best action for the Defender at the root and its value (with pruning).
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
    alpha, beta = float("-inf"), float("inf")
    for action in legal:
        successor = state.generate_successor(0, action)
        v = alpha_beta_search(successor, depth - 1, alpha, beta, maximizing_player=False)
        if v > best_value:
            best_value = v
            best_action = action
        elif v == best_value and best_action is not None:
            def min_gap(def_pos, int_pos):
                dx, dy = abs(def_pos[0] - int_pos[0]), abs(def_pos[1] - int_pos[1])
                return min(dx, dy)
            if min_gap(successor.defender_pos, successor.intruder_pos) < min_gap(
                state.generate_successor(0, best_action).defender_pos, state.intruder_pos
            ):
                best_action = action
        alpha = max(alpha, best_value)
    return best_action, best_value