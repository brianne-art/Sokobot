# Sokoban Solver Implementation Plan

## Philosophy
**Develop step-by-step. Test as you go. Understand before proceeding.**

Each phase builds on the previous one. Every phase has clear tests that must pass before moving forward.

---

## Symbol Legend

Uses standard Sokoban notation (one character per tile):

| Symbol | Meaning |
|--------|---------|
| `#`    | Wall |
| `@`    | Player |
| `+`    | Player on goal |
| `$`    | Box |
| `*`    | Box on goal |
| `.`    | Goal (empty) |
| ` `    | Empty floor |

---

## Phase 1: Puzzle Parser and State Representation
**Goal**: Load puzzles and create internal state representation

### What to Build
1. `parse_puzzle(text)` - Convert text to internal format
2. `State` class or structure with:
   - player_pos: (row, col)
   - boxes: frozenset of (row, col)
   - Static data (shared, not part of state hash):
     - goals: set of (row, col)
     - walls: set of (row, col)
     - dimensions: (rows, cols)
   - Goals and walls are static — they never change during moves. Separate them from the dynamic state (player + boxes) so that goals are never lost when the player or a box moves off a goal square.

### What to Test
```python
# Test 1: Parse simple 1-box puzzle
puzzle = """
#####
#@ .#
#$  #
#####
"""
state = parse_puzzle(puzzle)
assert state.player_pos == (1, 1)
assert state.boxes == frozenset([(2, 1)])
assert state.goals == {(1, 3)}
# verify walls, dimensions

# Test 2: Parse box on goal
puzzle = """
####
#@ #
#* #
####
"""
# Box should be in boxes AND goals should contain that position

# Test 3: Parse player on goal
puzzle = """
####
#+ #
#$ #
####
"""
# Player on goal, verify both player_pos and goals
```

### Success Criteria
- Can parse all puzzle elements correctly
- Handles boxes on goals and player on goals
- State is hashable (for use in closed set)

---

## Phase 2: Move Generation and Validation
**Goal**: Generate all valid moves from a state

### What to Build
1. `get_valid_moves(state)` - Returns list of (direction, new_state) pairs
2. Move validation logic:
   - Check if move hits wall
   - Check if push is valid (space beyond box is free)
   - Only allow pushing one box at a time

### What to Test
```python
# Test 1: Simple movement (no boxes)
puzzle = """
#####
#@  #
#   #
#####
"""
moves = get_valid_moves(state)
# Should have RIGHT, DOWN moves available
# Verify new states are correct

# Test 2: Blocked by wall
puzzle = """
###
#@#
###
"""
moves = get_valid_moves(state)
# Should have ZERO moves

# Test 3: Push a box
puzzle = """
#####
#@$ #
#   #
#####
"""
moves = get_valid_moves(state)
# RIGHT should push box to (1,3), player to (1,2)

# Test 4: Can't push (box blocked by wall)
puzzle = """
####
#@$#
####
"""
moves = get_valid_moves(state)
# RIGHT should NOT be valid (box can't move into wall)

# Test 5: Can't push (box blocked by another box)
puzzle = """
#####
#@$$#
#####
"""
moves = get_valid_moves(state)
# RIGHT should NOT be valid (can't push two boxes)
```

### Success Criteria
- Correctly identifies all valid moves
- Properly validates box pushing
- New states are correctly computed

---

## Phase 3: Goal Testing and Basic Search
**Goal**: Implement goal check and simple breadth-first search

### What to Build
1. `is_goal(state)` - Check if all boxes on goals
2. Simple BFS (not A* yet) to verify search framework works

### What to Test
```python
# Test 1: Goal detection
puzzle = """
####
#@ #
#* #
####
"""
assert is_goal(state) == True

# Test 2: Not goal (box not on goal)
puzzle = """
#####
#@ .#
#$  #
#####
"""
assert is_goal(state) == False

# Test 3: Solve trivial puzzle with BFS
puzzle = """
#####
#@$.#
#####
"""
# Box needs one push right
solution = solve_bfs(state)
assert solution == ['R']  # or verify it works

# Test 4: Slightly harder
puzzle = """
######
#@  .#
# $  #
######
"""
# Player must navigate around the box to push it toward the goal.
# Multiple moves required — exact sequence depends on solver.
solution = solve_bfs(state)
assert solution is not None and len(solution) > 0
# Verify by applying moves to reach goal state
```

### Success Criteria
- Goal detection works correctly
- BFS can solve trivial puzzles
- Can reconstruct path from start to goal

---

## Phase 4: Manhattan Distance Heuristic
**Goal**: Implement A* with simple heuristic

### What to Build
1. `manhattan_distance(pos1, pos2)` - Helper function
2. `heuristic_manhattan(state)` - For each box, take its Manhattan distance to the nearest goal, then sum. This is admissible because each box must travel at least as far as its nearest goal, regardless of other boxes. It may underestimate when multiple boxes share the same nearest goal, but that's fine — admissibility only requires never overestimating. Phase 6's Hungarian algorithm fixes this looseness.
3. A* search with this heuristic

