import csv
import time
from pathlib import Path

from AirspaceState import AirspaceState, point_in_inclusive_rect
from minimax_search import minimax_search, get_best_action_minimax
from alpha_beta_search import alpha_beta_search, get_best_action_alpha_beta
from expectimax_search import expectimax_search, get_best_action_expectimax
from heuristic_evaluation import calculate_distance


def get_grid_bounds(state):
    """Return (x_min, x_max, y_min, y_max) for display, from state.grid_bounds or inferred."""
    if state.grid_bounds is not None:
        return state.grid_bounds
    xs = [state.defender_pos[0], state.intruder_pos[0]]
    ys = [state.defender_pos[1], state.intruder_pos[1]]
    for (a, b) in state.restricted_zone:
        xs.extend([a, b])
        ys.extend([a, b])
    for c1, c2 in state.no_fly_zones:
        for p in (c1, c2):
            xs.append(p[0])
            ys.append(p[1])
    pad = 2
    return (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)


def print_state_grid(state, title=None):
    """
    Print the airspace as a grid: D=Defender, I=Intruder, R=Restricted zone, N=No-fly, .=empty.
    Same cell: X. Row 0 at bottom so UP (y+1) goes up on screen.
    """
    x_min, x_max, y_min, y_max = get_grid_bounds(state)
    (rx1, ry1), (rx2, ry2) = state.restricted_zone
    r_xlo, r_xhi = min(rx1, rx2), max(rx1, rx2)
    r_ylo, r_yhi = min(ry1, ry2), max(ry1, ry2)
    def in_nfz_cell(x, y):
        for rect in state.no_fly_zones:
            if point_in_inclusive_rect((x, y), rect):
                return True
        return False
    def_pos = (int(state.defender_pos[0]), int(state.defender_pos[1]))
    int_pos = (int(state.intruder_pos[0]), int(state.intruder_pos[1]))

    if title:
        print(title)

    # Header: column indices (compact: one char per column)
    width = x_max - x_min + 1
    header = "    " + "".join(str(i % 10) for i in range(x_min, x_max + 1))
    print(header)

    # Rows from top (y_max) to bottom (y_min) so UP is visually up
    for y in range(y_max, y_min - 1, -1):
        row = f"{y:3} "
        for x in range(x_min, x_max + 1):
            if def_pos == (x, y) and int_pos == (x, y):
                cell = "X"  # both on same cell
            elif def_pos == (x, y):
                cell = "D"
            elif int_pos == (x, y):
                cell = "I"
            elif r_xlo <= x <= r_xhi and r_ylo <= y <= r_yhi:
                cell = "R"
            elif in_nfz_cell(x, y):
                cell = "N"
            else:
                cell = "."
            row += cell
        print(row)
    print("     (D=Defender, I=Intruder, R=Restricted, N=No-fly, X=both)")
    print()


def get_intruder_greedy_action(state):
    """A simple policy for the Intruder: always move towards the restricted zone."""
    best_action = "STAY"
    min_dist = float('inf')
    
    for action in state.get_legal_actions(1):
        successor = state.generate_successor(1, action)
        dist = calculate_distance(successor.intruder_pos, state.restricted_zone_center)
        if dist < min_dist:
            min_dist = dist
            best_action = action
            
    return best_action


def intruder_in_restricted_zone(state):
    """True if intruder is inside the restricted zone rectangle (same rule as AirspaceState.is_terminal)."""
    (x1, y1), (x2, y2) = state.restricted_zone
    ix, iy = state.intruder_pos
    return x1 <= ix <= x2 and y1 <= iy <= y2


