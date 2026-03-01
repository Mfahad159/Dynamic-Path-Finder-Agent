"""
constants.py
============
All shared constants: colours, cell-type IDs, and timing values.
"""

# ── Window / layout ──────────────────────────────────────────────────────────
SIDEBAR_WIDTH  = 296    # px reserved for the right-hand panel
FPS            = 60

# ── Search animation ─────────────────────────────────────────────────────────
ANIM_SPEED     = 1      # search events replayed per frame  (1 = one node at a time)
AGENT_DELAY_MS = 350    # ms between agent steps
DYNAMIC_PROB   = 0.07   # probability of spawning a wall per agent step

# ── Colour palette ───────────────────────────────────────────────────────────
C_BG         = ( 13,  13,  18)
C_GRID_LINE  = ( 36,  36,  48)
C_EMPTY      = ( 26,  26,  34)
C_WALL       = (  8,   8,  12)
C_WALL_EDGE  = ( 28,  28,  36)
C_START      = (  0, 195,  80)
C_GOAL       = (220,  50,  50)
C_FRONTIER   = (240, 200,   0)   # yellow
C_VISITED    = ( 55, 100, 215)   # blue
C_PATH       = (  0, 230, 115)   # bright green
C_AGENT      = (255, 170,   0)   # orange
C_NEW_WALL   = (200,  55,  55)   # dynamic wall flash

C_SIDEBAR_BG = ( 18,  18,  26)
C_DIVIDER    = ( 42,  42,  58)
C_TEXT       = (215, 215, 228)
C_TEXT_DIM   = (105, 105, 128)
C_ACCENT     = ( 96, 146, 240)
C_BTN        = ( 36,  38,  54)
C_BTN_HOVER  = ( 55,  58,  80)
C_BTN_ACTIVE = ( 66, 110, 205)
C_BTN_TEXT   = (215, 215, 230)
C_SUCCESS    = (  0, 200, 100)
C_WARNING    = (230, 160,  30)
C_ERROR      = (215,  55,  55)

# ── Cell type IDs ─────────────────────────────────────────────────────────────
EMPTY    = 0
WALL     = 1
START    = 2
GOAL     = 3
FRONTIER = 4
VISITED  = 5
PATH     = 6

# Colour map from cell type → RGB
CELL_COLORS: dict = {
    EMPTY:    C_EMPTY,
    WALL:     C_WALL,
    START:    C_START,
    GOAL:     C_GOAL,
    FRONTIER: C_FRONTIER,
    VISITED:  C_VISITED,
    PATH:     C_PATH,
}
