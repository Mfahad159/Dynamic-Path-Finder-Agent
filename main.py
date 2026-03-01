"""
Dynamic Pathfinding Agent
=========================
A Pygame-based implementation of an AI pathfinding agent.

Features:
  • Configurable grid size (rows × cols)
  • Interactive map editor  (left-click = place wall, right-click = remove)
  • Random maze generation  (user-defined obstacle density)
  • GBFS   – Greedy Best-First Search  f(n) = h(n)
  • A*     – A-Star Search             f(n) = g(n) + h(n)
  • Heuristics: Manhattan distance / Euclidean distance
  • Animated search visualisation (yellow frontier, blue visited, green path)
  • Real-time metrics dashboard (nodes visited, path cost, exec time ms)
  • Dynamic obstacle spawning + automatic re-planning
  • Full sidebar GUI with buttons

Controls
--------
  Left-click  : Place / remove wall (toggle)
  Right-click : Remove wall
  S           : Enter "Set Start" mode, then left-click a cell
  G           : Enter "Set Goal"  mode, then left-click a cell
  R           : Generate random map
  SPACE       : Run selected algorithm
  C           : Clear search overlay
  D           : Toggle dynamic obstacle mode
  +  /  -     : Increase / decrease random map density
  ESC         : Quit
"""

import pygame
import sys
import heapq
import math
import random
import time

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH   = 296       # pixels for the right-hand panel
FPS             = 60
ANIM_SPEED      = 4         # search events processed per frame
AGENT_DELAY_MS  = 90        # ms between agent steps
DYNAMIC_PROB    = 0.07      # probability of spawning a wall per agent step

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
C_BG            = ( 13,  13,  18)
C_GRID_LINE     = ( 36,  36,  48)
C_EMPTY         = ( 26,  26,  34)
C_WALL          = (  8,   8,  12)
C_WALL_EDGE     = ( 28,  28,  36)
C_START         = (  0, 195,  80)
C_GOAL          = (220,  50,  50)
C_FRONTIER      = (240, 200,   0)   # yellow
C_VISITED       = ( 55, 100, 215)   # blue
C_PATH          = (  0, 230, 115)   # bright green
C_AGENT         = (255, 170,   0)   # orange
C_NEW_WALL      = (200,  55,  55)   # dynamic wall flash
C_SIDEBAR_BG    = ( 18,  18,  26)
C_DIVIDER       = ( 42,  42,  58)
C_TEXT          = (215, 215, 228)
C_TEXT_DIM      = (105, 105, 128)
C_ACCENT        = ( 96, 146, 240)
C_BTN           = ( 36,  38,  54)
C_BTN_HOVER     = ( 55,  58,  80)
C_BTN_ACTIVE    = ( 66, 110, 205)
C_BTN_TEXT      = (215, 215, 230)
C_SUCCESS       = (  0, 200, 100)
C_WARNING       = (230, 160,  30)
C_ERROR         = (215,  55,  55)

# ─────────────────────────────────────────────────────────────────────────────
# CELL TYPES
# ─────────────────────────────────────────────────────────────────────────────
EMPTY    = 0
WALL     = 1
START    = 2
GOAL     = 3
FRONTIER = 4
VISITED  = 5
PATH     = 6

CELL_COLORS = {
    EMPTY:    C_EMPTY,
    WALL:     C_WALL,
    START:    C_START,
    GOAL:     C_GOAL,
    FRONTIER: C_FRONTIER,
    VISITED:  C_VISITED,
    PATH:     C_PATH,
}

