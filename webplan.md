# Web Interface for Sokoban Solver

## Context
The solver (`sokoban.py`) is complete with `parse_puzzle`, `solve_astar`, `verify_solution`, and all supporting functions. We now need a web UI where users can select a puzzle, send it to the backend for solving, and step through the solution visually.

## Architecture

```
Browser (HTML/JS/CSS) <--JSON--> Flask API (app.py) --> sokoban.py
```

- **Backend**: `app.py` — Flask server with a REST API. Imports solver as a module, no changes to `sokoban.py`.
- **Frontend**: `static/index.html` — single-page app with vanilla JS (no framework). Renders the grid, calls the API, animates the solution.

## API Design

### `GET /api/puzzles`
Returns list of available pre-designed puzzles.
```json
[
  {"id": "trivial", "name": "Trivial (1 box)", "text": "#####\n#@$.#\n#####"},
  ...
]
```

### `POST /api/solve`
Request:
```json
{"puzzle": "#####\n#@$.#\n#####"}
```
Response (success):
```json
{
  "solved": true,
  "moves": ["R"],
  "steps": [
    {"player": [1,1], "boxes": [[1,2]]},
    {"player": [1,2], "boxes": [[1,3]]}
  ],
  "stats": {"states_explored": 2, "time": 0.001}
}
```
The `steps` array includes the initial state plus one entry per move, so the frontend can render each state without re-implementing game logic.

Response (unsolvable/timeout):
```json
{
  "solved": false,
  "error": "Puzzle is unsolvable",
  "stats": {"states_explored": 15, "time": 0.002}
}
```

## Pre-designed Puzzles
Hardcoded in `app.py`:
1. **Trivial** — 1 box, 1 push
2. **Easy** — 1 box, several moves
3. **Medium** — 2 boxes
4. **Hard** — 3 boxes

## Frontend Design
Single HTML file (`static/index.html`) with embedded CSS and JS:

1. **Puzzle selector** — dropdown of pre-designed puzzles, "Load" button
2. **Grid display** — CSS grid/table rendering the puzzle with colored cells (walls=dark, floor=light, goals=dot, boxes=colored square, player=circle)
3. **Controls** — "Solve" button, then step-through controls (Prev / Next / Play/Pause)
4. **Status bar** — shows current step number, total moves, solve time, states explored

### Step-through flow:
1. User selects puzzle → grid renders initial state
2. User clicks "Solve" → POST to `/api/solve` → receives steps array
3. User steps through with Prev/Next or auto-play

## Files to Create
1. **`app.py`** — Flask server (~80 lines)
2. **`static/index.html`** — Single-page frontend (~300 lines)

## Files NOT Modified
- `sokoban.py` — used as-is via import
- `test_sokoban.py` — solver tests unchanged

## Implementation Steps

### Step 1: `app.py` — Flask backend
- Define puzzle list with id/name/text
- `GET /api/puzzles` — return puzzle list
- `POST /api/solve` — parse puzzle text, solve, replay moves to generate steps array, return JSON
- `GET /` — serve `static/index.html`
- Helper to replay solution and collect each intermediate state as `{player, boxes}` for the steps array

### Step 2: `static/index.html` — Frontend
- Puzzle selector dropdown + Load button
- Grid renderer (reads walls/goals from puzzle text, overlays current step's player/boxes)
- Solve button → fetch POST → store steps
- Step controls: Prev, Next, Play/Pause with interval timer
- Status display

### Step 3: Test end-to-end
- `pip install flask`
- `python app.py`
- Open browser, load puzzle, solve, step through
- Verify all 4 puzzles solve and display correctly

## Verification
1. Run `python -m pytest test_sokoban.py` — all 72 existing tests still pass
2. Start server with `python app.py`
3. `curl localhost:5000/api/puzzles` — returns puzzle list JSON
4. `curl -X POST localhost:5000/api/solve -H 'Content-Type: application/json' -d '{"puzzle":"#####\n#@$.#\n#####"}'` — returns solution JSON with steps
5. Open `http://localhost:5000` in browser — load/solve/step through puzzles
