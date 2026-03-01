"""
Dynamic Pathfinding Agent — Step 1
====================================
Pygame window with a configurable grid.

Controls (Step 1):
  - Grid dimensions are set via console input at startup
  - Window shows a white grid with black border lines
  - Press ESC or close window to quit
"""

import pygame
import sys

# ─────────────────────────── CONSTANTS ───────────────────────────
SIDEBAR_WIDTH   = 260          # pixels reserved on the right for controls / metrics
CELL_MIN_SIZE   = 10           # minimum cell size in pixels
CELL_MAX_SIZE   = 60           # maximum cell size in pixels
FPS             = 60

# Colour palette
C_BG            = (18,  18,  18)   # window background
C_GRID_LINE     = (50,  50,  50)   # grid line colour
C_CELL_EMPTY    = (30,  30,  30)   # empty cell fill
C_CELL_WALL     = (15,  15,  15)   # wall (placeholder — unused in step 1)
C_START         = (0,  200,  80)   # start node
C_GOAL          = (220,  50,  50)  # goal node
C_SIDEBAR_BG    = (24,  24,  28)   # sidebar background
C_TEXT          = (220, 220, 220)  # general text
C_ACCENT        = (100, 149, 237)  # cornflower-blue accent


# ─────────────────────────── INPUT HELPERS ───────────────────────
def get_grid_dimensions():
    """Ask the user for grid size in the console."""
    print("\n╔══════════════════════════════════╗")
    print("║  Dynamic Pathfinding Agent       ║")
    print("╚══════════════════════════════════╝\n")
    while True:
        try:
            rows = int(input("  Enter number of ROWS    (5–60): ").strip())
            cols = int(input("  Enter number of COLUMNS (5–60): ").strip())
            if 5 <= rows <= 60 and 5 <= cols <= 60:
                return rows, cols
            print("  ⚠  Please enter values between 5 and 60.\n")
        except ValueError:
            print("  ⚠  Invalid input — please enter integers.\n")