# ─────────────────────────────────────────────────────────────────────────────
# HEURISTICS
# ─────────────────────────────────────────────────────────────────────────────
def manhattan(a: tuple, b: tuple) -> float:
    """Manhattan distance:  D = |x1−x2| + |y1−y2|"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def euclidean(a: tuple, b: tuple) -> float:
    """Euclidean distance:  D = sqrt((x1−x2)²+(y1−y2)²)"""
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

HEURISTICS = {'Manhattan': manhattan, 'Euclidean': euclidean}

# ─────────────────────────────────────────────────────────────────────────────
# NEIGHBOUR HELPER
# ─────────────────────────────────────────────────────────────────────────────
def get_neighbors(cells: list, rows: int, cols: int, node: tuple) -> list:
    """Return 4-connected walkable neighbours (not WALL) of node."""
    r, c = node
    result = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and cells[nr][nc] != WALL:
            result.append((nr, nc))
    return result

# ─────────────────────────────────────────────────────────────────────────────
# GREEDY BEST-FIRST SEARCH
# ─────────────────────────────────────────────────────────────────────────────
def run_gbfs(cells, rows, cols, start, goal, h_fn):
    """
    Greedy Best-First Search  —  f(n) = h(n)
    Returns:
        path          : list of (r,c) from start→goal, or None
        events        : list of ('frontier'|'expand', (r,c)) for animation
        nodes_visited : int
        path_cost     : int (steps)
        exec_ms       : float
    """
    t0   = time.perf_counter()
    heap = []
    counter = 0
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
            return path, events, nodes_visited, len(path) - 1, _ms(t0)

        for nb in get_neighbors(cells, rows, cols, cur):
            if nb not in visited and nb not in in_frontier:
                came_from[nb] = cur
                counter += 1
                heapq.heappush(heap, (h_fn(nb, goal), counter, nb))
                in_frontier.add(nb)
                if nb != goal:
                    events.append(('frontier', nb))

    return None, events, nodes_visited, 0, _ms(t0)

# ─────────────────────────────────────────────────────────────────────────────
# A* SEARCH
# ─────────────────────────────────────────────────────────────────────────────
def run_astar(cells, rows, cols, start, goal, h_fn):
    """
    A* Search  —  f(n) = g(n) + h(n)
    Returns same tuple as run_gbfs.
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
            return path, events, nodes_visited, g_cost[goal], _ms(t0)

        for nb in get_neighbors(cells, rows, cols, cur):
            new_g = g_cost[cur] + 1
            if nb not in g_cost or new_g < g_cost[nb]:
                g_cost[nb]  = new_g
                f_score     = new_g + h_fn(nb, goal)
                came_from[nb] = cur
                counter += 1
                heapq.heappush(heap, (f_score, counter, nb))
                in_frontier.add(nb)
                if nb not in visited and nb != goal:
                    events.append(('frontier', nb))

    return None, events, nodes_visited, 0, _ms(t0)

def _reconstruct(came_from: dict, goal: tuple) -> list:
    path, node = [], goal
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path

def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0

ALGORITHMS = {'GBFS': run_gbfs, 'A*': run_astar}

