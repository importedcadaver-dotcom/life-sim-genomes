"""Pure viewer layout, pacing, preview and input-validation utilities.

No Pygame import at module load; geometry can be tested headlessly.
There is no mutation of the simulation's ecological state here.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
import json
import numpy as np
from .simulation import Config

@dataclass(frozen=True)
class ViewLayout:
    map_rect: tuple[int, int, int, int]
    side_rect: tuple[int, int, int, int]
    toolbar_y: int
    pixel_scale: float


def layout_for(width: int, height: int, world_width: int = 72,
               world_height: int = 54) -> ViewLayout:
    """Responsively fit the entire habitat and reserve a real HUD region."""
    sidebar = min(355, max(275, int(width * .275)))
    available_w = max(160, width - sidebar - 64)
    available_h = max(120, height - 232)
    scale = min(available_w / world_width, available_h / world_height)
    pw, ph = max(1, int(world_width * scale)), max(1, int(world_height * scale))
    x = max(15, int((width - sidebar - pw) / 2))
    y = 104 + max(0, (available_h - ph) // 2)
    return ViewLayout((x, y, pw, ph), (width - sidebar - 18, 103, sidebar, height - 159),
                      height - 102, scale)


class SimulationClock:
    """Wall-clock pacing, independent of render FPS and deterministic world ticks."""
    RATES = (0.5, 1.5, 4., 10., 25., 70., 200., 600.)

    def __init__(self, index: int = 3):
        self.index = index
        self.carry = 0.0

    @property
    def rate(self) -> float:
        return self.RATES[self.index]

    def change(self, delta: int) -> None:
        self.index = min(len(self.RATES) - 1, max(0, self.index + delta))

    def steps(self, elapsed: float, *, paused: bool = False) -> int:
        if paused:
            self.carry = 0.0
            return 0
        self.carry += max(0.0, min(.20, elapsed)) * self.rate
        steps = min(int(self.carry), 24)
        self.carry -= steps
        # Don't keep an arbitrarily long backlog when rendering is slow.
        self.carry = min(self.carry, 24.)
        return steps


def toolbar_grid(x: int, y: int, width: int, count: int = 14,
                 columns: int = 7) -> list[tuple[int, int, int, int]]:
    """Two compact click rows with predictable hit targets at minimum window."""
    if width < 1 or columns < 1 or count < 0:
        raise ValueError("Invalid toolbar geometry")
    gap, height = 6, 33
    cols = min(columns, max(count, 1))
    item_w = (width - gap * (cols - 1)) // cols
    if item_w < 34:
        raise ValueError("Toolbar too narrow")
    return [(x + (i % cols) * (item_w + gap), y + (i // cols) * (height + 5),
             item_w, height) for i in range(count)]


def clamp_window_size(width: int, height: int) -> tuple[int, int]:
    """Viewer controls require at least the compact 1020×685 layout."""
    return (max(1020, int(width)), max(685, int(height)))


def load_qa_actions(path: str | Path | None) -> dict[int, list[dict]]:
    """Optional bounded UI smoke-test script, not an evolutionary experiment."""
    if path is None:
        return {}
    actions = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(actions, list) or len(actions) > 100:
        raise ValueError("QA script must be a list with at most 100 events")
    script: dict[int, list[dict]] = {}
    for item in actions:
        if not isinstance(item, dict) or item.get("action") not in ("key", "click", "resize", "wheel"):
            raise ValueError("Invalid QA action")
        frame = item.get("frame")
        if type(frame) is not int or not (1 <= frame <= 10000):
            raise ValueError("QA frame must be between 1 and 10000")
        action = item["action"]
        if action == "key" and (not isinstance(item.get("key"), str) or
                                 item["key"] not in ("SPACE", "ESCAPE", "r", "i", "a", "y", "q", "e", "d", "w", "1", "2", "3", "4",
                                                     "o", "h", "p", "s", "z", "x", "t", "j", "f", "l", "g", "5")):
            raise ValueError("Invalid QA key")
        if action in ("click", "resize"):
            keys = ("x", "y") if action == "click" else ("width", "height")
            if any(type(item.get(k)) is not int or not 0 <= item[k] <= 5000 for k in keys):
                raise ValueError("Invalid QA geometry")
        if action == "wheel" and item.get("delta") not in (-1, 1):
            raise ValueError("QA wheel delta must be -1 or 1")
        script.setdefault(frame, []).append(item)
    return script


def terrain_rgb(food: np.ndarray, capacity: np.ndarray, *, show_food: bool = True) -> np.ndarray:
    """Smooth, high-contrast scientific heatmap; no simulated 3D or fake entities."""
    values = food if show_food else capacity
    density = np.clip(np.log1p(values) / np.log1p(11), 0, 1)
    # Plum shadows and mint-to-blush illuminated food. Density remains readable.
    anchors = np.array([[28, 23, 45], [48, 52, 70], [65, 109, 104],
                        [156, 177, 138], [255, 206, 171]], dtype=float)
    u = density * (len(anchors) - 1)
    i = np.minimum(u.astype(int), len(anchors) - 2)
    fractional = (u - i)[..., None]
    return np.uint8(np.clip(anchors[i] * (1 - fractional) + anchors[i + 1] * fractional, 0, 255))


def draw_cute_organism(screen, pg, x: int, y: int, direction: float,
                       radius: int, pigment: tuple[int, int, int], *, selected=False,
                       spots=False) -> None:
    """Cute four-circle 'berry bug' with ears, eyes, blush and a heading nose.

    Entirely visual: genomes, sensors, motor commands and ecology are untouched.
    Compact LOD dots remain available for dense populations.
    """
    r = max(4, int(radius))
    outline = (48, 31, 59)
    ear = max(2, r // 2)
    pg.draw.circle(screen, outline, (x - r + 1, y - r + 1), ear + 1)
    pg.draw.circle(screen, outline, (x + r - 1, y - r + 1), ear + 1)
    pg.draw.circle(screen, pigment, (x - r + 1, y - r + 1), ear)
    pg.draw.circle(screen, pigment, (x + r - 1, y - r + 1), ear)
    pg.draw.circle(screen, outline, (x, y), r + 1)
    pg.draw.circle(screen, pigment, (x, y), r)
    # Tiny eye highlights preserve a friendly face even in a busy ecosystem.
    eye_y = y - max(1, r // 4)
    spacing = max(2, r // 3)
    pg.draw.circle(screen, outline, (x - spacing, eye_y), max(1, r // 5))
    pg.draw.circle(screen, outline, (x + spacing, eye_y), max(1, r // 5))
    if r >= 6:
        pg.draw.circle(screen, (255, 248, 252), (x - spacing, eye_y - 1), 1)
        pg.draw.circle(screen, (255, 248, 252), (x + spacing, eye_y - 1), 1)
        pg.draw.circle(screen, (255, 120, 172), (x - spacing - 2, y + 2), 2)
        pg.draw.circle(screen, (255, 120, 172), (x + spacing + 2, y + 2), 2)
    pg.draw.circle(screen, outline, (x, y + max(1, r // 3)), 1)
    if spots and r >= 6:
        pg.draw.circle(screen, (255, 240, 245), (x - r // 2, y + r // 3), max(1, r // 5))
        pg.draw.circle(screen, (255, 240, 245), (x + r // 2, y + r // 2), max(1, r // 6))
    # A visible directional indicator; the face is intentionally screen-facing.
    tip_x = int(x + np.cos(direction) * (r + 5))
    tip_y = int(y + np.sin(direction) * (r + 5))
    pg.draw.line(screen, (255, 234, 196), (x, y), (tip_x, tip_y), 2)
    pg.draw.circle(screen, (255, 234, 196), (tip_x, tip_y), 2)
    if selected:
        pg.draw.circle(screen, (255, 147, 204), (x, y), r + 7, 2)
        pg.draw.circle(screen, (255, 221, 238), (x, y), r + 12, 1)


def toggle_resource_layout(cfg: Config) -> Config:
    if cfg.resource_layout == "hills":
        return replace(cfg, resource_layout="islands", resource_background=0.01)
    return replace(cfg, resource_layout="hills", resource_background=0.25)


