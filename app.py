from flask import Flask, jsonify, request, send_from_directory

from sokoban import parse_puzzle, solve_astar, get_valid_moves, is_goal

app = Flask(__name__, static_folder='static')

PUZZLES = [
    {
        'id': 'trivial',
        'name': 'Trivial (1 box, 1 push)',
        'text': '#####\n#@$.#\n#####',
    },
    {
        'id': 'easy',
        'name': 'Easy (1 box)',
        'text': '######\n#@   #\n#  $ #\n#  . #\n#    #\n######',
    },
    {
        'id': 'medium',
        'name': 'Medium (2 boxes)',
        'text': '######\n#@$ .#\n# $ .#\n######',
    },
    {
        'id': 'hard',
        'name': 'Hard (3 boxes)',
        'text': '########\n#      #\n# @$ . #\n#  $ . #\n#  $ . #\n#      #\n########',
    },
]


def replay_solution(puzzle, moves):
    """Replay moves and collect each intermediate state as a step."""
    steps = []
    state = puzzle.state

    steps.append({
        'player': list(state.player_pos),
        'boxes': sorted([list(b) for b in state.boxes]),
    })

    for move in moves:
        for direction, new_state in get_valid_moves(state, puzzle.walls):
            if direction == move:
                state = new_state
                break
        steps.append({
            'player': list(state.player_pos),
            'boxes': sorted([list(b) for b in state.boxes]),
        })

    return steps


def parse_grid_info(puzzle):
    """Extract static grid info (walls, goals, dimensions) for frontend rendering."""
    return {
        'walls': sorted([list(w) for w in puzzle.walls]),
        'goals': sorted([list(g) for g in puzzle.goals]),
        'dimensions': list(puzzle.dimensions),
    }


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/puzzles')
def get_puzzles():
    return jsonify(PUZZLES)


@app.route('/api/solve', methods=['POST'])
def solve():
    data = request.get_json()
    if not data or 'puzzle' not in data:
        return jsonify({'solved': False, 'error': 'Missing puzzle field'}), 400

    puzzle_text = data['puzzle']

    try:
        puzzle = parse_puzzle(puzzle_text)
    except ValueError as e:
        return jsonify({'solved': False, 'error': f'Invalid puzzle: {e}'}), 400

    solution, stats = solve_astar(puzzle, timeout=60)

    result_stats = {
        'states_explored': stats['states_explored'],
        'time': round(stats['time'], 3),
    }

    if solution is not None:
        steps = replay_solution(puzzle, solution)
        grid = parse_grid_info(puzzle)
        return jsonify({
            'solved': True,
            'moves': solution,
            'steps': steps,
            'grid': grid,
            'stats': result_stats,
        })
    else:
        error = 'Timed out after 60 seconds' if stats['timed_out'] else 'Puzzle is unsolvable'
        return jsonify({
            'solved': False,
            'error': error,
            'stats': result_stats,
        })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