# ─────────────────────────────────────────────────────────────────────────────
# GRID
# ─────────────────────────────────────────────────────────────────────────────
class Grid:
    """Manages cell state and rendering."""

    def __init__(self, rows: int, cols: int, cell_size: int):
        self.rows      = rows
        self.cols      = cols
        self.cell_size = cell_size
        self.cells     = [[EMPTY] * cols for _ in range(rows)]
        self.start     = (0, 0)
        self.goal      = (rows - 1, cols - 1)
        self.cells[0][0]               = START
        self.cells[rows - 1][cols - 1] = GOAL
        self._flash_walls: set         = set()   # newly spawned dynamic walls

    # ── pixel helpers ────────────────────────────────────────────────────────
    def pixel_size(self) -> tuple:
        return self.cols * self.cell_size, self.rows * self.cell_size

    def cell_at(self, mx: int, my: int, ox: int = 0, oy: int = 0):
        """Return (row, col) for mouse pos, or None if out of bounds."""
        s = self.cell_size
        c, r = (mx - ox) // s, (my - oy) // s
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return r, c
        return None

    # ── wall editing ─────────────────────────────────────────────────────────
    def toggle_wall(self, r: int, c: int):
        if (r, c) in (self.start, self.goal):
            return
        self.cells[r][c] = WALL if self.cells[r][c] != WALL else EMPTY

    def place_wall(self, r: int, c: int):
        if (r, c) not in (self.start, self.goal) and self.cells[r][c] != WALL:
            self.cells[r][c] = WALL

    def remove_wall(self, r: int, c: int):
        if self.cells[r][c] == WALL:
            self.cells[r][c] = EMPTY

    # ── start / goal ─────────────────────────────────────────────────────────
    def set_start(self, r: int, c: int):
        if (r, c) == self.goal:
            return
        old_r, old_c = self.start
        if self.cells[old_r][old_c] == START:
            self.cells[old_r][old_c] = EMPTY
        self.start = (r, c)
        self.cells[r][c] = START

    def set_goal(self, r: int, c: int):
        if (r, c) == self.start:
            return
        old_r, old_c = self.goal
        if self.cells[old_r][old_c] == GOAL:
            self.cells[old_r][old_c] = EMPTY
        self.goal = (r, c)
        self.cells[r][c] = GOAL

    # ── search overlays ──────────────────────────────────────────────────────
    def reset_search(self):
        """Clear FRONTIER / VISITED / PATH cells; keep walls, start, goal."""
        self._flash_walls.clear()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c] in (FRONTIER, VISITED, PATH):
                    self.cells[r][c] = EMPTY

    def mark_frontier(self, node: tuple):
        r, c = node
        if (r, c) not in (self.start, self.goal) and self.cells[r][c] == EMPTY:
            self.cells[r][c] = FRONTIER

    def mark_visited(self, node: tuple):
        r, c = node
        if (r, c) not in (self.start, self.goal):
            self.cells[r][c] = VISITED

    def mark_path(self, path: list):
        for r, c in path:
            if (r, c) not in (self.start, self.goal):
                self.cells[r][c] = PATH

    def clear_path(self):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c] == PATH:
                    self.cells[r][c] = EMPTY

    # ── random generation ────────────────────────────────────────────────────
    def generate_random(self, density: float = 0.30):
        """Fill grid randomly. Start and goal are always kept clear."""
        self.reset_search()
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) == self.start:
                    self.cells[r][c] = START
                elif (r, c) == self.goal:
                    self.cells[r][c] = GOAL
                elif random.random() < density:
                    self.cells[r][c] = WALL
                else:
                    self.cells[r][c] = EMPTY

    # ── dynamic wall spawning ────────────────────────────────────────────────
    def spawn_dynamic_wall(self, exclude: set):
        """
        Attempt to spawn a wall on a random EMPTY cell not in `exclude`.
        Returns the spawned (r, c) or None.
        """
        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if self.cells[r][c] == EMPTY
            and (r, c) not in exclude
            and (r, c) not in (self.start, self.goal)
        ]
        if not candidates:
            return None
        r, c = random.choice(candidates)
        self.cells[r][c] = WALL
        self._flash_walls.add((r, c))
        return (r, c)

    # ── drawing ──────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, ox: int = 0, oy: int = 0,
             agent_pos=None):
        s   = self.cell_size
        fnt = None
        if s >= 18:
            fnt = pygame.font.SysFont("Segoe UI", max(9, s // 2 - 2), bold=True)

        for r in range(self.rows):
            for c in range(self.cols):
                x    = ox + c * s
                y    = oy + r * s
                rect = pygame.Rect(x, y, s, s)
                cell = self.cells[r][c]

                if agent_pos and (r, c) == agent_pos:
                    color = C_AGENT
                elif (r, c) in self._flash_walls:
                    color = C_NEW_WALL
                else:
                    color = CELL_COLORS.get(cell, C_EMPTY)

                pygame.draw.rect(surface, color, rect)

                # Wall gets a subtly lighter edge
                if cell == WALL and (r, c) not in self._flash_walls:
                    pygame.draw.rect(surface, C_WALL_EDGE, rect, 1)
                else:
                    pygame.draw.rect(surface, C_GRID_LINE, rect, 1)

                # Labels for start / goal
                if fnt and s >= 18:
                    if (r, c) == self.start:
                        lbl = fnt.render("S", True, (0, 0, 0))
                        surface.blit(lbl, lbl.get_rect(center=rect.center))
                    elif (r, c) == self.goal:
                        lbl = fnt.render("G", True, (255, 255, 255))
                        surface.blit(lbl, lbl.get_rect(center=rect.center))

                # Agent circle overlay
                if agent_pos and (r, c) == agent_pos and s >= 10:
                    cr = max(3, s // 3)
                    pygame.draw.circle(surface, (255, 220, 100), rect.center, cr)
                    pygame.draw.circle(surface, (200, 140, 0), rect.center, cr, 1)

# ─────────────────────────────────────────────────────────────────────────────
# BUTTON
# ─────────────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, x: int, y: int, w: int, h: int,
                 text: str, active: bool = False):
        self.rect   = pygame.Rect(x, y, w, h)
        self.text   = text
        self.active = active
        self._hover = False

    def update_hover(self, pos: tuple):
        self._hover = self.rect.collidepoint(pos)

    def clicked(self, event: pygame.event.Event) -> bool:
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.active:
            bg, fg = C_BTN_ACTIVE, (255, 255, 255)
        elif self._hover:
            bg, fg = C_BTN_HOVER, C_BTN_TEXT
        else:
            bg, fg = C_BTN, C_BTN_TEXT

        pygame.draw.rect(surface, bg,       self.rect, border_radius=6)
        pygame.draw.rect(surface, C_DIVIDER, self.rect, 1, border_radius=6)

        txt  = font.render(self.text, True, fg)
        trec = txt.get_rect(center=self.rect.center)
        surface.blit(txt, trec)

# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class App:
    # ── FSM states ───────────────────────────────────────────────────────────
    IDLE      = 'idle'
    ANIMATING = 'animating'
    MOVING    = 'moving'
    DYNAMIC   = 'dynamic'
    SET_START = 'set_start'
    SET_GOAL  = 'set_goal'

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols

        pygame.init()
        pygame.display.set_caption("Dynamic Pathfinding Agent")

        # ── window / grid sizing ─────────────────────────────────────────────
        info   = pygame.display.Info()
        max_w  = min(info.current_w - 40, 1600)
        max_h  = min(info.current_h - 80, 940)
        cs     = max(8, min(80,
                            min((max_w - SIDEBAR_WIDTH) // cols, max_h // rows)))
        gw, gh = cols * cs, rows * cs
        win_w  = gw + SIDEBAR_WIDTH
        win_h  = max(gh, 560)

        self.screen  = pygame.display.set_mode((win_w, win_h),
                                               pygame.RESIZABLE)
        self.clock   = pygame.time.Clock()
        self.grid    = Grid(rows, cols, cs)
        self.grid_ox = 0
        self.grid_oy = max(0, (win_h - gh) // 2)

        # ── fonts ─────────────────────────────────────────────────────────────
        self.f_title = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.f_med   = pygame.font.SysFont("Segoe UI", 14)
        self.f_sm    = pygame.font.SysFont("Segoe UI", 12)
        self.f_btn   = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.f_xs    = pygame.font.SysFont("Segoe UI", 11)

        # ── state ─────────────────────────────────────────────────────────────
        self.state         = self.IDLE
        self.algo_name     = 'A*'
        self.heur_name     = 'Manhattan'
        self.density       = 0.30
        self.dynamic_on    = False

        # search animation
        self.events_list   = []
        self.anim_idx      = 0
        self.path          = []
        self.agent_idx     = 0
        self.agent_pos     = None

        # metrics
        self.nodes_visited = 0
        self.path_cost     = 0
        self.exec_ms       = 0.0
        self.replans       = 0

        # status bar
        self.status_msg    = ("Ready — draw walls or click Generate Map, "
                              "then press RUN or SPACE.")
        self.status_color  = C_TEXT_DIM

        # timers
        self.last_agent_t  = 0

        # ── build sidebar buttons ─────────────────────────────────────────────
        self._build_buttons(win_w)

    # ── button construction ───────────────────────────────────────────────────
    def _build_buttons(self, win_w: int):
        sx  = win_w - SIDEBAR_WIDTH + 10
        fw  = SIDEBAR_WIDTH - 20
        bh  = 28
        hw  = (fw - 4) // 2

        # Algorithm
        self.btn_gbfs  = Button(sx, 0, hw, bh, "GBFS",       self.algo_name == 'GBFS')
        self.btn_astar = Button(sx + hw + 4, 0, hw, bh, "A*", self.algo_name == 'A*')
        # Heuristic
        self.btn_manh  = Button(sx, 0, hw, bh, "Manhattan",  self.heur_name == 'Manhattan')
        self.btn_eucl  = Button(sx + hw + 4, 0, hw, bh, "Euclidean", self.heur_name == 'Euclidean')
        # Actions
        self.btn_gen   = Button(sx, 0, fw, bh, "⚙  Generate Map")
        self.btn_run   = Button(sx, 0, fw, bh, "▶  Run Algorithm")
        self.btn_clear = Button(sx, 0, fw, bh, "✕  Clear Search")
        self.btn_ss    = Button(sx, 0, hw, bh, "Set Start")
        self.btn_sg    = Button(sx + hw + 4, 0, hw, bh, "Set Goal")
        self.btn_dyn   = Button(sx, 0, fw, bh, "⚡  Dynamic Mode: OFF")

        self.all_buttons = [
            self.btn_gbfs, self.btn_astar,
            self.btn_manh, self.btn_eucl,
            self.btn_gen, self.btn_run, self.btn_clear,
            self.btn_ss, self.btn_sg, self.btn_dyn,
        ]

    # ─────────────────────────────────────────────────────────────────────────
    def run(self):
        while True:
            self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()

    # ── events ────────────────────────────────────────────────────────────────
    def _handle_events(self):
        mp = pygame.mouse.get_pos()
        for btn in self.all_buttons:
            btn.update_hover(mp)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # ── keyboard ─────────────────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                elif event.key == pygame.K_SPACE:
                    self._run_algorithm()
                elif event.key == pygame.K_r:
                    self._generate_map()
                elif event.key == pygame.K_c:
                    self._clear_search()
                elif event.key == pygame.K_d:
                    self._toggle_dynamic()
                elif event.key == pygame.K_s:
                    self._enter_set_mode(self.SET_START)
                elif event.key == pygame.K_g:
                    self._enter_set_mode(self.SET_GOAL)
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    self.density = min(0.80, round(self.density + 0.05, 2))
                    self._set_status(f"Density → {int(self.density*100)}%", C_TEXT_DIM)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self.density = max(0.05, round(self.density - 0.05, 2))
                    self._set_status(f"Density → {int(self.density*100)}%", C_TEXT_DIM)

            # ── mouse ────────────────────────────────────────────────────────
            if event.type == pygame.MOUSEBUTTONDOWN:
                cell = self.grid.cell_at(*event.pos, self.grid_ox, self.grid_oy)
                if cell:
                    r, c = cell
                    if self.state == self.SET_START:
                        self.grid.set_start(r, c)
                        self.state = self.IDLE
                        self._set_status(f"Start → ({r},{c})", C_SUCCESS)
                    elif self.state == self.SET_GOAL:
                        self.grid.set_goal(r, c)
                        self.state = self.IDLE
                        self._set_status(f"Goal → ({r},{c})", C_SUCCESS)
                    elif self.state == self.IDLE:
                        if event.button == 1:
                            self.grid.toggle_wall(r, c)
                        elif event.button == 3:
                            self.grid.remove_wall(r, c)

            # ── mouse drag (paint walls) ─────────────────────────────────────
            if event.type == pygame.MOUSEMOTION and self.state == self.IDLE:
                cell = self.grid.cell_at(*event.pos, self.grid_ox, self.grid_oy)
                if cell:
                    r, c = cell
                    if pygame.mouse.get_pressed()[0]:
                        self.grid.place_wall(r, c)
                    elif pygame.mouse.get_pressed()[2]:
                        self.grid.remove_wall(r, c)

            # ── window resize ─────────────────────────────────────────────────
            if event.type == pygame.VIDEORESIZE:
                gw, gh = self.grid.pixel_size()
                self.grid_oy = max(0, (event.h - gh) // 2)

            # ── buttons ──────────────────────────────────────────────────────
            for btn in self.all_buttons:
                if btn.clicked(event):
                    self._on_button(btn)

    def _on_button(self, btn: Button):
        g = btn
        if btn is self.btn_gbfs:
            self.algo_name, self.btn_gbfs.active, self.btn_astar.active = 'GBFS', True, False
        elif btn is self.btn_astar:
            self.algo_name, self.btn_astar.active, self.btn_gbfs.active = 'A*',   True, False
        elif btn is self.btn_manh:
            self.heur_name, self.btn_manh.active, self.btn_eucl.active = 'Manhattan', True, False
        elif btn is self.btn_eucl:
            self.heur_name, self.btn_eucl.active, self.btn_manh.active = 'Euclidean', True, False
        elif btn is self.btn_gen:
            self._generate_map()
        elif btn is self.btn_run:
            self._run_algorithm()
        elif btn is self.btn_clear:
            self._clear_search()
        elif btn is self.btn_ss:
            self._enter_set_mode(self.SET_START)
        elif btn is self.btn_sg:
            self._enter_set_mode(self.SET_GOAL)
        elif btn is self.btn_dyn:
            self._toggle_dynamic()

    # ── state transitions ─────────────────────────────────────────────────────
    def _enter_set_mode(self, mode):
        if self.state in (self.ANIMATING, self.MOVING, self.DYNAMIC):
            return
        self.state = mode
        label = "Start" if mode == self.SET_START else "Goal"
        self._set_status(f"Click a cell to place the {label} node.", C_WARNING)

    def _generate_map(self):
        if self.state in (self.ANIMATING, self.MOVING, self.DYNAMIC):
            return
        self.grid.generate_random(self.density)
        self._reset_metrics()
        self.state = self.IDLE
        self._set_status(
            f"Random map generated ({int(self.density*100)}% walls). "
            "Press RUN or SPACE.", C_TEXT_DIM)

    def _run_algorithm(self):
        if self.state in (self.ANIMATING, self.MOVING, self.DYNAMIC):
            return
        self.grid.reset_search()
        self._reset_metrics()
        algo = ALGORITHMS[self.algo_name]
        h_fn = HEURISTICS[self.heur_name]
        g    = self.grid
        path, evts, nv, pc, em = algo(
            g.cells, g.rows, g.cols, g.start, g.goal, h_fn)

        self.events_list   = evts
        self.anim_idx      = 0
        self.nodes_visited = nv
        self.path_cost     = pc
        self.exec_ms       = em
        self.path          = path or []
        self.agent_pos     = None
        self.state         = self.ANIMATING

        if path:
            self._set_status(
                f"Path found! Visualising… | Nodes: {nv} | "
                f"Cost: {pc} | Time: {em:.2f}ms", C_SUCCESS)
        else:
            self._set_status(
                "No path found — all routes are blocked!", C_ERROR)

    def _clear_search(self):
        self.grid.reset_search()
        self._reset_metrics()
        self.state     = self.IDLE
        self.agent_pos = None
        self.path      = []
        self.events_list = []
        self.dynamic_on = False
        self.btn_dyn.active = False
        self.btn_dyn.text = "⚡  Dynamic Mode: OFF"
        self._set_status("Search cleared. Ready.", C_TEXT_DIM)

    def _toggle_dynamic(self):
        if self.state == self.MOVING:
            self.dynamic_on = True
            self.state      = self.DYNAMIC
            self.btn_dyn.active = True
            self.btn_dyn.text = "⚡  Dynamic Mode: ON"
            self._set_status("Dynamic mode ON — walls may spawn!", C_WARNING)
        elif self.state == self.DYNAMIC:
            self.dynamic_on = False
            self.state      = self.MOVING
            self.btn_dyn.active = False
            self.btn_dyn.text = "⚡  Dynamic Mode: OFF"
            self._set_status("Dynamic mode OFF.", C_TEXT_DIM)
        else:
            self.dynamic_on = not self.dynamic_on
            self.btn_dyn.active = self.dynamic_on
            self.btn_dyn.text = (
                "⚡  Dynamic Mode: ON" if self.dynamic_on
                else "⚡  Dynamic Mode: OFF")
            self._set_status(
                "Dynamic mode will activate when agent starts moving.",
                C_TEXT_DIM)

    # ── update loop ───────────────────────────────────────────────────────────
    def _update(self):
        now = pygame.time.get_ticks()
        g   = self.grid

        # ── search animation ──────────────────────────────────────────────────
        if self.state == self.ANIMATING:
            for _ in range(ANIM_SPEED):
                if self.anim_idx < len(self.events_list):
                    ev_type, ev_cell = self.events_list[self.anim_idx]
                    if ev_type == 'frontier':
                        g.mark_frontier(ev_cell)
                    else:
                        g.mark_visited(ev_cell)
                    self.anim_idx += 1
                else:
                    # animation finished
                    if self.path:
                        g.mark_path(self.path)
                        self.agent_pos = self.path[0]
                        self.agent_idx = 0
                        self.state     = self.DYNAMIC if self.dynamic_on else self.MOVING
                        self._set_status(
                            f"Agent moving… | Cost: {self.path_cost} | "
                            f"Nodes: {self.nodes_visited} | "
                            f"Time: {self.exec_ms:.2f}ms", C_SUCCESS)
                    else:
                        self.state = self.IDLE
                    break

        # ── agent movement (MOVING or DYNAMIC) ────────────────────────────────
        elif self.state in (self.MOVING, self.DYNAMIC):
            if now - self.last_agent_t >= AGENT_DELAY_MS:
                self.last_agent_t = now
                g._flash_walls.clear()

                if self.agent_idx < len(self.path) - 1:
                    # Dynamic: maybe spawn a wall
                    if self.state == self.DYNAMIC and random.random() < DYNAMIC_PROB:
                        remaining_set = set(self.path[self.agent_idx + 1:])
                        spawned = g.spawn_dynamic_wall(remaining_set)
                        if spawned and spawned in remaining_set:
                            # Wall landed on current path → re-plan
                            self._replan()
                            return

                    self.agent_idx += 1
                    self.agent_pos  = self.path[self.agent_idx]
                else:
                    # Reached goal
                    self.agent_pos  = g.goal
                    self.state      = self.IDLE
                    self.dynamic_on = False
                    self.btn_dyn.active = False
                    self.btn_dyn.text   = "⚡  Dynamic Mode: OFF"
                    self._set_status(
                        f"✓ Goal reached! | Cost: {self.path_cost} | "
                        f"Nodes: {self.nodes_visited} | Re-plans: {self.replans} | "
                        f"Time: {self.exec_ms:.2f}ms", C_SUCCESS)

    def _replan(self):
        """Re-compute path from agent's current position after a blocked cell."""
        g       = self.grid
        algo    = ALGORITHMS[self.algo_name]
        h_fn    = HEURISTICS[self.heur_name]
        current = self.agent_pos

        # Clear old path cells
        g.clear_path()

        path, evts, nv, pc, em = algo(
            g.cells, g.rows, g.cols, current, g.goal, h_fn)

        self.nodes_visited += nv
        self.exec_ms       += em
        self.replans       += 1

        if path:
            self.path       = path
            self.path_cost  = len(path) - 1
            self.agent_idx  = 0
            g.mark_path(path)
            self._set_status(
                f"Re-planning #{self.replans}  — new cost: {self.path_cost} | "
                f"Total nodes: {self.nodes_visited} | "
                f"Time: {self.exec_ms:.2f}ms", C_WARNING)
        else:
            self.state      = self.IDLE
            self.dynamic_on = False
            self._set_status(
                "Agent stuck — no path after re-plan!", C_ERROR)

    # ── draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        win_w, win_h = self.screen.get_size()
        gw, gh       = self.grid.pixel_size()
        self.grid_oy = max(0, (win_h - gh) // 2)

        self.screen.fill(C_BG)
        self.grid.draw(self.screen, self.grid_ox, self.grid_oy, self.agent_pos)
        self._draw_sidebar(win_w, win_h)
        pygame.display.flip()

    def _draw_sidebar(self, win_w: int, win_h: int):
        sx      = win_w - SIDEBAR_WIDTH
        surface = self.screen
        fw      = SIDEBAR_WIDTH - 20
        hw      = (fw - 4) // 2
        bx      = sx + 10
        by      = 12

        # Panel background + left border
        pygame.draw.rect(surface, C_SIDEBAR_BG, (sx, 0, SIDEBAR_WIDTH, win_h))
        pygame.draw.line(surface, C_ACCENT, (sx, 0), (sx, win_h), 2)

        # ── Title ─────────────────────────────────────────────────────────────
        t = self.f_title.render("Pathfinding Agent", True, C_ACCENT)
        surface.blit(t, (bx, by)); by += t.get_height() + 2
        s = self.f_sm.render("Dynamic Grid Navigation  •  Pygame", True, C_TEXT_DIM)
        surface.blit(s, (bx, by)); by += s.get_height() + 8
        self._div(surface, sx, by); by += 10

        # ── Algorithm ─────────────────────────────────────────────────────────
        self._label(surface, bx, by, "ALGORITHM"); by += 18
        self.btn_gbfs.rect  = pygame.Rect(bx, by, hw, 28)
        self.btn_astar.rect = pygame.Rect(bx + hw + 4, by, hw, 28)
        self.btn_gbfs.draw(surface, self.f_btn)
        self.btn_astar.draw(surface, self.f_btn)
        by += 34

        # ── Heuristic ─────────────────────────────────────────────────────────
        self._label(surface, bx, by, "HEURISTIC"); by += 18
        self.btn_manh.rect = pygame.Rect(bx, by, hw, 28)
        self.btn_eucl.rect = pygame.Rect(bx + hw + 4, by, hw, 28)
        self.btn_manh.draw(surface, self.f_btn)
        self.btn_eucl.draw(surface, self.f_btn)
        by += 34

        self._div(surface, sx, by); by += 10

        # ── Action buttons ────────────────────────────────────────────────────
        for btn in (self.btn_gen, self.btn_run, self.btn_clear):
            btn.rect = pygame.Rect(bx, by, fw, 28)
            btn.draw(surface, self.f_btn)
            by += 32

        self.btn_ss.rect = pygame.Rect(bx, by, hw, 28)
        self.btn_sg.rect = pygame.Rect(bx + hw + 4, by, hw, 28)
        self.btn_ss.draw(surface, self.f_btn)
        self.btn_sg.draw(surface, self.f_btn)
        by += 32

        self.btn_dyn.rect = pygame.Rect(bx, by, fw, 28)
        self.btn_dyn.draw(surface, self.f_btn)
        by += 36

        self._div(surface, sx, by); by += 10

        # ── Metrics ───────────────────────────────────────────────────────────
        self._label(surface, bx, by, "METRICS"); by += 18

        metrics = [
            ("Nodes Visited",  str(self.nodes_visited)),
            ("Path Cost",      str(self.path_cost)),
            ("Exec Time",      f"{self.exec_ms:.2f} ms"),
            ("Re-Plans",       str(self.replans)),
            ("Algorithm",      self.algo_name),
            ("Heuristic",      self.heur_name),
            ("Grid Size",      f"{self.grid.rows} × {self.grid.cols}"),
            ("Density",        f"{int(self.density * 100)}%"),
        ]
        for lbl, val in metrics:
            ls = self.f_sm.render(lbl,  True, C_TEXT_DIM)
            vs = self.f_med.render(val, True, C_TEXT)
            surface.blit(ls, (bx, by))
            surface.blit(vs, (sx + SIDEBAR_WIDTH - vs.get_width() - 10, by))
            by += max(ls.get_height(), vs.get_height()) + 4

        self._div(surface, sx, by); by += 10

        # ── Legend ────────────────────────────────────────────────────────────
        self._label(surface, bx, by, "LEGEND"); by += 18
        legend = [
            (C_START,    "Start node"),
            (C_GOAL,     "Goal node"),
            (C_WALL,     "Wall / obstacle"),
            (C_FRONTIER, "Frontier (queue)"),
            (C_VISITED,  "Visited / expanded"),
            (C_PATH,     "Final path"),
            (C_AGENT,    "Agent"),
            (C_NEW_WALL, "Dynamic wall spawn"),
        ]
        for col, name in legend:
            pygame.draw.rect(surface, col,      pygame.Rect(bx, by + 2, 12, 12),
                             border_radius=2)
            pygame.draw.rect(surface, C_DIVIDER, pygame.Rect(bx, by + 2, 12, 12),
                             1, border_radius=2)
            ns = self.f_sm.render(name, True, C_TEXT_DIM)
            surface.blit(ns, (bx + 16, by))
            by += ns.get_height() + 3

        self._div(surface, sx, by); by += 8

        # ── Controls hint ─────────────────────────────────────────────────────
        self._label(surface, bx, by, "CONTROLS"); by += 18
        hints = [
            "LClick / drag  : place wall",
            "RClick / drag  : remove wall",
            "S  →  set Start  |  G  →  set Goal",
            "R  →  random map  |  C  →  clear",
            "+/-  →  adjust density",
            "SPACE  →  run  |  D  →  dynamic",
            "ESC  →  quit",
        ]
        for h in hints:
            hs = self.f_xs.render(h, True, C_TEXT_DIM)
            surface.blit(hs, (bx, by)); by += hs.get_height() + 2

        # ── Status bar ────────────────────────────────────────────────────────
        status_y = max(by + 8, win_h - 56)
        self._div(surface, sx, status_y); status_y += 8
        self._wrap_text(surface, self.status_msg, self.status_color,
                        bx, status_y, fw)

        # ── State badge ───────────────────────────────────────────────────────
        badge_color = {
            self.IDLE:      C_TEXT_DIM,
            self.ANIMATING: C_FRONTIER,
            self.MOVING:    C_PATH,
            self.DYNAMIC:   C_WARNING,
            self.SET_START: C_START,
            self.SET_GOAL:  C_GOAL,
        }.get(self.state, C_TEXT_DIM)
        badge_text = {
            self.IDLE:      "● IDLE",
            self.ANIMATING: "● SEARCHING",
            self.MOVING:    "● MOVING",
            self.DYNAMIC:   "⚡ DYNAMIC",
            self.SET_START: "● SET START",
            self.SET_GOAL:  "● SET GOAL",
        }.get(self.state, self.state.upper())
        bs = self.f_sm.render(badge_text, True, badge_color)
        surface.blit(bs, (sx + SIDEBAR_WIDTH - bs.get_width() - 8, 8))

    # ── sidebar helpers ───────────────────────────────────────────────────────
    def _div(self, surface, sx, y):
        pygame.draw.line(surface, C_DIVIDER,
                         (sx + 6, y), (sx + SIDEBAR_WIDTH - 6, y), 1)

    def _label(self, surface, x, y, text):
        s = self.f_xs.render(text, True, C_TEXT_DIM)
        surface.blit(s, (x, y))

    def _wrap_text(self, surface, text, color, x, y, max_w):
        words, line = text.split(), ""
        for word in words:
            test = (line + " " + word).strip()
            if self.f_sm.size(test)[0] > max_w and line:
                surface.blit(self.f_sm.render(line, True, color), (x, y))
                y += self.f_sm.get_height() + 2
                line = word
            else:
                line = test
        if line:
            surface.blit(self.f_sm.render(line, True, color), (x, y))

    def _set_status(self, msg: str, color):
        self.status_msg   = msg
        self.status_color = color

    def _reset_metrics(self):
        self.nodes_visited = 0
        self.path_cost     = 0
        self.exec_ms       = 0.0
        self.replans       = 0

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def get_grid_dimensions() -> tuple:
    print("\n╔════════════════════════════════════╗")
    print("║   Dynamic Pathfinding Agent  v1.0  ║")
    print("╚════════════════════════════════════╝\n")
    while True:
        try:
            rows = int(input("  Enter number of ROWS    (5 – 60): ").strip())
            cols = int(input("  Enter number of COLUMNS (5 – 60): ").strip())
            if 5 <= rows <= 60 and 5 <= cols <= 60:
                return rows, cols
            print("  ⚠  Values must be between 5 and 60.\n")
        except ValueError:
            print("  ⚠  Please enter whole numbers.\n")


def main():
    rows, cols = get_grid_dimensions()
    print(f"\n  ✓ Launching {rows}×{cols} grid…")
    App(rows, cols).run()


if __name__ == "__main__":
    main()
