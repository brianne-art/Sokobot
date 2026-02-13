import heapq
import time
from collections import deque
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment

DIRECTIONS = {
    'U': (-1, 0),
    'D': (1, 0),
    'L': (0, -1),
    'R': (0, 1),
}


@dataclass(frozen=True)
class State:
    player_pos: tuple  # (row, col)
    boxes: frozenset   # frozenset of (row, col)


@dataclass
class Puzzle:
    state: State
    goals: frozenset   # frozenset of (row, col)
    walls: frozenset   # frozenset of (row, col)
    dimensions: tuple  # (rows, cols)


SYMBOL_MAP = {
    '#': 'wall',
    '@': 'player',
    '+': 'player_on_goal',
    '$': 'box',
    '*': 'box_on_goal',
    '.': 'goal',
    ' ': 'floor',
    '-': 'floor',
}


def parse_puzzle(text):
    """Parse a puzzle string into a Puzzle object.

    Uses standard Sokoban symbols (one character per tile):
        #  = wall
        @  = player
        +  = player on goal
        $  = box
        *  = box on goal
        .  = goal (empty)
        ' ' or - = empty floor
    """
    lines = [line for line in text.splitlines() if line.strip()]

    player_pos = None
    boxes = set()
    goals = set()
    walls = set()

    for row, line in enumerate(lines):
        for col, char in enumerate(line):
            kind = SYMBOL_MAP.get(char)
            if kind is None:
                raise ValueError(f"Unknown symbol '{char}' at row {row}, col {col}")
            if kind == 'wall':
                walls.add((row, col))
            elif kind == 'player':
                player_pos = (row, col)
            elif kind == 'player_on_goal':
                player_pos = (row, col)
                goals.add((row, col))
            elif kind == 'box':
                boxes.add((row, col))
            elif kind == 'box_on_goal':
                boxes.add((row, col))
                goals.add((row, col))
            elif kind == 'goal':
                goals.add((row, col))

    if player_pos is None:
        raise ValueError("No player found in puzzle")

    rows = len(lines)
    cols = max(col for _, col in walls) + 1 if walls else 0

    return Puzzle(
        state=State(player_pos=player_pos, boxes=frozenset(boxes)),
        goals=frozenset(goals),
        walls=frozenset(walls),
        dimensions=(rows, cols),
    )


def get_valid_moves(state, walls):
    """Return list of (direction, new_state) pairs for all valid moves."""
    moves = []
    pr, pc = state.player_pos

    for direction, (dr, dc) in DIRECTIONS.items():
        new_r, new_c = pr + dr, pc + dc
        new_pos = (new_r, new_c)

        if new_pos in walls:
            continue

        if new_pos in state.boxes:
            # Pushing a box — check the space beyond it
            beyond = (new_r + dr, new_c + dc)
            if beyond in walls or beyond in state.boxes:
                continue
            new_boxes = (state.boxes - {new_pos}) | {beyond}
            moves.append((direction, State(new_pos, frozenset(new_boxes))))
        else:
            # Simple move into empty space
            moves.append((direction, State(new_pos, state.boxes)))

    return moves


def is_goal(state, goals):
    """Check if all boxes are on goal positions."""
    return state.boxes == goals


def solve_bfs(puzzle):
    """Solve a puzzle using breadth-first search.

    Returns a list of move directions, or None if unsolvable.
    """
    if is_goal(puzzle.state, puzzle.goals):
        return []

    queue = deque([(puzzle.state, [])])
    visited = {puzzle.state}

    while queue:
        state, path = queue.popleft()
        for direction, new_state in get_valid_moves(state, puzzle.walls):
            if new_state in visited:
                continue
            new_path = path + [direction]
            if is_goal(new_state, puzzle.goals):
                return new_path
            visited.add(new_state)
            queue.append((new_state, new_path))

    return None


def is_corner_deadlock(state, walls, goals):
    """Check if any box is stuck in a corner without a goal."""
    for box in state.boxes:
        if box in goals:
            continue
        r, c = box
        wall_up = (r - 1, c) in walls
        wall_down = (r + 1, c) in walls
        wall_left = (r, c - 1) in walls
        wall_right = (r, c + 1) in walls
        if (wall_up or wall_down) and (wall_left or wall_right):
            return True
    return False