### What to Test
```python
# Test 1: Heuristic calculation
state with boxes at [(2,2), (3,3)] and goals at [(2,4), (4,2)]
h = heuristic_manhattan(state)
# For box (2,2): nearest goal is (2,4) at distance 2, or (4,2) at distance 2 → min = 2
# For box (3,3): nearest goal is (2,4) at distance 2, or (4,2) at distance 2 → min = 2
# h = 2 + 2 = 4

# Test 2: Solve same puzzles as BFS, verify A* finds same or better
# Should be same solution length, but explore fewer states

# Test 3: Solve 2-box puzzle
puzzle = """
#######
#@   .#
#$   .#
# $   #
#######
"""
solution = solve_astar(state)
assert solution is not None
# Verify solution works
```

### Success Criteria
- Heuristic is admissible (never overestimates)
- A* finds optimal solutions
- A* explores fewer states than BFS on same puzzles

---

## Phase 5: Deadlock Detection
**Goal**: Prune states where boxes are stuck

### What to Build
1. `is_corner_deadlock(state)` - Check if any box in corner without goal
2. `is_wall_deadlock(state)` - Check if a box is against a wall edge that has no goal along its length (the box can slide along the wall but never reach a goal)
3. Early rejection of deadlocked states in search

### What to Test
```python
# Test 1: Corner deadlock detection
puzzle = """
#####
#  @#
#   #
#  .#
#####
"""
# Simulate a state where the box has been pushed into the top-left corner (1,1).
# Walls are above and to the left, so the box can never be moved again.
state_with_corner_box = make_state(player=(1,2), boxes=frozenset([(1,1)]), ...)
assert is_corner_deadlock(state_with_corner_box) == True

# Test 2: Not a deadlock (goal in corner)
puzzle = """
#####
#@  #
#*  #
#####
"""
# Box is in the corner at (2,1) but there IS a goal there, so it's fine.
assert is_corner_deadlock(state) == False

# Test 3: Unsolvable puzzle should fail faster
puzzle = """
####
#@.#
#$ #
####
"""
# With deadlock detection, should explore fewer states
# and recognize unsolvable faster
```

### Success Criteria
- Correctly identifies simple corner deadlocks
- Search rejects deadlocked states early
- Unsolvable puzzles fail faster

---

## Phase 6: Hungarian Algorithm Heuristic
**Goal**: Better heuristic for faster solving

### What to Build
1. `heuristic_hungarian(state)` - Optimal box-goal matching
2. Use `scipy.optimize.linear_sum_assignment`

### What to Test
```python
# Test 1: Heuristic comparison
# Same state, verify Hungarian >= Manhattan (tighter/higher estimate is better).
# Hungarian finds the optimal assignment so it never underestimates as much
# as the naive nearest-goal sum does.

# Test 2: Solve medium puzzle (3-4 boxes)
puzzle = """
#########
#@     .#
#$     .#
# $    .#
#  $   .#
#########
"""
solution = solve_astar_hungarian(state)
assert solution is not None
# Compare states explored vs Manhattan heuristic

# Test 3: More complex puzzle
# Should solve faster than Manhattan
```

### Success Criteria
- Hungarian heuristic is still admissible
- Explores fewer states than Manhattan on complex puzzles
- Solves 3-5 box puzzles within reasonable time

---

## Phase 7: Timeout and Solution Verification
**Goal**: Add timeout, verify solutions, polish

### What to Build
1. 60-second timeout mechanism
2. `verify_solution(initial_state, moves)` - Apply moves and check goal
3. Pretty-print solution and statistics

### What to Test
```python
# Test 1: Timeout on difficult puzzle
# Verify returns None after 60 seconds

# Test 2: Solution verification
puzzle = ...
solution = solve(state)
assert verify_solution(state, solution) == True

# Test 3: End-to-end on test suite
# Run all test puzzles, verify they solve or timeout gracefully
```

### Success Criteria
- Timeout works correctly
- All solutions are verified
- Can solve puzzles end-to-end and output readable results

---

## Testing Strategy

### Unit Tests
Each phase has focused unit tests on specific functionality

### Integration Tests  
Later phases test that earlier components still work

### Test Puzzle Suite
- **Trivial**: 1 box, obvious solution (sanity check)
- **Easy**: 2-3 boxes, small grid (quick solving)
- **Medium**: 3-5 boxes, ~8x8 grid (target difficulty)
- **Unsolvable**: For deadlock detection

### Before Moving to Next Phase
1. ✅ All tests for current phase pass
2. ✅ Understand what the code does
3. ✅ Code is clean and readable
4. ✅ Previous phase tests still pass

---

## Final Deliverable

A command-line solver that:
1. Loads puzzle from text file or string
2. Solves using A* with Hungarian heuristic
3. Outputs solution moves: `['U', 'R', 'R', 'D', ...]`
4. Verifies solution is correct
5. Prints statistics (states explored, time taken)
6. Handles timeout gracefully

Example usage:
```python
puzzle_text = """
#####
#@ .#
#$  #
#####
"""

solution = solve_puzzle(puzzle_text)
if solution:
    print(f"Solution in {len(solution)} moves: {solution}")
    # ['R', 'R', 'U']
else:
    print("No solution found (timeout or unsolvable)")
```