def _inclusive_rect_extents(rect):
    """rect: ((x1,y1), (x2,y2)) in any order -> (x_lo, x_hi, y_lo, y_hi) inclusive integer bounds."""
    (x1, y1), (x2, y2) = rect
    return min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)


def point_in_inclusive_rect(pos, rect):
    x_lo, x_hi, y_lo, y_hi = _inclusive_rect_extents(rect)
    x, y = pos[0], pos[1]
    return x_lo <= x <= x_hi and y_lo <= y <= y_hi


def distance_point_to_inclusive_rect(pos, rect):
    """Euclidean distance from pos to the closest point in the closed axis-aligned rectangle."""
    x_lo, x_hi, y_lo, y_hi = _inclusive_rect_extents(rect)
    x, y = float(pos[0]), float(pos[1])
    cx = min(max(x, x_lo), x_hi)
    cy = min(max(y, y_lo), y_hi)
    return ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5


class AirspaceState:
    def __init__(self, defender_pos, intruder_pos, restricted_zone, no_fly_zones=None, grid_bounds=None):
        """
        grid_bounds: optional (x_min, x_max, y_min, y_max). If None, no boundary;
        agents can move arbitrarily. If set, get_legal_actions filters out moves
        that would leave the grid (avoids runaway behavior in search).

        no_fly_zones: list of inclusive rectangles, each the same form as restricted_zone,
        e.g. [((x1,y1), (x2,y2)), ...]. Agents may not end a turn inside any of these.
        """
        self.defender_pos = defender_pos  # (x, y) tuple
        self.intruder_pos = intruder_pos  # (x, y) tuple

        # restricted_zone: bounding box [(x1, y1), (x2, y2)] (any order; center is computed)
        self.restricted_zone = tuple(tuple(p) for p in restricted_zone)
        if len(self.restricted_zone) != 2:
            raise ValueError("restricted_zone must be [(x1,y1), (x2,y2)]")
        self.no_fly_zones = []
        for entry in no_fly_zones or []:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise ValueError("each no_fly entry must be [(x1,y1), (x2,y2)]")
            c0, c1 = entry[0], entry[1]
            r = (tuple(c0), tuple(c1))
            for p in r:
                if len(p) != 2:
                    raise ValueError("each no_fly entry must be [(x1,y1), (x2,y2)]")
            self.no_fly_zones.append(r)
        if grid_bounds is not None:
            self.grid_bounds = tuple(grid_bounds)
            if len(self.grid_bounds) != 4:
                raise ValueError("grid_bounds must be (x_min, x_max, y_min, y_max)")
        else:
            self.grid_bounds = None

        (x1, y1), (x2, y2) = self.restricted_zone
        self.restricted_zone_center = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def position_in_no_fly(self, pos):
        """True if pos lies in any no-fly rectangle (inclusive, same as restricted zone)."""
        for rect in self.no_fly_zones:
            if point_in_inclusive_rect(pos, rect):
                return True
        return False

    def is_terminal(self):
        # 1. Success Criteria: The defending agent successfully intercepts the intruder [cite: 70]
        if self.defender_pos == self.intruder_pos:
            return True
            
        # 2. Failure Criteria: The intruder breaches the restricted zone
        (x1, y1), (x2, y2) = self.restricted_zone
        ix, iy = self.intruder_pos
        if x1 <= ix <= x2 and y1 <= iy <= y2:
            return True
            
        return False

    def get_legal_actions(self, agent_index):
        # Standard 2D grid movements [cite: 33]. Filter: cannot stop inside a no-fly zone;
        # if grid_bounds is set, also keep non-STAY moves inside the grid.
        all_actions = ["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
        x, y = self.defender_pos if agent_index == 0 else self.intruder_pos
        x_min = x_max = y_min = y_max = None
        if self.grid_bounds is not None:
            x_min, x_max, y_min, y_max = self.grid_bounds
        legal = []
        for a in all_actions:
            if a == "STAY":
                nx, ny = x, y
            else:
                nx, ny = x, y
                if a == "UP":
                    ny += 1
                elif a == "DOWN":
                    ny -= 1
                elif a == "LEFT":
                    nx -= 1
                elif a == "RIGHT":
                    nx += 1
            if self.position_in_no_fly((nx, ny)):
                continue
            if self.grid_bounds is not None and a != "STAY":
                if not (x_min <= nx <= x_max and y_min <= ny <= y_max):
                    continue
            legal.append(a)
        return legal

    def generate_successor(self, agent_index, action):
        """
        Creates a new state based on the action taken by the specified agent.
        agent_index 0 = Defender (MAX)
        agent_index 1 = Intruder (MIN)
        """
        # Convert tuples to lists to modify them safely without altering the parent state
        def_pos = list(self.defender_pos)
        int_pos = list(self.intruder_pos)
        
        target_pos = def_pos if agent_index == 0 else int_pos
        
        # Apply the movement
        if action == "UP":
            target_pos[1] += 1
        elif action == "DOWN":
            target_pos[1] -= 1
        elif action == "LEFT":
            target_pos[0] -= 1
        elif action == "RIGHT":
            target_pos[0] += 1
        # If action is "STAY", coordinates do not change
            
        # Re-pack the coordinates
        if agent_index == 0:
            new_def_pos = tuple(target_pos)
            new_int_pos = tuple(int_pos)
        else:
            new_def_pos = tuple(def_pos)
            new_int_pos = tuple(target_pos)
            
        return AirspaceState(
            new_def_pos, new_int_pos, self.restricted_zone, self.no_fly_zones, self.grid_bounds
        )

    def __str__(self):
        """Helper to print the state cleanly during testing."""
        return f"Defender: {self.defender_pos} | Intruder: {self.intruder_pos}"