def write_matlab_airspace_files(
    state,
    out_dir=".",
    config_name="airspace_config.csv",
    no_fly_name="no_fly_zones.csv",
):
    """
    Write grid bounds, restricted zone, start positions, and no-fly rectangles for animate_airspace.m
    (read when these files are present in the same folder as the .m file).
    """
    out = Path(out_dir)
    x_min, x_max, y_min, y_max = get_grid_bounds(state)
    (rx1, ry1), (rx2, ry2) = state.restricted_zone
    cfg_path = out / config_name
    with open(cfg_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "grid_x_min",
                "grid_x_max",
                "grid_y_min",
                "grid_y_max",
                "rz_x1",
                "rz_y1",
                "rz_x2",
                "rz_y2",
                "def0_x",
                "def0_y",
                "int0_x",
                "int0_y",
            ]
        )
        w.writerow(
            [
                x_min,
                x_max,
                y_min,
                y_max,
                rx1,
                ry1,
                rx2,
                ry2,
                state.defender_pos[0],
                state.defender_pos[1],
                state.intruder_pos[0],
                state.intruder_pos[1],
            ]
        )
    nfz_path = out / no_fly_name
    with open(nfz_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x1", "y1", "x2", "y2"])
        for c1, c2 in state.no_fly_zones:
            w.writerow([c1[0], c1[1], c2[0], c2[1]])
    return str(cfg_path), str(nfz_path)


def simulate_game(
    initial_state,
    search_depth,
    use_expectimax=False,
    log_csv_path="simulation_log.csv",
    verbose=True,
):
    """Runs a full turn-by-turn simulation until a terminal state is reached.
    Writes agents' coordinates to log_csv_path at the end of each turn."""
    state = initial_state
    turn = 1
    max_turns = 50  # Safety net to prevent infinite loops during testing

    algorithm_name = "Expectimax" if use_expectimax else "Alpha-Beta"
    if verbose:
        print(f"\n=== Starting Full Simulation: {algorithm_name} (Depth {search_depth}) ===")

    with open(log_csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["turn", "defender_x", "defender_y", "intruder_x", "intruder_y"])

        while not state.is_terminal() and turn <= max_turns:
            if verbose:
                print(f"\n--- Turn {turn} ---")
                print(f"Current State: {state}")
                print_state_grid(state, title=f"  Grid at start of turn {turn}:")

            # 1. Defender's Turn (MAX)
            if use_expectimax:
                def_action, _ = get_best_action_expectimax(state, search_depth)
            else:
                def_action, _ = get_best_action_alpha_beta(state, search_depth)

            if verbose:
                print(f"-> Defender chooses: {def_action}")
            state = state.generate_successor(0, def_action)
            if verbose:
                print_state_grid(state, title="  Grid after Defender move:")

            # Check if Defender caught the Intruder immediately
            if state.is_terminal():
                writer.writerow([turn, state.defender_pos[0], state.defender_pos[1], state.intruder_pos[0], state.intruder_pos[1]])
                break

            # 2. Intruder's Turn (MIN - Greedy)
            int_action = get_intruder_greedy_action(state)
            if verbose:
                print(f"-> Intruder chooses: {int_action}")
            state = state.generate_successor(1, int_action)
            if verbose:
                print_state_grid(state, title="  Grid after Intruder move:")

            writer.writerow([turn, state.defender_pos[0], state.defender_pos[1], state.intruder_pos[0], state.intruder_pos[1]])
            turn += 1

    # Terminal State Evaluation
    if state.defender_pos == state.intruder_pos:
        outcome = f"Result: DEFENDER WINS! Interception took {turn} turn(s)."
    elif intruder_in_restricted_zone(state):
        outcome = "Result: INTRUDER WINS! Restricted zone breached."
    else:
        outcome = (
            "Result: No decisive outcome — max turns reached without interception "
            "and the intruder never entered the restricted zone."
        )

    if verbose:
        print("\n=== Simulation Ended ===")
        print(f"Final State: {state}")
        print_state_grid(state, title="  Final grid:")
        print(f"Log written to {log_csv_path}")
    # Always print who won (so quiet runs, e.g. run_scenario.py, still report the outcome)
    print(outcome)
    if verbose:
        print("========================\n")

def run_tests():
    # 1. Initialize the environment (restricted zone, no-fly zones)
    restricted_zone = [(10, 10), (12, 12)]
    no_fly_zones = [((5, 5), (7, 7))]

    initial_state = AirspaceState(
        defender_pos=(6, 6),
        intruder_pos=(4, 4),
        restricted_zone=restricted_zone,
        no_fly_zones=no_fly_zones,
    )

    print(f"Initial State -> {initial_state}")
    print("-" * 40)

    # 2) Benchmark across depths for report table
    depths = [2, 4, 6, 8]
    results = []
    print("\nBenchmarking algorithms across depths (plies):", depths)
    print("-" * 110)
    print(
        f"{'Depth':>5} | {'MM Val':>9} | {'MM Act':>7} | {'MM t(s)':>8} | "
        f"{'AB Val':>9} | {'AB Act':>7} | {'AB t(s)':>8} | "
        f"{'EX Val':>9} | {'EX Act':>7} | {'EX t(s)':>8}"
    )
    print("-" * 110)

    for depth in depths:
        t0 = time.perf_counter()
        best_action_mm, mm_value = get_best_action_minimax(initial_state, depth)
        t_mm = time.perf_counter() - t0

        t0 = time.perf_counter()
        best_action_ab, ab_value = get_best_action_alpha_beta(initial_state, depth)
        t_ab = time.perf_counter() - t0

        t0 = time.perf_counter()
        best_action_ex, ex_value = get_best_action_expectimax(initial_state, depth)
        t_ex = time.perf_counter() - t0

        results.append(
            (depth, mm_value, best_action_mm, t_mm, ab_value, best_action_ab, t_ab, ex_value, best_action_ex, t_ex)
        )
        print(
            f"{depth:>5} | {mm_value:>9.2f} | {str(best_action_mm):>7} | {t_mm:>8.4f} | "
            f"{ab_value:>9.2f} | {str(best_action_ab):>7} | {t_ab:>8.4f} | "
            f"{ex_value:>9.2f} | {str(best_action_ex):>7} | {t_ex:>8.4f}"
        )
    print("-" * 110)

    print("\nCSV-style results (copy/paste into report):")
    print(
        "depth,minimax_value,minimax_action,minimax_time_s,"
        "alpha_beta_value,alpha_beta_action,alpha_beta_time_s,"
        "expectimax_value,expectimax_action,expectimax_time_s"
    )
    for row in results:
        d, mm_v, mm_a, mm_t, ab_v, ab_a, ab_t, ex_v, ex_a, ex_t = row
        print(
            f"{d},{mm_v:.4f},{mm_a},{mm_t:.6f},"
            f"{ab_v:.4f},{ab_a},{ab_t:.6f},"
            f"{ex_v:.4f},{ex_a},{ex_t:.6f}"
        )

    # Save benchmark table to CSV for report usage
    benchmark_csv_path = "benchmark_results.csv"
    with open(benchmark_csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "depth",
            "minimax_value",
            "minimax_action",
            "minimax_time_s",
            "alpha_beta_value",
            "alpha_beta_action",
            "alpha_beta_time_s",
            "expectimax_value",
            "expectimax_action",
            "expectimax_time_s",
        ])
        for d, mm_v, mm_a, mm_t, ab_v, ab_a, ab_t, ex_v, ex_a, ex_t in results:
            writer.writerow([
                d,
                f"{mm_v:.6f}",
                mm_a,
                f"{mm_t:.6f}",
                f"{ab_v:.6f}",
                ab_a,
                f"{ab_t:.6f}",
                f"{ex_v:.6f}",
                ex_a,
                f"{ex_t:.6f}",
            ])
    print(f"\nBenchmark CSV written to: {benchmark_csv_path}")
    
    # 5. Full Game Simulations
    print("\nRunning Full Game Simulations for Progress Report...")
    depth = depths[-1]  # Use deepest benchmarked depth for simulations
    print(f"Using search depth={depth} for full-game simulations.")
    
    # Give them a bit more room to maneuver for the full simulation
    sim_state = AirspaceState(
        defender_pos=(14, 14),
        intruder_pos=(64, 64),
        restricted_zone=[(30, 30), (40, 40)],
        no_fly_zones=[((20, 20), (20, 20)), ((22, 22), (22, 22))],
        grid_bounds=(0, 80, 0, 80)
    )

    # Simulate with Alpha-Beta (same depth as value tests)
    simulate_game(sim_state, search_depth=depth, use_expectimax=False)
    
    # Simulate with Expectimax
    simulate_game(sim_state, search_depth=depth, use_expectimax=True)

if __name__ == "__main__":
    _t0 = time.perf_counter()
    run_tests()
    _elapsed = time.perf_counter() - _t0
    print(f"\nTotal time to complete tests: {_elapsed:.3f} s")