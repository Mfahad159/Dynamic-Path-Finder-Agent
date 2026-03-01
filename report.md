# Project Report: Dynamic Pathfinding Agent

**Course:** Artificial Intelligence (AI)  
**Assignment:** A2 – Q6  
**Student:** Muhammad Fahad  
**Campus:** National University of Computer & Emerging Sciences, Chiniot-Faisalabad  
**Semester:** 6  
**Library:** Pygame 2.6.1  
**Language:** Python 3.13  

---

## 1. Introduction

This project implements a **Dynamic Pathfinding Agent** that navigates a grid-based environment using **informed search algorithms**. The agent must not only find a path from a start node to a goal but also react in real time when new obstacles appear while it is in motion. This simulates real-world challenges faced by autonomous robots, self-driving vehicles, and game AI.

The implementation uses **Pygame** for the graphical user interface, enabling a fully interactive experience without any static map files.

---

## 2. Environment Specifications

### 2.1 Dynamic Grid Sizing
At startup the user is prompted to enter the number of rows and columns (5–60). The cell size is computed automatically to fit the screen:
```
cell_size = min((available_width) // cols, window_height // rows)
```

### 2.2 Fixed Start & Goal
- **Start node** (green, labelled "S") defaults to the top-left corner `(0, 0)`.
- **Goal node** (red, labelled "G") defaults to the bottom-right corner `(rows-1, cols-1)`.
- Both can be relocated at any time using the `S` / `G` keys followed by a click.
- The start and goal **cannot** be overwritten by walls or random generation.

### 2.3 Random Map Generation
The `Grid.generate_random(density)` method:
1. Iterates every cell.
2. Assigns `WALL` with probability equal to `density` (default 0.30 = 30%).
3. Always restores start and goal cells after generation.
4. Density is adjustable in real time with `+` / `-` keys (range 5%–80%).

### 2.4 Interactive Map Editor
Mouse interaction is handled in the main event loop:
- **Left-click / left-drag:** place wall
- **Right-click / right-drag:** remove wall
- Drags are processed via `MOUSEMOTION` + `get_pressed()`.

### 2.5 Constraint Compliance
No `.txt` map files are used. All grid state is stored in a Python 2-D list (`Grid.cells`) and generated programmatically.

---

## 3. Algorithmic Implementation

Both algorithms operate on **4-connected grids** (up, down, left, right). All cost values are uniform (step cost = 1).

### 3.1 Greedy Best-First Search (GBFS)

**Evaluation function:** `f(n) = h(n)`

GBFS uses a **min-heap** (priority queue) ordered by the heuristic value alone. It greedily expands whichever open node appears closest to the goal.

**Key properties:**
- **Complete:** No (can loop in non-tree graphs unless visited set is maintained)
- **Optimal:** No (may return a longer path)
- **Time complexity:** O(b^m) worst case
- **Practical speed:** Fast, few nodes expanded when heuristic is accurate

```python
heapq.heappush(heap, (h_fn(start, goal), counter, start))
```

### 3.2 A* Search

**Evaluation function:** `f(n) = g(n) + h(n)`

A* maintains an exact path cost `g(n)` for every discovered node and re-orders the priority queue accordingly. A node is re-inserted if a cheaper path to it is found.

**Key properties:**
- **Complete:** Yes (on finite graphs)
- **Optimal:** Yes (with an admissible heuristic)
- **Time & space complexity:** O(b^d) in the worst case

```python
f_score = new_g + h_fn(nb, goal)
heapq.heappush(heap, (f_score, counter, nb))
```

### 3.3 Heuristic Functions

| Heuristic | Formula | Admissible? | Notes |
|-----------|---------|-------------|-------|
| Manhattan | `\|r1−r2\| + \|c1−c2\|` | ✓ (4-conn.) | Never overestimates on a 4-connected grid |
| Euclidean | `√((r1−r2)²+(c1−c2)²)` | ✓ | Slightly underestimates; can slow A* |

Both heuristics are **admissible** for a 4-connected unit-cost grid, guaranteeing A* optimality.

### 3.4 Tie-Breaking
A monotonically increasing counter is used as a secondary heap key to break ties and ensure FIFO exploration of equal-cost nodes:
```python
heapq.heappush(heap, (f_score, counter, node))
counter += 1
```

---

## 4. Dynamic Obstacles and Re-planning

### 4.1 Spawning Logic
When **Dynamic Mode** is active (button or `D` key), at every agent step:
```python
if random.random() < DYNAMIC_PROB:   # 7% chance
    spawned = grid.spawn_dynamic_wall(remaining_path_set)
```
`spawn_dynamic_wall` picks a random `EMPTY` cell that is **not** in the remaining path set, the start, or the goal. This ensures the agent is not immediately blocked unfairly.