def compute_cell_size(rows: int, cols: int, win_w: int, win_h: int) -> int:
    """Compute the largest cell size that fits the grid inside the canvas area."""
    canvas_w = win_w - SIDEBAR_WIDTH
    size = min(canvas_w // cols, win_h // rows)
    return max(CELL_MIN_SIZE, min(size, CELL_MAX_SIZE))


# ─────────────────────────── GRID CLASS ──────────────────────────
class Grid:
    """Holds cell state and knows how to draw itself."""

    EMPTY = 0
    WALL  = 1
    START = 2
    GOAL  = 3

    def __init__(self, rows: int, cols: int, cell_size: int):
        self.rows      = rows
        self.cols      = cols
        self.cell_size = cell_size
        self.cells     = [[self.EMPTY] * cols for _ in range(rows)]

        # Default start = top-left corner, goal = bottom-right corner
        self.start = (0, 0)
        self.goal  = (rows - 1, cols - 1)
        self.cells[self.start[0]][self.start[1]] = self.START
        self.cells[self.goal[0]][self.goal[1]]   = self.GOAL

    # ── drawing ──────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0):
        s = self.cell_size
        for r in range(self.rows):
            for c in range(self.cols):
                x = offset_x + c * s
                y = offset_y + r * s
                rect = pygame.Rect(x, y, s, s)
                state = self.cells[r][c]

                # Fill colour
                if state == self.WALL:
                    colour = C_CELL_WALL
                elif state == self.START:
                    colour = C_START
                elif state == self.GOAL:
                    colour = C_GOAL
                else:
                    colour = C_CELL_EMPTY

                pygame.draw.rect(surface, colour, rect)
                # Grid line border
                pygame.draw.rect(surface, C_GRID_LINE, rect, 1)

    def grid_pixel_size(self) -> tuple[int, int]:
        """Return (width, height) of the grid in pixels."""
        return self.cols * self.cell_size, self.rows * self.cell_size


# ─────────────────────────── SIDEBAR ─────────────────────────────
def draw_sidebar(surface: pygame.Surface, font_big, font_med, font_sm,
                 grid: Grid, offset_x: int):
    """Render the right-hand sidebar with title and grid info."""
    # Background panel
    sidebar_rect = pygame.Rect(offset_x, 0, SIDEBAR_WIDTH, surface.get_height())
    pygame.draw.rect(surface, C_SIDEBAR_BG, sidebar_rect)
    pygame.draw.line(surface, C_ACCENT,
                     (offset_x, 0), (offset_x, surface.get_height()), 2)

    x = offset_x + 16
    y = 20

    # Title
    title = font_big.render("Pathfinding Agent", True, C_ACCENT)
    surface.blit(title, (x, y));  y += title.get_height() + 4
    sub = font_sm.render("Dynamic Grid Navigation", True, (130, 130, 160))
    surface.blit(sub, (x, y));    y += sub.get_height() + 20

    # Divider
    pygame.draw.line(surface, C_GRID_LINE,
                     (offset_x + 10, y), (offset_x + SIDEBAR_WIDTH - 10, y), 1)
    y += 14

    # Grid info
    info_lines = [
        ("Grid Size",  f"{grid.rows} × {grid.cols}"),
        ("Cell Size",  f"{grid.cell_size} px"),
        ("Start Node", f"({grid.start[0]}, {grid.start[1]})"),
        ("Goal Node",  f"({grid.goal[0]}, {grid.goal[1]})"),
    ]
    for label, value in info_lines:
        lbl_surf = font_sm.render(label, True, (130, 130, 160))
        val_surf = font_med.render(value, True, C_TEXT)
        surface.blit(lbl_surf, (x, y));          y += lbl_surf.get_height() + 2
        surface.blit(val_surf, (x + 10, y));     y += val_surf.get_height() + 12

    # Divider
    pygame.draw.line(surface, C_GRID_LINE,
                     (offset_x + 10, y), (offset_x + SIDEBAR_WIDTH - 10, y), 1)
    y += 14

    # Hint
    hint_lines = [
        "── Step 1 ──",
        "Grid is rendering.",
        "Close window or",
        "press ESC to quit.",
    ]
    for line in hint_lines:
        hint = font_sm.render(line, True, (100, 100, 120))
        surface.blit(hint, (x, y));  y += hint.get_height() + 4


# ─────────────────────────── MAIN ────────────────────────────────
def main():
    rows, cols = get_grid_dimensions()

    pygame.init()
    pygame.display.set_caption("Dynamic Pathfinding Agent — Step 1")

    # Set a sensible initial window size, then recompute cell size
    info        = pygame.display.Info()
    win_w       = min(info.current_w - 40,  1600)
    win_h       = min(info.current_h - 80,  900)

    cell_size   = compute_cell_size(rows, cols, win_w, win_h)
    grid_w      = cols * cell_size
    grid_h      = rows * cell_size

    # Resize window to fit the grid exactly + sidebar
    win_w       = grid_w + SIDEBAR_WIDTH
    win_h       = max(grid_h, 480)          # keep at least 480 px tall
    screen      = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)

    # Fonts
    font_big    = pygame.font.SysFont("Segoe UI", 18, bold=True)
    font_med    = pygame.font.SysFont("Segoe UI", 15)
    font_sm     = pygame.font.SysFont("Segoe UI", 13)

    grid        = Grid(rows, cols, cell_size)
    clock       = pygame.time.Clock()

    print(f"\n  ✓ Window opened — {rows}×{cols} grid, cell size {cell_size}px")
    print("  Press ESC or close the window to exit.\n")

    running     = True
    while running:
        # ── Events ───────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # ── Draw ─────────────────────────────────────────────────
        screen.fill(C_BG)

        # Grid offset: centre the grid vertically in the canvas area
        offset_x = 0
        offset_y = max(0, (win_h - grid_h) // 2)

        grid.draw(screen, offset_x, offset_y)
        draw_sidebar(screen, font_big, font_med, font_sm, grid, grid_w)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
