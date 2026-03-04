"""
grid.py
=======
Grid class — manages cell state and all grid rendering.

Cell types are defined in constants.py.
"""

import random
import pygame

from constants import (
    EMPTY, WALL, START, GOAL, FRONTIER, VISITED, PATH,
    CELL_COLORS, C_GRID_LINE, C_WALL_EDGE, C_AGENT, C_NEW_WALL,
)


class Grid:
    """
    Holds a 2-D array of cell states and knows how to draw itself.

    Attributes
    ----------
    rows, cols  : int      — grid dimensions
    cell_size   : int      — pixel size of one cell
    cells       : list     — 2-D array of cell type IDs
    start, goal : (r, c)   — fixed start and goal positions
    """

    def __init__(self, rows: int, cols: int, cell_size: int):
        self.rows      = rows
        self.cols      = cols
        self.cell_size = cell_size
        self.cells     = [[EMPTY] * cols for _ in range(rows)]
        self.costs     = [[random.randint(1, 10) for _ in range(cols)] for _ in range(rows)]
        self.start     = (0, 0)
        self.goal      = (rows - 1, cols - 1)
        self.cells[0][0]               = START
        self.cells[rows - 1][cols - 1] = GOAL
        self._flash_walls: set         = set()   # newly spawned dynamic walls

    # ── pixel helpers ─────────────────────────────────────────────────────────

    def pixel_size(self) -> tuple:
        """Return (width, height) of the grid in pixels."""
        return self.cols * self.cell_size, self.rows * self.cell_size

    def cell_at(self, mx: int, my: int, ox: int = 0, oy: int = 0):
        """
        Convert a mouse position to (row, col).
        Returns None if the position is outside the grid.
        """
        s = self.cell_size
        c = (mx - ox) // s
        r = (my - oy) // s
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return r, c
        return None

    # ── wall editing ──────────────────────────────────────────────────────────

    def toggle_wall(self, r: int, c: int):
        """Toggle a cell between EMPTY and WALL (ignores start/goal)."""
        if (r, c) in (self.start, self.goal):
            return
        self.cells[r][c] = WALL if self.cells[r][c] != WALL else EMPTY

    def place_wall(self, r: int, c: int):
        """Set a cell to WALL (drag painting); ignores start/goal."""
        if (r, c) not in (self.start, self.goal) and self.cells[r][c] != WALL:
            self.cells[r][c] = WALL

    def remove_wall(self, r: int, c: int):
        """Remove a WALL cell, restoring it to EMPTY."""
        if self.cells[r][c] == WALL:
            self.cells[r][c] = EMPTY

    # ── start / goal manipulation ─────────────────────────────────────────────

    def set_start(self, r: int, c: int):
        """Relocate the start node to (r, c)."""
        if (r, c) == self.goal:
            return
        old_r, old_c = self.start
        if self.cells[old_r][old_c] == START:
            self.cells[old_r][old_c] = EMPTY
        self.start = (r, c)
        self.cells[r][c] = START

    def set_goal(self, r: int, c: int):
        """Relocate the goal node to (r, c)."""
        if (r, c) == self.start:
            return
        old_r, old_c = self.goal
        if self.cells[old_r][old_c] == GOAL:
            self.cells[old_r][old_c] = EMPTY
        self.goal = (r, c)
        self.cells[r][c] = GOAL

    # ── search overlays ───────────────────────────────────────────────────────

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
        """Remove PATH markers only (used during re-planning)."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c] == PATH:
                    self.cells[r][c] = EMPTY

    # ── random generation ─────────────────────────────────────────────────────

    def generate_random(self, density: float = 0.30):
        """
        Fill the grid randomly.
        Each cell becomes WALL with probability *density*.
        Start and goal are always kept clear.
        Regenerate random costs for all cells.
        """
        self.reset_search()
        # Regenerate random costs for each cell
        self.costs = [[random.randint(1, 10) for _ in range(self.cols)] for _ in range(self.rows)]
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

    # ── dynamic wall spawning ─────────────────────────────────────────────────

    def spawn_dynamic_wall(self, exclude: set):
        """
        Attempt to place a wall on a random EMPTY cell not in *exclude*.

        Parameters
        ----------
        exclude : set of (r, c) — cells that must stay clear (current path)

        Returns
        -------
        (r, c) of the spawned wall, or None if no candidate exists.
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

    # ── rendering ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface,
             ox: int = 0, oy: int = 0,
             agent_pos=None):
        """
        Render all grid cells onto *surface*.

        Parameters
        ----------
        ox, oy     : pixel offset of the grid's top-left corner
        agent_pos  : (r, c) of the agent, or None
        """
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

                # Colour priority: agent > flash wall > normal
                if agent_pos and (r, c) == agent_pos:
                    color = C_AGENT
                elif (r, c) in self._flash_walls:
                    color = C_NEW_WALL
                else:
                    color = CELL_COLORS.get(cell, EMPTY)

                pygame.draw.rect(surface, color, rect)

                # Border
                border_color = C_WALL_EDGE if cell == WALL else C_GRID_LINE
                pygame.draw.rect(surface, border_color, rect, 1)

                # S / G labels when cells are large enough
                if fnt:
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
                    pygame.draw.circle(surface, (200, 140, 0),   rect.center, cr, 1)
