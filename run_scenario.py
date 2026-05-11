#!/usr/bin/env python3
"""
Run minimax, alpha–beta, and expectimax for a custom airspace scenario.

Writes files for animate_airspace.m (same directory as the .m file or --out-dir):
  - simulation_log.csv  — turn-by-turn positions (required by MATLAB)
  - airspace_config.csv — grid, restricted zone, start positions
  - no_fly_zones.csv    — no-fly rectangles, one row per [x1,y1,x2,y2] (may be header-only)

Non-interactive (example):
  python3 run_scenario.py --defender 6 6 --intruder 4 4 \\
    --restricted 10 10 12 12 --depth 5 --no-fly 4 4 7 7

Skip full-game sim / CSV (values only):
  python3 run_scenario.py ... --no-sim

Interactive:
  python3 run_scenario.py -i
"""

import argparse
import time
from pathlib import Path

from AirspaceState import AirspaceState
from alpha_beta_search import get_best_action_alpha_beta
from expectimax_search import get_best_action_expectimax
from minimax_search import get_best_action_minimax
from test_run import simulate_game, write_matlab_airspace_files


def _parse_int_pair(text, label):
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError(f"{label} must be two numbers (x y), got: {text!r}")
    return (int(parts[0]), int(parts[1]))


def _parse_no_fly_rectangles(items):
    """From repeated --no-fly x1 y1 x2 y2, build [((x1,y1), (x2,y2)), ...]."""
    if not items:
        return []
    out = []
    for q in items:
        if len(q) != 4:
            raise ValueError("each --no-fly must have four numbers: x1 y1 x2 y2")
        a, b, c, d = (int(q[0]), int(q[1]), int(q[2]), int(q[3]))
        out.append(((a, b), (c, d)))
    return out


def prompt_scenario():
    print("Custom scenario (integers; empty no-fly line to finish). No-fly regions are inclusive rectangles [(x1,y1),(x2,y2)].")
    d = _parse_int_pair(input("Defender position (x y): ").strip(), "Defender")
    i = _parse_int_pair(input("Intruder position (x y): ").strip(), "Intruder")
    rz = input("Restricted zone corners (x1 y1 x2 y2): ").strip()
    parts = rz.replace(",", " ").split()
    if len(parts) != 4:
        raise SystemExit("Restricted zone must be four numbers: x1 y1 x2 y2")
    restricted_zone = [(int(parts[0]), int(parts[1])), (int(parts[2]), int(parts[3]))]

    no_fly = []
    while True:
        line = input("No-fly rectangle (x1 y1 x2 y2), same form as restricted zone, or Enter to finish: ").strip()
        if not line:
            break
        parts = line.replace(",", " ").split()
        if len(parts) != 4:
            raise SystemExit("No-fly must be four integers: x1 y1 x2 y2")
        no_fly.append(
            ((int(parts[0]), int(parts[1])), (int(parts[2]), int(parts[3])))
        )

    gb = input("Grid bounds (x_min x_max y_min y_max) or Enter for none: ").strip()
    if gb:
        g = gb.replace(",", " ").split()
        if len(g) != 4:
            raise SystemExit("Grid bounds must be four numbers or empty")
        grid_bounds = (int(g[0]), int(g[1]), int(g[2]), int(g[3]))
    else:
        grid_bounds = None

    depth = int(input("Search depth (plies): ").strip())
    return d, i, restricted_zone, no_fly, grid_bounds, depth


def run_algorithms(state, depth):
    print(f"\nState: defender={state.defender_pos} intruder={state.intruder_pos}")
    print(f"       restricted_zone={list(state.restricted_zone)} no_fly={state.no_fly_zones} grid_bounds={state.grid_bounds}")
    print(f"Depth: {depth} (plies)\n")

    t0 = time.perf_counter()
    mm_a, mm_v = get_best_action_minimax(state, depth)
    t_mm = time.perf_counter() - t0

    t0 = time.perf_counter()
    ab_a, ab_v = get_best_action_alpha_beta(state, depth)
    t_ab = time.perf_counter() - t0

    t0 = time.perf_counter()
    ex_a, ex_v = get_best_action_expectimax(state, depth)
    t_ex = time.perf_counter() - t0

    print(f"  Minimax      value={mm_v:12.4f}  best_action={mm_a!s}  time={t_mm:.4f} s")
    print(f"  Alpha–Beta   value={ab_v:12.4f}  best_action={ab_a!s}  time={t_ab:.4f} s")
    print(f"  Expectimax   value={ex_v:12.4f}  best_action={ex_a!s}  time={t_ex:.4f} s")