def is_wall_deadlock(state, walls, goals):
    """Check if a box is against a wall edge with no goal along that wall line.

    If a box is adjacent to a wall on one axis, it can only move along the
    other axis. If there's no goal reachable along that line, it's deadlocked.
    """
    for box in state.boxes:
        if box in goals:
            continue
        r, c = box
        wall_up = (r - 1, c) in walls
        wall_down = (r + 1, c) in walls
        wall_left = (r, c - 1) in walls
        wall_right = (r, c + 1) in walls

        # Box against a horizontal wall (above or below) — can only move L/R
        for vertical_wall in (wall_up, wall_down):
            if not vertical_wall:
                continue
            # Check if there's any goal along this wall row
            has_goal = False
            # Scan left
            cc = c
            while (r, cc) not in walls:
                if (r, cc) in goals:
                    has_goal = True
                    break
                cc -= 1
            if not has_goal:
                # Scan right
                cc = c + 1
                while (r, cc) not in walls:
                    if (r, cc) in goals:
                        has_goal = True
                        break
                    cc += 1
            if not has_goal:
                return True

        # Box against a vertical wall (left or right) — can only move U/D
        for horizontal_wall in (wall_left, wall_right):
            if not horizontal_wall:
                continue
            has_goal = False
            # Scan up
            rr = r
            while (rr, c) not in walls:
                if (rr, c) in goals:
                    has_goal = True
                    break
                rr -= 1
            if not has_goal:
                # Scan down
                rr = r + 1
                while (rr, c) not in walls:
                    if (rr, c) in goals:
                        has_goal = True
                        break
                    rr += 1
            if not has_goal:
                return True

    return False


def is_deadlocked(state, walls, goals):
    """Check if a state is deadlocked (unsolvable)."""
    return is_corner_deadlock(state, walls, goals) or is_wall_deadlock(state, walls, goals)


def manhattan_distance(pos1, pos2):
    """Manhattan distance between two (row, col) positions."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def heuristic_manhattan(state, goals):
    """Sum of each box's Manhattan distance to its nearest goal.

    Admissible: each box must travel at least as far as its nearest goal.
    May underestimate when multiple boxes share the same nearest goal.
    """
    return sum(
        min(manhattan_distance(box, goal) for goal in goals)
        for box in state.boxes
    )


def heuristic_hungarian(state, goals):
    """Optimal box-goal assignment using the Hungarian algorithm.

    Builds a cost matrix of Manhattan distances between all boxes and goals,
    then finds the minimum-cost assignment. Always >= heuristic_manhattan
    and still admissible.
    """
    if not state.boxes:
        return 0
    boxes = list(state.boxes)
    goals_list = list(goals)
    cost = np.array([
        [manhattan_distance(b, g) for g in goals_list]
        for b in boxes
    ])
    row_ind, col_ind = linear_sum_assignment(cost)
    return int(cost[row_ind, col_ind].sum())


def solve_astar(puzzle, heuristic=None, timeout=60):
    """Solve a puzzle using A* search.

    Returns (solution, stats) where solution is a list of move directions
    or None, and stats is a dict with search statistics.
    """
    if heuristic is None:
        heuristic = heuristic_hungarian

    stats = {'states_explored': 0, 'time': 0.0, 'timed_out': False}
    start_time = time.monotonic()

    if is_goal(puzzle.state, puzzle.goals):
        stats['time'] = time.monotonic() - start_time
        return [], stats

    h = heuristic(puzzle.state, puzzle.goals)
    # (f_score, tie_breaker, g_score, state, path)
    counter = 0
    open_set = [(h, counter, 0, puzzle.state, [])]
    visited = set()

    while open_set:
        if time.monotonic() - start_time > timeout:
            stats['time'] = time.monotonic() - start_time
            stats['timed_out'] = True
            return None, stats

        f, _, g, state, path = heapq.heappop(open_set)

        if state in visited:
            continue
        visited.add(state)
        stats['states_explored'] += 1

        for direction, new_state in get_valid_moves(state, puzzle.walls):
            if new_state in visited:
                continue
            new_g = g + 1
            new_path = path + [direction]
            if is_goal(new_state, puzzle.goals):
                stats['states_explored'] += 1
                stats['time'] = time.monotonic() - start_time
                return new_path, stats
            if is_deadlocked(new_state, puzzle.walls, puzzle.goals):
                continue
            new_h = heuristic(new_state, puzzle.goals)
            counter += 1
            heapq.heappush(open_set, (new_g + new_h, counter, new_g, new_state, new_path))

    stats['time'] = time.monotonic() - start_time
    return None, stats


def verify_solution(puzzle, moves):
    """Apply moves to puzzle and check if the goal state is reached."""
    state = puzzle.state
    for move in moves:
        found = False
        for direction, new_state in get_valid_moves(state, puzzle.walls):
            if direction == move:
                state = new_state
                found = True
                break
        if not found:
            return False
    return is_goal(state, puzzle.goals)


def solve_puzzle(text, timeout=60):
    """End-to-end solver: parse, solve, verify, and print results.

    Returns the solution list or None.
    """
    puzzle = parse_puzzle(text)
    solution, stats = solve_astar(puzzle, timeout=timeout)

    if solution is not None:
        verified = verify_solution(puzzle, solution)
        print(f"Solution found in {len(solution)} moves: {solution}")
        print(f"  States explored: {stats['states_explored']}")
        print(f"  Time: {stats['time']:.3f}s")
        print(f"  Verified: {verified}")
        if not verified:
            print("  WARNING: Solution verification failed!")
    else:
        if stats['timed_out']:
            print(f"No solution found (timed out after {stats['time']:.1f}s)")
        else:
            print("No solution found (puzzle is unsolvable)")
        print(f"  States explored: {stats['states_explored']}")
        print(f"  Time: {stats['time']:.3f}s")

    return solution
