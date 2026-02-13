from sokoban import (
    parse_puzzle, get_valid_moves, is_goal, solve_bfs, solve_astar,
    manhattan_distance, heuristic_manhattan, heuristic_hungarian,
    is_corner_deadlock, is_wall_deadlock, is_deadlocked,
    verify_solution, solve_puzzle, State,
)


class TestParsePuzzle:
    def test_simple_one_box(self):
        puzzle = (
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        p = parse_puzzle(puzzle)
        assert p.state.player_pos == (1, 1)
        assert p.state.boxes == frozenset([(2, 1)])
        assert p.goals == frozenset([(1, 3)])
        assert (0, 0) in p.walls
        assert (0, 4) in p.walls
        assert p.dimensions == (4, 5)

    def test_box_on_goal(self):
        puzzle = (
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        p = parse_puzzle(puzzle)
        assert (2, 1) in p.state.boxes
        assert (2, 1) in p.goals

    def test_player_on_goal(self):
        puzzle = (
            "####\n"
            "#+ #\n"
            "#$ #\n"
            "####"
        )
        p = parse_puzzle(puzzle)
        assert p.state.player_pos == (1, 1)
        assert (1, 1) in p.goals
        assert (2, 1) in p.state.boxes

    def test_multiple_boxes_and_goals(self):
        puzzle = (
            "#######\n"
            "#@   .#\n"
            "#$   .#\n"
            "# $   #\n"
            "#######"
        )
        p = parse_puzzle(puzzle)
        assert p.state.player_pos == (1, 1)
        assert p.state.boxes == frozenset([(2, 1), (3, 2)])
        assert p.goals == frozenset([(1, 5), (2, 5)])
        assert p.dimensions == (5, 7)

    def test_state_is_hashable(self):
        puzzle = (
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        p = parse_puzzle(puzzle)
        s = {p.state}
        assert p.state in s

    def test_box_on_goal_preserves_both(self):
        """Box on goal should appear in both boxes and goals."""
        puzzle = (
            "#####\n"
            "#@ .#\n"
            "# * #\n"
            "#####"
        )
        p = parse_puzzle(puzzle)
        assert (2, 2) in p.state.boxes
        assert (2, 2) in p.goals
        assert (1, 3) in p.goals

    def test_no_player_raises(self):
        puzzle = (
            "####\n"
            "#  #\n"
            "####"
        )
        try:
            parse_puzzle(puzzle)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "No player" in str(e)

    def test_walls_correct(self):
        puzzle = (
            "###\n"
            "#@#\n"
            "###"
        )
        p = parse_puzzle(puzzle)
        expected_walls = frozenset([
            (0, 0), (0, 1), (0, 2),
            (1, 0),         (1, 2),
            (2, 0), (2, 1), (2, 2),
        ])
        assert p.walls == expected_walls

    def test_equal_states_hash_equal(self):
        """Two states with the same player and boxes should be equal."""
        puzzle1 = (
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        puzzle2 = (
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        p1 = parse_puzzle(puzzle1)
        p2 = parse_puzzle(puzzle2)
        assert p1.state == p2.state
        assert hash(p1.state) == hash(p2.state)


class TestGetValidMoves:
    def test_simple_movement(self):
        p = parse_puzzle(
            "#####\n"
            "#@  #\n"
            "#   #\n"
            "#####"
        )
        moves = get_valid_moves(p.state, p.walls)
        dirs = {d for d, _ in moves}
        assert dirs == {'R', 'D'}

    def test_blocked_by_wall(self):
        p = parse_puzzle(
            "###\n"
            "#@#\n"
            "###"
        )
        moves = get_valid_moves(p.state, p.walls)
        assert moves == []

    def test_push_box(self):
        p = parse_puzzle(
            "#####\n"
            "#@$ #\n"
            "#   #\n"
            "#####"
        )
        moves = get_valid_moves(p.state, p.walls)
        move_dict = {d: s for d, s in moves}
        # Can push box right
        assert 'R' in move_dict
        r_state = move_dict['R']
        assert r_state.player_pos == (1, 2)
        assert (1, 3) in r_state.boxes
        assert (1, 2) not in r_state.boxes

    def test_cant_push_box_into_wall(self):
        p = parse_puzzle(
            "####\n"
            "#@$#\n"
            "####"
        )
        moves = get_valid_moves(p.state, p.walls)
        dirs = {d for d, _ in moves}
        assert 'R' not in dirs

    def test_cant_push_box_into_box(self):
        p = parse_puzzle(
            "#####\n"
            "#@$$#\n"
            "#####"
        )
        moves = get_valid_moves(p.state, p.walls)
        dirs = {d for d, _ in moves}
        assert 'R' not in dirs

    def test_all_four_directions(self):
        p = parse_puzzle(
            "#####\n"
            "#   #\n"
            "# @ #\n"
            "#   #\n"
            "#####"
        )
        moves = get_valid_moves(p.state, p.walls)
        dirs = {d for d, _ in moves}
        assert dirs == {'U', 'D', 'L', 'R'}

    def test_push_updates_state_correctly(self):
        """Push box down: player takes box's old position, box moves one further."""
        p = parse_puzzle(
            "#####\n"
            "#@  #\n"
            "#$  #\n"
            "#   #\n"
            "#####"
        )
        move_dict = {d: s for d, s in get_valid_moves(p.state, p.walls)}
        assert 'D' in move_dict
        new = move_dict['D']
        assert new.player_pos == (2, 1)
        assert (3, 1) in new.boxes
        assert (2, 1) not in new.boxes

    def test_push_preserves_other_boxes(self):
        """Pushing one box should not affect other boxes."""
        p = parse_puzzle(
            "######\n"
            "#@$  #\n"
            "#  $ #\n"
            "######"
        )
        move_dict = {d: s for d, s in get_valid_moves(p.state, p.walls)}
        new = move_dict['R']
        assert (2, 3) in new.boxes  # untouched box
        assert (1, 3) in new.boxes  # pushed box
        assert len(new.boxes) == 2


class TestIsGoal:
    def test_all_boxes_on_goals(self):
        p = parse_puzzle(
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        assert is_goal(p.state, p.goals) is True

    def test_box_not_on_goal(self):
        p = parse_puzzle(
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        assert is_goal(p.state, p.goals) is False

    def test_multiple_boxes_all_on_goals(self):
        p = parse_puzzle(
            "#####\n"
            "#@* #\n"
            "# * #\n"
            "#####"
        )
        assert is_goal(p.state, p.goals) is True

    def test_some_boxes_on_goals(self):
        p = parse_puzzle(
            "######\n"
            "#@ *.#\n"
            "#$   #\n"
            "######"
        )
        assert is_goal(p.state, p.goals) is False


class TestSolveBFS:
    def test_already_solved(self):
        p = parse_puzzle(
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        solution = solve_bfs(p)
        assert solution == []

    def test_one_push(self):
        p = parse_puzzle(
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        solution = solve_bfs(p)
        assert solution == ['R']

    def test_simple_puzzle(self):
        p = parse_puzzle(
            "######\n"
            "#@ $.#\n"
            "#    #\n"
            "######"
        )
        solution = solve_bfs(p)
        assert solution is not None
        # Verify solution by replaying moves
        state = p.state
        for move in solution:
            move_dict = {d: s for d, s in get_valid_moves(state, p.walls)}
            assert move in move_dict, f"Invalid move {move}"
            state = move_dict[move]
        assert is_goal(state, p.goals)

    def test_two_box_puzzle(self):
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "# $ .#\n"
            "######"
        )
        solution = solve_bfs(p)
        assert solution is not None
        # Verify by replay
        state = p.state
        for move in solution:
            move_dict = {d: s for d, s in get_valid_moves(state, p.walls)}
            state = move_dict[move]
        assert is_goal(state, p.goals)

    def test_unsolvable_returns_none(self):
        # Box in corner, goal elsewhere — unsolvable
        p = parse_puzzle(
            "####\n"
            "#*.#\n"
            "#@ #\n"
            "####"
        )
        # Manually create a state where box is stuck in corner without goal
        stuck = State(player_pos=(2, 1), boxes=frozenset([(1, 1)]))
        stuck_puzzle = type(p)(
            state=stuck,
            goals=frozenset([(1, 2)]),
            walls=p.walls,
            dimensions=p.dimensions,
        )
        solution = solve_bfs(stuck_puzzle)
        assert solution is None

    def test_solution_is_optimal(self):
        """BFS should find the shortest solution."""
        # Box at (1,2), goal at (1,4) — two pushes right
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "######"
        )
        solution = solve_bfs(p)
        assert solution is not None
        state = p.state
        for move in solution:
            move_dict = {d: s for d, s in get_valid_moves(state, p.walls)}
            state = move_dict[move]
        assert is_goal(state, p.goals)
        # Optimal: R, R (push box twice)
        assert len(solution) == 2


class TestManhattanHeuristic:
    def test_manhattan_distance(self):
        assert manhattan_distance((0, 0), (3, 4)) == 7
        assert manhattan_distance((2, 2), (2, 2)) == 0
        assert manhattan_distance((1, 5), (4, 2)) == 6

    def test_heuristic_at_goal_is_zero(self):
        p = parse_puzzle(
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        assert heuristic_manhattan(p.state, p.goals) == 0

    def test_heuristic_value(self):
        # boxes at (2,1), goals at (1,3)
        p = parse_puzzle(
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        h = heuristic_manhattan(p.state, p.goals)
        # box (2,1) to goal (1,3) = |2-1| + |1-3| = 3
        assert h == 3

    def test_heuristic_two_boxes(self):
        # boxes at (2,2) and (3,3), goals at (2,4) and (4,2)
        state = State(player_pos=(1, 1), boxes=frozenset([(2, 2), (3, 3)]))
        goals = frozenset([(2, 4), (4, 2)])
        h = heuristic_manhattan(state, goals)
        # box (2,2): min(dist to (2,4)=2, dist to (4,2)=2) = 2
        # box (3,3): min(dist to (2,4)=2, dist to (4,2)=2) = 2
        # h = 4
        assert h == 4

    def test_heuristic_is_admissible(self):
        """Heuristic should never overestimate actual cost."""
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "######"
        )
        h = heuristic_manhattan(p.state, p.goals)
        solution, _ = solve_astar(p)
        assert h <= len(solution)


class TestSolveAStar:
    def _verify_solution(self, puzzle, solution):
        """Replay moves and check goal is reached."""
        state = puzzle.state
        for move in solution:
            move_dict = {d: s for d, s in get_valid_moves(state, puzzle.walls)}
            assert move in move_dict, f"Invalid move {move}"
            state = move_dict[move]
        assert is_goal(state, puzzle.goals)

    def test_already_solved(self):
        p = parse_puzzle(
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        solution, stats = solve_astar(p)
        assert solution == []

    def test_one_push(self):
        p = parse_puzzle(
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        solution, stats = solve_astar(p)
        assert solution == ['R']

    def test_two_box_puzzle(self):
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "# $ .#\n"
            "######"
        )
        solution, stats = solve_astar(p)
        assert solution is not None
        self._verify_solution(p, solution)

    def test_same_length_as_bfs(self):
        """A* should find optimal solutions (same length as BFS)."""
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "######"
        )
        bfs_solution = solve_bfs(p)
        astar_solution, _ = solve_astar(p)
        assert len(astar_solution) == len(bfs_solution)

    def test_fewer_states_than_bfs(self):
        """A* should explore fewer or equal states compared to BFS on a larger puzzle."""
        p = parse_puzzle(
            "#######\n"
            "#@  $.#\n"
            "#     #\n"
            "#######"
        )
        # BFS: count visited states
        bfs_visited = set()
        bfs_visited.add(p.state)
        from collections import deque
        queue = deque([(p.state, [])])
        bfs_found = False
        while queue:
            state, path = queue.popleft()
            for d, ns in get_valid_moves(state, p.walls):
                if ns in bfs_visited:
                    continue
                if is_goal(ns, p.goals):
                    bfs_found = True
                    break
                bfs_visited.add(ns)
                queue.append((ns, path + [d]))
            if bfs_found:
                break

        _, astar_stats = solve_astar(p)
        assert astar_stats['states_explored'] <= len(bfs_visited)

    def test_unsolvable_returns_none(self):
        stuck = State(player_pos=(2, 1), boxes=frozenset([(1, 1)]))
        p = parse_puzzle(
            "####\n"
            "#*.#\n"
            "#@ #\n"
            "####"
        )
        stuck_puzzle = type(p)(
            state=stuck,
            goals=frozenset([(1, 2)]),
            walls=p.walls,
            dimensions=p.dimensions,
        )
        solution, _ = solve_astar(stuck_puzzle)
        assert solution is None

    def test_medium_puzzle(self):
        p = parse_puzzle(
            "#######\n"
            "#     #\n"
            "#@$ . #\n"
            "#  $ .#\n"
            "#######"
        )
        solution, stats = solve_astar(p)
        assert solution is not None
        self._verify_solution(p, solution)


class TestCornerDeadlock:
    def test_box_in_corner_no_goal(self):
        """Box in top-left corner with no goal there is deadlocked."""
        p = parse_puzzle(
            "#####\n"
            "#  @#\n"
            "#  .#\n"
            "#####"
        )
        state = State(player_pos=(1, 2), boxes=frozenset([(1, 1)]))
        assert is_corner_deadlock(state, p.walls, p.goals) is True

    def test_box_in_corner_with_goal(self):
        """Box in corner WITH a goal there is not deadlocked."""
        p = parse_puzzle(
            "#####\n"
            "#@  #\n"
            "#*  #\n"
            "#####"
        )
        assert is_corner_deadlock(p.state, p.walls, p.goals) is False

    def test_box_along_wall_not_corner(self):
        """Box against one wall but not cornered is not a corner deadlock."""
        p = parse_puzzle(
            "#####\n"
            "#   #\n"
            "#$@ #\n"
            "#  .#\n"
            "#####"
        )
        assert is_corner_deadlock(p.state, p.walls, p.goals) is False

    def test_multiple_boxes_one_deadlocked(self):
        """One box in corner without goal triggers deadlock."""
        p = parse_puzzle(
            "#####\n"
            "#  @#\n"
            "#  .#\n"
            "#  .#\n"
            "#####"
        )
        # Box at (1,1) is in corner, box at (2,3) is on goal
        state = State(player_pos=(1, 3), boxes=frozenset([(1, 1), (2, 3)]))
        assert is_corner_deadlock(state, p.walls, p.goals) is True


class TestWallDeadlock:
    def test_box_against_top_wall_no_goal_in_row(self):
        """Box against top wall with no goal along that wall segment."""
        p = parse_puzzle(
            "#####\n"
            "# $@#\n"
            "#   #\n"
            "#  .#\n"
            "#####"
        )
        assert is_wall_deadlock(p.state, p.walls, p.goals) is True

    def test_box_against_wall_with_goal_in_row(self):
        """Box against top wall but goal exists along that wall row."""
        p = parse_puzzle(
            "#####\n"
            "#.$@#\n"
            "#   #\n"
            "#####"
        )
        assert is_wall_deadlock(p.state, p.walls, p.goals) is False

    def test_box_against_left_wall_no_goal_in_col(self):
        """Box against left wall with no goal along that column."""
        p = parse_puzzle(
            "#####\n"
            "#$  #\n"
            "#@ .#\n"
            "#####"
        )
        assert is_wall_deadlock(p.state, p.walls, p.goals) is True

    def test_box_against_left_wall_with_goal_in_col(self):
        """Box against left wall with goal in same column."""
        p = parse_puzzle(
            "######\n"
            "#    #\n"
            "#$ @ #\n"
            "#.   #\n"
            "######"
        )
        assert is_wall_deadlock(p.state, p.walls, p.goals) is False


class TestDeadlockInSearch:
    def _verify_solution(self, puzzle, solution):
        state = puzzle.state
        for move in solution:
            move_dict = {d: s for d, s in get_valid_moves(state, puzzle.walls)}
            assert move in move_dict
            state = move_dict[move]
        assert is_goal(state, puzzle.goals)

    def test_deadlock_pruning_reduces_states(self):
        """With deadlock detection, A* should explore fewer states than BFS."""
        p = parse_puzzle(
            "#######\n"
            "#     #\n"
            "#@$ . #\n"
            "#  $ .#\n"
            "#######"
        )
        solution, stats = solve_astar(p)
        assert solution is not None

        bfs_visited = set()
        bfs_visited.add(p.state)
        from collections import deque
        queue = deque([(p.state, [])])
        while queue:
            state, path = queue.popleft()
            for d, ns in get_valid_moves(state, p.walls):
                if ns in bfs_visited:
                    continue
                if is_goal(ns, p.goals):
                    break
                bfs_visited.add(ns)
                queue.append((ns, path + [d]))
        assert stats['states_explored'] <= len(bfs_visited)

    def test_solvable_puzzle_still_works(self):
        """Deadlock detection should not reject valid states."""
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "# $ .#\n"
            "######"
        )
        solution, _ = solve_astar(p)
        assert solution is not None
        self._verify_solution(p, solution)

    def test_unsolvable_detected_faster(self):
        """Unsolvable puzzle where box will be pushed into corner."""
        p = parse_puzzle(
            "####\n"
            "#@.#\n"
            "#$ #\n"
            "####"
        )
        solution, stats = solve_astar(p)
        assert solution is None
        assert stats['states_explored'] < 20


class TestHungarianHeuristic:
    def test_at_goal_is_zero(self):
        p = parse_puzzle(
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        assert heuristic_hungarian(p.state, p.goals) == 0

    def test_single_box(self):
        p = parse_puzzle(
            "#####\n"
            "#@ .#\n"
            "#$  #\n"
            "#####"
        )
        # box (2,1) to goal (1,3) = 3
        assert heuristic_hungarian(p.state, p.goals) == 3

    def test_hungarian_ge_manhattan(self):
        """Hungarian should produce >= estimate compared to naive nearest-goal."""
        # Two boxes that share the same nearest goal
        state = State(player_pos=(0, 0), boxes=frozenset([(1, 1), (1, 3)]))
        goals = frozenset([(1, 2), (3, 3)])
        h_man = heuristic_manhattan(state, goals)
        h_hun = heuristic_hungarian(state, goals)
        assert h_hun >= h_man

    def test_hungarian_tighter_than_manhattan(self):
        """Hungarian should give a tighter estimate when boxes compete for goals."""
        # Both boxes nearest to same goal — manhattan double-counts
        state = State(player_pos=(0, 0), boxes=frozenset([(1, 1), (1, 3)]))
        goals = frozenset([(1, 2), (5, 5)])
        h_man = heuristic_manhattan(state, goals)
        h_hun = heuristic_hungarian(state, goals)
        # Manhattan: min(1, 8) + min(1, 6) = 1 + 1 = 2
        # Hungarian optimal: (1,1)->(1,2)=1 + (1,3)->(5,5)=6 = 7
        #                 or (1,1)->(5,5)=8 + (1,3)->(1,2)=1 = 9
        # Hungarian picks cost 7
        assert h_man == 2
        assert h_hun == 7
        assert h_hun > h_man

    def test_admissible(self):
        """Hungarian heuristic should never overestimate."""
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "######"
        )
        h = heuristic_hungarian(p.state, p.goals)
        solution, _ = solve_astar(p)
        assert h <= len(solution)

    def test_three_box_puzzle(self):
        """Hungarian should handle 3 boxes."""
        state = State(
            player_pos=(0, 0),
            boxes=frozenset([(1, 1), (2, 2), (3, 3)]),
        )
        goals = frozenset([(1, 3), (3, 1), (2, 2)])
        h = heuristic_hungarian(state, goals)
        # Optimal assignment: (1,1)->(1,3)=2, (2,2)->(2,2)=0, (3,3)->(3,1)=2 → 4
        assert h == 4


class TestSolveAStarHungarian:
    def _verify_solution(self, puzzle, solution):
        state = puzzle.state
        for move in solution:
            move_dict = {d: s for d, s in get_valid_moves(state, puzzle.walls)}
            assert move in move_dict
            state = move_dict[move]
        assert is_goal(state, puzzle.goals)

    def test_uses_hungarian_by_default(self):
        """solve_astar should use Hungarian heuristic by default."""
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "######"
        )
        solution, _ = solve_astar(p)
        assert solution is not None
        self._verify_solution(p, solution)

    def test_hungarian_fewer_states_than_manhattan(self):
        """Hungarian heuristic should explore fewer states on competing-goal puzzles."""
        p = parse_puzzle(
            "#######\n"
            "#     #\n"
            "#@$ . #\n"
            "#  $ .#\n"
            "#######"
        )
        _, stats_hun = solve_astar(p, heuristic=heuristic_hungarian)
        _, stats_man = solve_astar(p, heuristic=heuristic_manhattan)
        assert stats_hun['states_explored'] <= stats_man['states_explored']

    def test_optimal_same_as_bfs(self):
        """Hungarian A* should find same-length solution as BFS."""
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "# $ .#\n"
            "######"
        )
        bfs_solution = solve_bfs(p)
        astar_solution, _ = solve_astar(p)
        assert len(astar_solution) == len(bfs_solution)

    def test_medium_puzzle(self):
        p = parse_puzzle(
            "########\n"
            "#      #\n"
            "# @$ . #\n"
            "#  $ . #\n"
            "#  $ . #\n"
            "#      #\n"
            "########"
        )
        solution, stats = solve_astar(p)
        assert solution is not None
        self._verify_solution(p, solution)


class TestTimeout:
    def test_timeout_returns_none(self):
        """With a very short timeout, solver should return None and flag timed_out."""
        p = parse_puzzle(
            "########\n"
            "#      #\n"
            "# @$ . #\n"
            "#  $ . #\n"
            "#  $ . #\n"
            "#      #\n"
            "########"
        )
        solution, stats = solve_astar(p, timeout=0.0001)
        assert solution is None
        assert stats['timed_out'] is True

    def test_stats_include_time(self):
        p = parse_puzzle(
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        solution, stats = solve_astar(p)
        assert 'time' in stats
        assert stats['time'] >= 0
        assert stats['timed_out'] is False


class TestVerifySolution:
    def test_valid_solution(self):
        p = parse_puzzle(
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        assert verify_solution(p, ['R']) is True

    def test_invalid_move(self):
        p = parse_puzzle(
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        assert verify_solution(p, ['U']) is False

    def test_incomplete_solution(self):
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "######"
        )
        assert verify_solution(p, ['R']) is False

    def test_empty_solution_at_goal(self):
        p = parse_puzzle(
            "####\n"
            "#@ #\n"
            "#* #\n"
            "####"
        )
        assert verify_solution(p, []) is True

    def test_empty_solution_not_at_goal(self):
        p = parse_puzzle(
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        assert verify_solution(p, []) is False

    def test_multi_step_solution(self):
        p = parse_puzzle(
            "######\n"
            "#@$ .#\n"
            "# $ .#\n"
            "######"
        )
        solution, _ = solve_astar(p)
        assert verify_solution(p, solution) is True


class TestSolvePuzzleEndToEnd:
    def test_solvable(self, capsys):
        text = (
            "#####\n"
            "#@$.#\n"
            "#####"
        )
        solution = solve_puzzle(text)
        assert solution is not None
        captured = capsys.readouterr()
        assert "Solution found" in captured.out
        assert "Verified: True" in captured.out

    def test_unsolvable(self, capsys):
        text = (
            "####\n"
            "#@.#\n"
            "#$ #\n"
            "####"
        )
        solution = solve_puzzle(text)
        assert solution is None
        captured = capsys.readouterr()
        assert "unsolvable" in captured.out

    def test_timeout(self, capsys):
        text = (
            "########\n"
            "#      #\n"
            "# @$ . #\n"
            "#  $ . #\n"
            "#  $ . #\n"
            "#      #\n"
            "########"
        )
        solution = solve_puzzle(text, timeout=0.0001)
        assert solution is None
        captured = capsys.readouterr()
        assert "timed out" in captured.out

    def test_two_box(self, capsys):
        text = (
            "######\n"
            "#@$ .#\n"
            "# $ .#\n"
            "######"
        )
        solution = solve_puzzle(text)
        assert solution is not None
        captured = capsys.readouterr()
        assert "Verified: True" in captured.out