def run_matlab_export_and_sim(state, sim_depth, out_dir, log_name, use_expectimax):
    """Write MATLAB layout CSVs and run a full-game simulation log (see test_run.simulate_game)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg_p, nfz_p = write_matlab_airspace_files(
        state,
        out_dir=str(out),
    )
    log_path = out / log_name
    sim_label = "Expectimax" if use_expectimax else "Alpha–Beta"
    print(
        f"\n=== Full-game simulation for MATLAB ({sim_label}, depth {sim_depth}) ===\n"
        f"  Writing layout: {cfg_p}, {nfz_p}"
    )
    simulate_game(
        state,
        search_depth=sim_depth,
        use_expectimax=use_expectimax,
        log_csv_path=str(log_path),
        verbose=False,
    )
    print(
        f"  Trajectory: {log_path}\n"
        f"  Open animate_airspace.m in the same folder as these files, then run the script in MATLAB."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Run adversarial search for a custom defender/intruder scenario."
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Prompt for positions, zone, no-fly list, and depth",
    )
    parser.add_argument("--defender", nargs=2, type=int, metavar=("X", "Y"), help="Defender (x y)")
    parser.add_argument("--intruder", nargs=2, type=int, metavar=("X", "Y"), help="Intruder (x y)")
    parser.add_argument(
        "--restricted",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        help="Restricted zone corners [(x1,y1), (x2,y2)]",
    )
    parser.add_argument(
        "--no-fly",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        action="append",
        default=[],
        help="No-fly rectangle, inclusive [(x1,y1),(x2,y2)] (repeat for multiple): --no-fly 4 4 6 6",
    )
    parser.add_argument(
        "--grid-bounds",
        nargs=4,
        type=int,
        metavar=("X_LO", "X_HI", "Y_LO", "Y_HI"),
        help="Optional (x_min x_max y_min y_max)",
    )
    parser.add_argument("--depth", type=int, help="Search depth in plies")
    parser.add_argument(
        "--no-sim",
        action="store_true",
        help="Do not run full-game simulation or write simulation_log / layout CSVs for MATLAB",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=".",
        help="Directory for simulation_log.csv, airspace_config.csv, no_fly_zones.csv (default: .)",
    )
    parser.add_argument(
        "--log",
        type=str,
        default="simulation_log.csv",
        help="Filename for the trajectory log inside --out-dir (default: simulation_log.csv)",
    )
    parser.add_argument(
        "--sim-algorithm",
        choices=("ab", "ex"),
        default="ab",
        help="Defender policy during full-game sim: alpha–beta (ab) or expectimax (ex) (default: ab)",
    )

    args = parser.parse_args()

    if args.interactive or args.depth is None:
        d, i, restricted_zone, no_fly, grid_bounds, depth = prompt_scenario()
    else:
        if not all([args.defender is not None, args.intruder is not None, args.restricted is not None]):
            parser.error("Need --defender, --intruder, and --restricted with --depth (or use -i / --interactive)")
        d = tuple(args.defender)
        i = tuple(args.intruder)
        restricted_zone = [(args.restricted[0], args.restricted[1]), (args.restricted[2], args.restricted[3])]
        no_fly = _parse_no_fly_rectangles(args.no_fly)
        grid_bounds = tuple(args.grid_bounds) if args.grid_bounds else None
        depth = args.depth

    state = AirspaceState(
        defender_pos=d,
        intruder_pos=i,
        restricted_zone=restricted_zone,
        no_fly_zones=no_fly,
        grid_bounds=grid_bounds,
    )
    run_algorithms(state, depth)
    if not args.no_sim:
        run_matlab_export_and_sim(
            state,
            sim_depth=depth,
            out_dir=args.out_dir,
            log_name=args.log,
            use_expectimax=(args.sim_algorithm == "ex"),
        )


if __name__ == "__main__":
    main()
