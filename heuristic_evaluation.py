import math

from AirspaceState import distance_point_to_inclusive_rect


def calculate_distance(pos1, pos2):
    """Calculates the Euclidean distance between two (x, y) coordinates."""
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def heuristic_evaluation(state):
    """
    Calculates the utility U(s) of the current state for the Defender (MAX).
    Higher scores favor the Defender.
    Terminal states: defender win -> large positive; intruder breach -> large negative.
    """
    # Terminal states: clear win/loss so search prefers winning
    if state.defender_pos == state.intruder_pos:
        return 1e6   # Defender intercepted
    (x1, y1), (x2, y2) = state.restricted_zone
    ix, iy = state.intruder_pos
    if x1 <= ix <= x2 and y1 <= iy <= y2:
        return -1e6   # Intruder breached

    # 1. Define the Weights (You will tune these for your preliminary results)
    w1 = 10.0  # High priority: Keep the intruder away from the protected zone
    w2 = 5.0   # Medium priority: Catch the intruder quickly
    w3 = 2.0   # Lower priority: Avoid risky constraints (e.g., no-fly zones)
    w4 = 3.0   # Pursuit: reward closing the smaller defender–intruder gap (chase in both axes)

    # 2. Safety(s): Measures distance from restricted zone [cite: 199]
    # We want the intruder to be as FAR from the zone as possible.
    # Assuming restricted_zone_center is an (x, y) tuple.
    safety_score = calculate_distance(state.intruder_pos, state.restricted_zone_center)

    # 3. Time(s): Penalizes long engagement [cite: 200]
    # A smaller distance between the Defender and Intruder means a faster interception.
    # By subtracting this, the Defender is motivated to close the gap.
    time_penalty = calculate_distance(state.defender_pos, state.intruder_pos)

    # 4. Risk(s): Models likelihood of failure [cite: 201]
    # Penalize the Defender for getting too close to environmental constraints (no-fly zones).
    risk_penalty = 0.0
    safe_distance_threshold = 5.0 
    
    for nfz_rect in state.no_fly_zones:
        dist_to_nfz = distance_point_to_inclusive_rect(state.defender_pos, nfz_rect)
        if dist_to_nfz < safe_distance_threshold:
            # Inverse relationship: closer to the no-fly zone = exponentially higher risk
            risk_penalty += (safe_distance_threshold - dist_to_nfz) ** 2

    # 5. Pursuit: reward having closed at least one axis (so defender doesn’t only move in one direction)
    dx = abs(state.defender_pos[0] - state.intruder_pos[0])
    dy = abs(state.defender_pos[1] - state.intruder_pos[1])
    pursuit_bonus = max(0, 10 - min(dx, dy))  # higher when min gap is small

    # 6. Final Utility Calculation
    utility = (w1 * safety_score) - (w2 * time_penalty) - (w3 * risk_penalty) + (w4 * pursuit_bonus)

    return utility