### 4.2 Path-Collision Detection
After a wall is spawned, its coordinates are **compared against the remaining path** (stored as a Python `set` for O(1) lookup):
```python
remaining = set(self.path[self.agent_idx + 1:])
spawned = grid.spawn_dynamic_wall(remaining)
if spawned and spawned in remaining:
    self._replan()
```
If the wall does **not** fall on the path, movement continues without any re-computation — satisfying the efficiency requirement.

### 4.3 Re-planning Mechanism
`App._replan()`:
1. Clears only `PATH`-marked cells (preserves `VISITED` history for context).
2. Calls the selected algorithm from `agent_pos` → `goal`.
3. Marks new path in green.
4. Accumulates metrics (nodes visited, exec time, re-plan counter).
5. If no path exists, halts the agent with an error status.

---

## 5. Visualisation

### 5.1 Search Animation
The algorithm runs to completion first (recording events), then replays them at `ANIM_SPEED = 4` events per frame:

| Event | Cell colour |
|-------|-------------|
| `'frontier'` | 🟡 Yellow |
| `'expand'` | 🔵 Blue |
| Final path | 🟢 Green |
| Agent | 🟠 Orange |
| Dynamic wall | 🔴 Red flash |

### 5.2 Real-Time Metrics Dashboard
The sidebar panel updates live with:

| Metric | Description |
|--------|-------------|
| **Nodes Visited** | Total cells expanded by the algorithm |
| **Path Cost** | Number of steps from start to goal |
| **Exec Time** | Wall-clock time for algorithm computation (ms) |
| **Re-Plans** | Number of times the agent had to re-route |

Metrics accumulate across re-plans to give a holistic view of total effort expended.

---

## 6. GUI Design

The interface is divided into two panels:

**Left panel — Grid canvas**
- Fills available space at a computed cell size.
- "S" and "G" labels drawn inside cells when cell size ≥ 18 px.
- Agent rendered as a circle with a halo effect.

**Right panel — Sidebar (296 px)**
- Algorithm and heuristic toggle buttons (mutually exclusive per group).
- Generate Map, Run, Clear, Set Start/Goal, Dynamic Mode buttons.
- Metrics table.
- Colour legend.
- Keyboard controls reference.
- Status bar with word-wrap and colour coding (green = success, orange = warning, red = error).
- State badge in top-right corner.

---

## 7. State Machine

The application uses a Finite State Machine (FSM):

```
IDLE  ─── SPACE / RUN ──► ANIMATING
            │
            ▼ (animation done + path found)
          MOVING  ──── D ──►  DYNAMIC
            │                    │
            │                    │ (obstacle on path → _replan)
            ◄────────────────────┘
            │
            ▼ (goal reached / no path)
          IDLE
```

Additional states: `SET_START`, `SET_GOAL` (click-to-place modes).

---

## 8. Performance Analysis

| Algorithm | Heuristic | Typical Nodes Visited | Path Optimality |
|-----------|-----------|----------------------|-----------------|
| GBFS | Manhattan | Low | Not guaranteed |
| GBFS | Euclidean | Low | Not guaranteed |
| A* | Manhattan | Medium | Optimal |
| A* | Euclidean | Medium | Optimal |

**Observation:** GBFS is faster (fewer nodes) but may find suboptimal paths. A* with Manhattan consistently finds the shortest path on 4-connected grids.

---

## 9. Conclusion

The Dynamic Pathfinding Agent meets all specified requirements:

- ✅ Dynamic grid sizing via console input
- ✅ Fixed start & goal, relocatable by the user
- ✅ Random map generation with configurable density
- ✅ Interactive map editor (click + drag)
- ✅ No static `.txt` map files
- ✅ GBFS with f(n) = h(n)
- ✅ A* with f(n) = g(n) + h(n)
- ✅ Manhattan and Euclidean heuristics
- ✅ GUI algorithm/heuristic selection
- ✅ Dynamic obstacle spawning (7% chance per step)
- ✅ Efficient path-collision detection (O(1) set lookup)
- ✅ Immediate re-planning from current position
- ✅ Yellow frontier / Blue visited / Green path visualisation
- ✅ Real-time metrics: nodes visited, path cost, exec time (ms), re-plans
- ✅ Full Pygame GUI (no console-only output)

---

## 10. References

1. Russell, S. & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.
2. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics*.
3. Pygame Documentation. https://www.pygame.org/docs/
4. Python `heapq` module. https://docs.python.org/3/library/heapq.html
