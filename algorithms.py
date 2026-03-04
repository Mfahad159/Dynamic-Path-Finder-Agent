"""
algorithms.py
=============
Heuristic functions and informed search algorithms (GBFS, A*).

Public API
----------
    manhattan(a, b)  → float
    euclidean(a, b)  → float
    run_gbfs(cells, costs, rows, cols, start, goal, h_fn)  → SearchResult
    run_astar(cells, costs, rows, cols, start, goal, h_fn) → SearchResult

SearchResult = (path | None, events, nodes_visited, path_cost, exec_ms)
    path          : list[(r,c)] start→goal, or None if unreachable
    events        : list[('frontier'|'expand', (r,c))] for animation
    nodes_visited : int
    path_cost     : float (accumulated edge costs)
    exec_ms       : float (wall-clock milliseconds)
"""

import heapq
import math
import time

from constants import WALL

# ── Heuristics ────────────────────────────────────────────────────────────────

def manhattan(a: tuple, b: tuple) -> float:
    """Manhattan distance:  D = |x1−x2| + |y1−y2|"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a: tuple, b: tuple) -> float:
    """Euclidean distance:  D = √((x1−x2)²+(y1−y2)²)"""
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)


HEURISTICS: dict = {
    'Manhattan': manhattan,
    'Euclidean': euclidean,
}

# ── Internal helpers ──────────────────────────────────────────────────────────

def _neighbors(cells: list, rows: int, cols: int, node: tuple) -> list:
    """Return 4-connected walkable neighbours (non-WALL) of *node*."""
    r, c = node
    result = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and cells[nr][nc] != WALL:
            result.append((nr, nc))
    return result


def _reconstruct(came_from: dict, goal: tuple) -> list:
    """Walk backwards through *came_from* to build the path list."""
    path, node = [], goal
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


def _elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0

# ── Greedy Best-First Search ──────────────────────────────────────────────────

def run_gbfs(cells, costs, rows, cols, start, goal, h_fn):
    """
    Greedy Best-First Search  —  f(n) = h(n)

    Expands the node with the smallest heuristic value.
    Fast, but *not* guaranteed to find the optimal path.
    Uses random costs from the costs matrix for each node.
    """
    t0      = time.perf_counter()
    heap    = []
    counter = 0
    heapq.heappush(heap, (h_fn(start, goal), counter, start))

    came_from   = {start: None}
    in_frontier = {start}
    visited     = set()
    events      = []
    nodes_visited = 0

    path_cost = 0  # Track cumulative path cost

    while heap:
        _, _, cur = heapq.heappop(heap)
        if cur in visited:
            continue
        in_frontier.discard(cur)
        visited.add(cur)
        nodes_visited += 1

        if cur != start and cur != goal:
            events.append(('expand', cur))

        if cur == goal:
            path = _reconstruct(came_from, goal)
            # Calculate total path cost
            total_cost = 0
            for node in path[1:]:
                total_cost += costs[node[0]][node[1]]
            return path, events, nodes_visited, total_cost, _elapsed_ms(t0)

        for nb in _neighbors(cells, rows, cols, cur):
            if nb not in visited and nb not in in_frontier:
                came_from[nb] = cur
                counter += 1
                heapq.heappush(heap, (h_fn(nb, goal), counter, nb))
                in_frontier.add(nb)
                if nb != goal:
                    events.append(('frontier', nb))

    return None, events, nodes_visited, 0, _elapsed_ms(t0)

# ── A* Search ─────────────────────────────────────────────────────────────────

def run_astar(cells, costs, rows, cols, start, goal, h_fn):
    """
    A* Search  —  f(n) = g(n) + h(n)

    Combines exact path cost g(n) with heuristic h(n).
    Optimal when the heuristic is admissible (never overestimates).
    Uses random costs from the costs matrix for each node.
    """
    t0      = time.perf_counter()
    heap    = []
    counter = 0
    g_cost  = {start: 0}
    heapq.heappush(heap, (h_fn(start, goal), counter, start))

    came_from   = {start: None}
    in_frontier = {start}
    visited     = set()
    events      = []
    nodes_visited = 0

    while heap:
        _, _, cur = heapq.heappop(heap)
        if cur in visited:
            continue
        in_frontier.discard(cur)
        visited.add(cur)
        nodes_visited += 1

        if cur != start and cur != goal:
            events.append(('expand', cur))

        if cur == goal:
            path = _reconstruct(came_from, goal)
            return path, events, nodes_visited, g_cost[goal], _elapsed_ms(t0)

        for nb in _neighbors(cells, rows, cols, cur):
            nb_cost = costs[nb[0]][nb[1]]
            new_g = g_cost[cur] + nb_cost
            if nb not in g_cost or new_g < g_cost[nb]:
                g_cost[nb]    = new_g
                f_score       = new_g + h_fn(nb, goal)
                came_from[nb] = cur
                counter      += 1
                heapq.heappush(heap, (f_score, counter, nb))
                in_frontier.add(nb)
                if nb not in visited and nb != goal:
                    events.append(('frontier', nb))

    return None, events, nodes_visited, 0, _elapsed_ms(t0)


# Algorithm registry — used by the App to look up by name
ALGORITHMS: dict = {
    'GBFS': run_gbfs,
    'A*':   run_astar,
}
