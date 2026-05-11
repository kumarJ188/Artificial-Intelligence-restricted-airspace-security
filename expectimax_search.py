"""
Expectimax search for uncertainty and probabilistic outcomes (spec §7).
Chance nodes model P(s' | s, a); value is expected utility over successors.
"""

from heuristic_evaluation import heuristic_evaluation


def expectimax_search(state, depth, agent_index):
    """
    Returns the expectimax value of the state.
    agent_index 0 = Defender (MAX), 1 = Intruder (CHANCE).
    V(s) = Σ_{s'} P(s' | s, a) · V(s') at chance nodes.
    depth is in plies (one move = one ply), same as minimax and alpha_beta.
    """
    if depth == 0 or state.is_terminal():
        return heuristic_evaluation(state)

    if agent_index == 0:  # MAX (Defender)
        v = float("-inf")
        for action in state.get_legal_actions(0):
            successor = state.generate_successor(0, action)
            v = max(v, expectimax_search(successor, depth - 1, 1))
        return v

    else:  # CHANCE (Intruder: stochastic outcomes)
        expected_value = 0.0
        legal_actions = state.get_legal_actions(1)
        if not legal_actions:
            return heuristic_evaluation(state)

        probability = 1.0 / len(legal_actions)
        for action in legal_actions:
            successor = state.generate_successor(1, action)
            branch_value = expectimax_search(successor, depth - 1, 0)
            expected_value += probability * branch_value
        return expected_value


def get_best_action_expectimax(state, depth):
    """
    Returns the best action for the Defender at the root and its expected value.
    depth is in plies (one move = one ply), consistent with minimax and alpha_beta.
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
        v = expectimax_search(successor, depth - 1, agent_index=1)
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
    return best_action, best_value