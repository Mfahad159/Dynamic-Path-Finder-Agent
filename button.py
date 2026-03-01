"""
button.py
=========
Reusable Button widget for the sidebar GUI.
"""

import pygame
from constants import C_BTN, C_BTN_HOVER, C_BTN_ACTIVE, C_BTN_TEXT, C_DIVIDER


class Button:
    """
    A clickable rectangular button with hover and active states.

    Parameters
    ----------
    x, y, w, h : int    — position and size in pixels
    text        : str   — label displayed on the button
    active      : bool  — whether the button starts in the "active" (selected) state
    """

    def __init__(self, x: int, y: int, w: int, h: int,
                 text: str, active: bool = False):
        self.rect   = pygame.Rect(x, y, w, h)
        self.text   = text
        self.active = active
        self._hover = False

    # ── event helpers ─────────────────────────────────────────────────────────

    def update_hover(self, mouse_pos: tuple):
        """Call once per frame with the current mouse position."""
        self._hover = self.rect.collidepoint(mouse_pos)

    def clicked(self, event: pygame.event.Event) -> bool:
        """Return True if this button was left-clicked in *event*."""
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))

    # ── rendering ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        """Render the button onto *surface* using *font* for the label."""
        if self.active:
            bg, fg = C_BTN_ACTIVE, (255, 255, 255)
        elif self._hover:
            bg, fg = C_BTN_HOVER, C_BTN_TEXT
        else:
            bg, fg = C_BTN, C_BTN_TEXT

        pygame.draw.rect(surface, bg,        self.rect, border_radius=6)
        pygame.draw.rect(surface, C_DIVIDER, self.rect, 1, border_radius=6)

        txt  = font.render(self.text, True, fg)
        trec = txt.get_rect(center=self.rect.center)
        surface.blit(txt, trec)
