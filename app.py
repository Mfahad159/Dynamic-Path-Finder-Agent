"""
app.py
======
App class — main game loop, finite-state machine, event handling,
sidebar rendering, and dynamic re-planning orchestration.
"""

import random
import sys
import numpy as np

import pygame

from constants import (
    SIDEBAR_WIDTH, FPS, ANIM_SPEED, AGENT_DELAY_MS, DYNAMIC_PROB,
    # colours
    C_BG, C_SIDEBAR_BG, C_DIVIDER, C_ACCENT,
    C_TEXT, C_TEXT_DIM, C_BTN_TEXT,
    C_SUCCESS, C_WARNING, C_ERROR,
    C_START, C_GOAL, C_WALL, C_FRONTIER, C_VISITED, C_PATH, C_AGENT, C_NEW_WALL,
    # cell types
    WALL, PATH,
)
from grid import Grid
from algorithms import ALGORITHMS, HEURISTICS
from button import Button


class App:
    """
    Top-level application.

    Responsibilities
    ----------------
    - Initialise Pygame and build the window
    - Run the main event / update / draw loop
    - Own the FSM and dispatch state transitions
    - Render the sidebar (metrics, buttons, legend, controls)
    """

    # ── FSM state labels ──────────────────────────────────────────────────────
    IDLE      = 'idle'
    ANIMATING = 'animating'   # replaying search events
    MOVING    = 'moving'      # agent walking the path
    DYNAMIC   = 'dynamic'     # agent walking + dynamic obstacles
    SET_START = 'set_start'   # waiting for user to click a new start cell
    SET_GOAL  = 'set_goal'    # waiting for user to click a new goal cell

    # ── construction ──────────────────────────────────────────────────────────

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols

        # Initialize mixer BEFORE pygame.init() for better compatibility
        self._init_sounds()

        pygame.init()
        pygame.display.set_caption("Dynamic Pathfinding Agent")

        # Window + cell sizing
        info  = pygame.display.Info()
        max_w = min(info.current_w - 40, 1600)
        max_h = min(info.current_h - 80,  940)
        cs    = max(8, min(80,
                           min((max_w - SIDEBAR_WIDTH) // cols,
                               max_h // rows)))
        gw, gh = cols * cs, rows * cs
        win_w  = gw + SIDEBAR_WIDTH
        win_h  = max(gh, 560)

        self.screen  = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
        self.clock   = pygame.time.Clock()
        self.grid    = Grid(rows, cols, cs)
        self.grid_ox = 0
        self.grid_oy = max(0, (win_h - gh) // 2)

        # Fonts
        self.f_title = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.f_med   = pygame.font.SysFont("Segoe UI", 14)
        self.f_sm    = pygame.font.SysFont("Segoe UI", 12)
        self.f_btn   = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.f_xs    = pygame.font.SysFont("Segoe UI", 11)

        # Selection state
        self.algo_name  = 'A*'
        self.heur_name  = 'Manhattan'
        self.density    = 0.30
        self.dynamic_on = False

        # FSM
        self.state = self.IDLE

        # Search animation
        self.events_list = []
        self.anim_idx    = 0

        # Agent
        self.path      = []
        self.agent_idx = 0
        self.agent_pos = None

        # Metrics
        self.nodes_visited = 0
        self.path_cost     = 0
        self.exec_ms       = 0.0
        self.replans       = 0

        # Status bar
        self.status_msg   = ("Ready — draw walls or click Generate Map, "
                             "then press RUN or SPACE.")
        self.status_color = C_TEXT_DIM

        # Timers
        self.last_agent_t = 0

        # Build sidebar buttons
        self._build_buttons(win_w)

    # ── sound helpers ─────────────────────────────────────────────────────────

    def _init_sounds(self):
        """Synthesise two short sine-wave tones used during traversal."""
        try:
            # Re-initialize mixer if not already done, or ensure it's ready
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
                pygame.mixer.init()
            
            self.node_sound = self._make_tone(freq=330,  duration_ms=45, volume=0.08)
            self.step_sound = self._make_tone(freq=440,  duration_ms=60, volume=0.12)
            
            print(f"  ✓ Audio initialized: {pygame.mixer.get_init()}")
        except Exception as e:
            print(f"  ⚠ Audio initialization failed: {e}")
            self.node_sound = None
            self.step_sound = None

    @staticmethod
    def _make_tone(freq: float, duration_ms: int, volume: float) -> pygame.mixer.Sound:
        """Return a short sine-wave Sound object with a smooth envelope and slight gradient."""
        sample_rate = 44100
        n_samples   = int(sample_rate * duration_ms / 1000)
        t           = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
        
        # Frequency Gradient (slight descending slide for a more natural feel)
        freq_grad   = np.linspace(freq, freq * 0.95, n_samples)
        wave        = np.sin(2 * np.pi * freq_grad * t)
        
        # Gentle Envelope (Sine-shaped attack/release)
        # 20% attack, 80% release
        att_len = n_samples // 5
        rel_len = n_samples - att_len
        envelope = np.ones(n_samples)
        envelope[:att_len] = 0.5 * (1 - np.cos(np.pi * np.arange(att_len) / att_len))
        envelope[att_len:] = 0.5 * (1 + np.cos(np.pi * np.arange(rel_len) / rel_len))
        
        wave        = (wave * envelope * volume * 32767).astype(np.int16)
        
        # If mixer is stereo, we need to reshape for stereo
        mixer_conf = pygame.mixer.get_init()
        if mixer_conf and mixer_conf[2] == 2:
            wave = np.repeat(wave[:, np.newaxis], 2, axis=1)
            
        sound = pygame.sndarray.make_sound(wave)
        return sound

    def _build_buttons(self, win_w: int):
        sx   = win_w - SIDEBAR_WIDTH + 10
        fw   = SIDEBAR_WIDTH - 20
        bh   = 28
        hw   = (fw - 4) // 2

        self.btn_gbfs  = Button(sx, 0, hw, bh, "GBFS",       self.algo_name == 'GBFS')
        self.btn_astar = Button(sx + hw + 4, 0, hw, bh, "A*", self.algo_name == 'A*')
        self.btn_manh  = Button(sx, 0, hw, bh, "Manhattan",  self.heur_name == 'Manhattan')
        self.btn_eucl  = Button(sx + hw + 4, 0, hw, bh, "Euclidean", False)
        self.btn_gen   = Button(sx, 0, fw, bh, "Generate Map")
        self.btn_run   = Button(sx, 0, fw, bh, "Run Algorithm")
        self.btn_clear = Button(sx, 0, fw, bh, "Clear Search")
        self.btn_ss    = Button(sx, 0, hw, bh, "Set Start")
        self.btn_sg    = Button(sx + hw + 4, 0, hw, bh, "Set Goal")
        self.btn_dyn   = Button(sx, 0, fw, bh, "Dynamic Mode: OFF")

        self.all_buttons = [
            self.btn_gbfs, self.btn_astar,
            self.btn_manh, self.btn_eucl,
            self.btn_gen, self.btn_run, self.btn_clear,
            self.btn_ss,  self.btn_sg,
            self.btn_dyn,
        ]

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()

    # ── event handling ────────────────────────────────────────────────────────

    def _handle_events(self):
        mp = pygame.mouse.get_pos()
        for btn in self.all_buttons:
            btn.update_hover(mp)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            # Keyboard
            if event.type == pygame.KEYDOWN:
                self._on_key(event.key)

            # Mouse clicks on grid
            if event.type == pygame.MOUSEBUTTONDOWN:
                cell = self.grid.cell_at(*event.pos, self.grid_ox, self.grid_oy)
                if cell:
                    self._on_grid_click(cell, event.button)

            # Mouse drag (paint walls)
            if event.type == pygame.MOUSEMOTION and self.state == self.IDLE:
                cell = self.grid.cell_at(*event.pos, self.grid_ox, self.grid_oy)
                if cell:
                    r, c = cell
                    pressed = pygame.mouse.get_pressed()
                    if pressed[0]:
                        self.grid.place_wall(r, c)
                    elif pressed[2]:
                        self.grid.remove_wall(r, c)

            # Window resize
            if event.type == pygame.VIDEORESIZE:
                _, gh = self.grid.pixel_size()
                self.grid_oy = max(0, (event.h - gh) // 2)

            # Sidebar button clicks
            for btn in self.all_buttons:
                if btn.clicked(event):
                    self._on_button(btn)

    def _on_key(self, key):
        k = pygame   # K_ESCAPE, K_SPACE, etc. are on pygame, not pygame.key
        if key == k.K_ESCAPE:
            pygame.quit(); sys.exit()
        elif key == k.K_SPACE:
            self._run_algorithm()
        elif key == k.K_r:
            self._generate_map()
        elif key == k.K_c:
            self._clear_search()
        elif key == k.K_d:
            self._toggle_dynamic()
        elif key == k.K_s:
            self._enter_set_mode(self.SET_START)
        elif key == k.K_g:
            self._enter_set_mode(self.SET_GOAL)
        elif key in (k.K_PLUS, k.K_EQUALS, k.K_KP_PLUS):
            self.density = min(0.80, round(self.density + 0.05, 2))
            self._set_status(f"Density → {int(self.density*100)}%", C_TEXT_DIM)
        elif key in (k.K_MINUS, k.K_KP_MINUS):
            self.density = max(0.05, round(self.density - 0.05, 2))
            self._set_status(f"Density → {int(self.density*100)}%", C_TEXT_DIM)

    def _on_grid_click(self, cell: tuple, button: int):
        r, c = cell
        if self.state == self.SET_START:
            self.grid.set_start(r, c)
            self.state = self.IDLE
            self._set_status(f"Start → ({r}, {c})", C_SUCCESS)
        elif self.state == self.SET_GOAL:
            self.grid.set_goal(r, c)
            self.state = self.IDLE
            self._set_status(f"Goal → ({r}, {c})", C_SUCCESS)
        elif self.state == self.IDLE:
            if button == 1:
                self.grid.toggle_wall(r, c)
            elif button == 3:
                self.grid.remove_wall(r, c)

    def _on_button(self, btn: Button):
        if btn is self.btn_gbfs:
            self.algo_name = 'GBFS'
            self.btn_gbfs.active, self.btn_astar.active = True, False
        elif btn is self.btn_astar:
            self.algo_name = 'A*'
            self.btn_astar.active, self.btn_gbfs.active = True, False
        elif btn is self.btn_manh:
            self.heur_name = 'Manhattan'
            self.btn_manh.active, self.btn_eucl.active = True, False
        elif btn is self.btn_eucl:
            self.heur_name = 'Euclidean'
            self.btn_eucl.active, self.btn_manh.active = True, False
        elif btn is self.btn_gen:   self._generate_map()
        elif btn is self.btn_run:   self._run_algorithm()
        elif btn is self.btn_clear: self._clear_search()
        elif btn is self.btn_ss:    self._enter_set_mode(self.SET_START)
        elif btn is self.btn_sg:    self._enter_set_mode(self.SET_GOAL)
        elif btn is self.btn_dyn:   self._toggle_dynamic()

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
            self._set_status("No path found — all routes are blocked!", C_ERROR)

    def _clear_search(self):
        self.grid.reset_search()
        self._reset_metrics()
        self.state      = self.IDLE
        self.agent_pos  = None
        self.path       = []
        self.events_list = []
        self.dynamic_on = False
        self.btn_dyn.active = False
        self.btn_dyn.text   = "Dynamic Mode: OFF"
        self._set_status("Search cleared. Ready.", C_TEXT_DIM)

    def _toggle_dynamic(self):
        if self.state == self.MOVING:
            self.dynamic_on     = True
            self.state          = self.DYNAMIC
            self.btn_dyn.active = True
            self.btn_dyn.text   = "Dynamic Mode: ON"
            self._set_status("Dynamic mode ON — walls may spawn!", C_WARNING)
        elif self.state == self.DYNAMIC:
            self.dynamic_on     = False
            self.state          = self.MOVING
            self.btn_dyn.active = False
            self.btn_dyn.text   = "Dynamic Mode: OFF"
            self._set_status("Dynamic mode OFF.", C_TEXT_DIM)
        else:
            self.dynamic_on     = not self.dynamic_on
            self.btn_dyn.active = self.dynamic_on
            self.btn_dyn.text   = (
                "Dynamic Mode: ON"
                if self.dynamic_on else "Dynamic Mode: OFF")
            self._set_status(
                "Dynamic mode will activate once the agent starts moving.",
                C_TEXT_DIM)

    # ── update ────────────────────────────────────────────────────────────────

    def _update(self):
        if self.state == self.ANIMATING:
            self._update_animation()
        elif self.state in (self.MOVING, self.DYNAMIC):
            self._update_agent()

    def _update_animation(self):
        """Replay recorded search events, ANIM_SPEED events per frame."""
        g = self.grid
        for _ in range(ANIM_SPEED):
            if self.anim_idx < len(self.events_list):
                ev_type, ev_cell = self.events_list[self.anim_idx]
                if ev_type == 'frontier':
                    g.mark_frontier(ev_cell)
                else:
                    g.mark_visited(ev_cell)
                # Play a soft tick for each node processed
                if self.node_sound:
                    self.node_sound.play()
                self.anim_idx += 1
            else:
                # Animation finished
                if self.path:
                    g.mark_path(self.path)
                    self.agent_pos = self.path[0]
                    self.agent_idx = 0
                    self.state = self.DYNAMIC if self.dynamic_on else self.MOVING
                    self._set_status(
                        f"Agent moving… | Cost: {self.path_cost} | "
                        f"Nodes: {self.nodes_visited} | "
                        f"Time: {self.exec_ms:.2f}ms", C_SUCCESS)
                else:
                    self.state = self.IDLE
                break

    def _update_agent(self):
        """Move the agent one step if enough time has passed."""
        now = pygame.time.get_ticks()
        if now - self.last_agent_t < AGENT_DELAY_MS:
            return
        self.last_agent_t = now
        g = self.grid
        g._flash_walls.clear()

        if self.agent_idx < len(self.path) - 1:
            # Possibly spawn a dynamic wall
            if self.state == self.DYNAMIC and random.random() < DYNAMIC_PROB:
                remaining_set = set(self.path[self.agent_idx + 1:])
                spawned = g.spawn_dynamic_wall(remaining_set)
                if spawned and spawned in remaining_set:
                    self._replan()
                    return

            self.agent_idx += 1
            self.agent_pos  = self.path[self.agent_idx]
            # Play a brighter click for each agent step
            if self.step_sound:
                self.step_sound.play()
        else:
            # Goal reached
            self.agent_pos  = g.goal
            self.state      = self.IDLE
            self.dynamic_on = False
            self.btn_dyn.active = False
            self.btn_dyn.text   = "Dynamic Mode: OFF"
            self._set_status(
                f"✓ Goal reached! | Cost: {self.path_cost} | "
                f"Nodes: {self.nodes_visited} | Re-plans: {self.replans} | "
                f"Time: {self.exec_ms:.2f}ms", C_SUCCESS)

    def _replan(self):
        """Re-compute a path from the agent's current position to the goal."""
        g       = self.grid
        algo    = ALGORITHMS[self.algo_name]
        h_fn    = HEURISTICS[self.heur_name]
        current = self.agent_pos

        g.clear_path()
        path, _, nv, pc, em = algo(
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
                f"Re-plan #{self.replans} — new cost: {self.path_cost} | "
                f"Total nodes: {self.nodes_visited} | "
                f"Time: {self.exec_ms:.2f}ms", C_WARNING)
        else:
            self.state      = self.IDLE
            self.dynamic_on = False
            self._set_status("Agent stuck — no path after re-plan!", C_ERROR)

    # ── draw ──────────────────────────────────────────────────────────────────

    def _draw(self):
        win_w, win_h = self.screen.get_size()
        _, gh        = self.grid.pixel_size()
        self.grid_oy = max(0, (win_h - gh) // 2)

        self.screen.fill(C_BG)
        self.grid.draw(self.screen, self.grid_ox, self.grid_oy, self.agent_pos)
        self._draw_sidebar(win_w, win_h)
        pygame.display.flip()

    # ── sidebar rendering ─────────────────────────────────────────────────────

    def _draw_sidebar(self, win_w: int, win_h: int):
        sx  = win_w - SIDEBAR_WIDTH
        fw  = SIDEBAR_WIDTH - 20
        hw  = (fw - 4) // 2
        bx  = sx + 10
        by  = 12
        sur = self.screen

        # Background panel
        pygame.draw.rect(sur, C_SIDEBAR_BG, (sx, 0, SIDEBAR_WIDTH, win_h))
        pygame.draw.line(sur, C_ACCENT, (sx, 0), (sx, win_h), 2)

        # Title
        t = self.f_title.render("Pathfinding Agent", True, C_ACCENT)
        sur.blit(t, (bx, by)); by += t.get_height() + 2
        s = self.f_sm.render("Dynamic Grid Navigation  •  Pygame", True, C_TEXT_DIM)
        sur.blit(s, (bx, by)); by += s.get_height() + 8
        self._div(sx, by); by += 10

        # State badge (top-right of sidebar)
        badge_color = {
            self.IDLE:      C_TEXT_DIM, self.ANIMATING: C_FRONTIER,
            self.MOVING:    C_PATH,     self.DYNAMIC:   C_WARNING,
            self.SET_START: C_START,    self.SET_GOAL:  C_GOAL,
        }.get(self.state, C_TEXT_DIM)
        badge_text = {
            self.IDLE: "● IDLE", self.ANIMATING: "● SEARCHING",
            self.MOVING: "● MOVING", self.DYNAMIC: "⚡ DYNAMIC",
            self.SET_START: "● SET START", self.SET_GOAL: "● SET GOAL",
        }.get(self.state, self.state.upper())
        bs = self.f_sm.render(badge_text, True, badge_color)
        sur.blit(bs, (sx + SIDEBAR_WIDTH - bs.get_width() - 8, 8))

        # Algorithm
        self._label(bx, by, "ALGORITHM"); by += 18
        self.btn_gbfs.rect  = pygame.Rect(bx, by, hw, 28)
        self.btn_astar.rect = pygame.Rect(bx + hw + 4, by, hw, 28)
        self.btn_gbfs.draw(sur, self.f_btn)
        self.btn_astar.draw(sur, self.f_btn)
        by += 34

        # Heuristic
        self._label(bx, by, "HEURISTIC"); by += 18
        self.btn_manh.rect = pygame.Rect(bx, by, hw, 28)
        self.btn_eucl.rect = pygame.Rect(bx + hw + 4, by, hw, 28)
        self.btn_manh.draw(sur, self.f_btn)
        self.btn_eucl.draw(sur, self.f_btn)
        by += 34

        self._div(sx, by); by += 10

        # Action buttons
        for btn in (self.btn_gen, self.btn_run, self.btn_clear):
            btn.rect = pygame.Rect(bx, by, fw, 28)
            btn.draw(sur, self.f_btn); by += 32

        self.btn_ss.rect = pygame.Rect(bx, by, hw, 28)
        self.btn_sg.rect = pygame.Rect(bx + hw + 4, by, hw, 28)
        self.btn_ss.draw(sur, self.f_btn)
        self.btn_sg.draw(sur, self.f_btn)
        by += 32

        self.btn_dyn.rect = pygame.Rect(bx, by, fw, 28)
        self.btn_dyn.draw(sur, self.f_btn); by += 36

        self._div(sx, by); by += 10

        # Metrics
        self._label(bx, by, "METRICS"); by += 18
        metrics = [
            ("Nodes Visited", str(self.nodes_visited)),
            ("Path Cost",     str(self.path_cost)),
            ("Exec Time",     f"{self.exec_ms:.2f} ms"),
            ("Re-Plans",      str(self.replans)),
            ("Algorithm",     self.algo_name),
            ("Heuristic",     self.heur_name),
            ("Grid Size",     f"{self.grid.rows} × {self.grid.cols}"),
            ("Density",       f"{int(self.density * 100)}%"),
        ]
        for lbl, val in metrics:
            ls = self.f_sm.render(lbl,  True, C_TEXT_DIM)
            vs = self.f_med.render(val, True, C_TEXT)
            sur.blit(ls, (bx, by))
            sur.blit(vs, (sx + SIDEBAR_WIDTH - vs.get_width() - 10, by))
            by += max(ls.get_height(), vs.get_height()) + 4

        self._div(sx, by); by += 10

        # Legend
        self._label(bx, by, "LEGEND"); by += 18
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
            pygame.draw.rect(sur, col,
                             pygame.Rect(bx, by + 2, 12, 12), border_radius=2)
            pygame.draw.rect(sur, C_DIVIDER,
                             pygame.Rect(bx, by + 2, 12, 12), 1, border_radius=2)
            ns = self.f_sm.render(name, True, C_TEXT_DIM)
            sur.blit(ns, (bx + 16, by)); by += ns.get_height() + 3

        self._div(sx, by); by += 8

        # Controls hint
        self._label(bx, by, "CONTROLS"); by += 18
        for h in [
            "LClick / drag  : place wall",
            "RClick / drag  : remove wall",
            "S → set Start  |  G → set Goal",
            "R → random map  |  C → clear",
            "+/−  →  adjust density",
            "SPACE → run  |  D → dynamic",
            "ESC → quit",
        ]:
            hs = self.f_xs.render(h, True, C_TEXT_DIM)
            sur.blit(hs, (bx, by)); by += hs.get_height() + 2

        # Status bar
        status_y = max(by + 8, win_h - 56)
        self._div(sx, status_y); status_y += 8
        self._wrap_text(self.status_msg, self.status_color, bx, status_y, fw)

    # ── sidebar helpers ───────────────────────────────────────────────────────

    def _div(self, sx: int, y: int):
        pygame.draw.line(self.screen, C_DIVIDER,
                         (sx + 6, y), (sx + SIDEBAR_WIDTH - 6, y), 1)

    def _label(self, x: int, y: int, text: str):
        s = self.f_xs.render(text, True, C_TEXT_DIM)
        self.screen.blit(s, (x, y))

    def _wrap_text(self, text: str, color, x: int, y: int, max_w: int):
        words, line = text.split(), ""
        for word in words:
            test = (line + " " + word).strip()
            if self.f_sm.size(test)[0] > max_w and line:
                self.screen.blit(self.f_sm.render(line, True, color), (x, y))
                y += self.f_sm.get_height() + 2
                line = word
            else:
                line = test
        if line:
            self.screen.blit(self.f_sm.render(line, True, color), (x, y))

    def _set_status(self, msg: str, color):
        self.status_msg   = msg
        self.status_color = color

    def _reset_metrics(self):
        self.nodes_visited = 0
        self.path_cost     = 0
        self.exec_ms       = 0.0
        self.replans       = 0
