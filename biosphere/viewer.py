"""Interactive ecosystem observatory. Visuals never alter evolutionary rules.

Pygame is imported lazily so the research engine and geometry tests remain
headless. The only terrain mutation is the explicitly marked sandbox brush.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import math
import time
import json

import numpy as np

from .simulation import Config, World
from .genetics import LOCI, phenotype_summary, INDEX
from .playful import (Chronicle, MiniGames, PairedLab, LAB_VARIANTS, cheat, creature_color)


# Stable public imports: existing tests and QA tools still import these from viewer.
from .viewer_presentation import (
    ViewLayout, SimulationClock, layout_for, toolbar_grid, clamp_window_size,
    load_qa_actions, terrain_rgb, draw_cute_organism, toggle_resource_layout,
)


def view(args) -> None:
    try:
        import pygame
    except ImportError as exc:
        raise SystemExit("Install the optional viewer: pip install pygame-ce") from exc

    pygame.init()
    screen = pygame.display.set_mode(clamp_window_size(getattr(args, "window_width", 1400),
                                                     getattr(args, "window_height", 880)), pygame.RESIZABLE)
    pygame.display.set_caption("Accidental Biosphere | Pink Living Observatory")
    clock = pygame.time.Clock()
    qa_actions = load_qa_actions(getattr(args, "qa_script", None))
    qa_events_executed = 0
    ui = pygame.font.SysFont("segoeui", 17)
    small = pygame.font.SysFont("segoeui", 14)
    big = pygame.font.SysFont("segoeui", 26, bold=True)
    num = pygame.font.SysFont("consolas", 23, bold=True)
    micro = pygame.font.SysFont("consolas", 12)
    BG, PANEL, PANEL2 = (25, 19, 39), (40, 32, 55), (60, 44, 72)
    TEXT, MUTED, GREEN, GOLD, CORAL = ((255, 242, 249), (189, 172, 196),
                                      (166, 231, 202), (255, 197, 223), (255, 142, 164))
    PINK, PLUM = (255, 151, 206), (77, 51, 87)
    world = (World.load(args.resume) if args.resume else World(
        Config(max_population=args.max_population, boundary_mode=args.boundary_mode,
               patch_shift_interval=args.patch_shift_interval, move_cost=args.move_cost,
               resource_layout=args.resource_layout,
               resource_background=(args.resource_background if args.resource_background is not None else
                                    (0.01 if args.resource_layout == "islands" else 0.25)),
               island_count=args.island_count, island_sigma=args.island_sigma,
               island_peak=args.island_peak,
               genetics_enabled=not getattr(args, "legacy_genetics", False),
               regulation_enabled=(not getattr(args, "legacy_genetics", False) and
                                   not getattr(args, "no_regulation", False)),
               reproduction_mode=getattr(args, "reproduction_mode", "mixed"),
               body_mutation_probability=getattr(args, "body_mutation_rate", .045),
               copy_mutation_probability=getattr(args, "copy_mutation_rate", .008)), seed=args.seed))
    seed = world.seed
    pause = False
    sim_clock = SimulationClock()
    pause_on_events = False  # Do not interrupt a new viewer before the user opts in.
    reset_confirmation: tuple[str, float] | None = None
    # Start with a real organism highlighted, avoiding an empty specimen panel.
    # Observing a specimen never alters RNG, motor commands or evolutionary selection.
    selected_id: int | None = int(world.ids[0]) if world.population else None
    if selected_id is not None:
        world.watch(selected_id)
    follow = False
    zoom_steps = (1.0, 1.5, 2.25, 3.5)
    zoom_index = 0
    cam_x, cam_y = world.config.width / 2, world.config.height / 2
    show_food = True
    show_help = False
    show_journal = False
    show_archive = False
    archive_offset = 0
    show_micro = False
    show_tree = False
    side_tab = "specimen"
    sandbox_brush = False
    show_cheats = show_games = show_chronicle = show_lab = show_dna = False
    mini_kind = "berries"
    dna_page = "body"
    reg_page = 0
    games = MiniGames()
    lab: PairedLab | None = None
    replay_index = -1
    tree_offset = 0
    chronicle_offset = 0
    chronicle = Chronicle(events=[dict(e) for e in world.observation_log[-8000:]])
    observer_warning: str | None = None
    if args.resume:
        companion = Path(str(args.resume) + ".observer.json")
        if companion.exists():
            try:
                chronicle, games = Chronicle.load(companion, checkpoint=args.resume)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                # Old/malformed sidecars must not block reading a valid world.
                observer_warning = f"Observer notebook not loaded: {exc}"
                chronicle = Chronicle(events=[dict(e) for e in world.observation_log[-8000:]])
    event_rings: list[tuple[float, str, float, float]] = []
    event_feed: list[tuple[int, str]] = [
        (int(event["tick"]), f"{event['kind']} · #{event['id']}")
        for event in world.observation_log[-8:]]
    history = world.population_history
    buttons: list[tuple[pygame.Rect, str]] = []
    notice, notice_until = "", 0.0
    frame = 0
    pending_save = False
    saving_path: Path | None = None
    dragging = False
    drag_origin = None
    drag_camera = None
    regrowth_presets = (0.001, 0.003, 0.006, 0.012, 0.030)
    cached_terrain_key = None
    cached_terrain_surface = None
    cached_archive_deaths = -1
    cached_archive_rows: list[dict] = []

    def announce(message: str) -> None:
        nonlocal notice, notice_until
        notice = message
        notice_until = time.monotonic() + 4.5

    if observer_warning:
        announce(observer_warning)
    elif selected_id is not None:
        announce(f"Specimen #{selected_id} highlighted · click another or press L to follow")

    def caption(t: str, x: float, y: float, color=MUTED, font=small,
                max_width: int | None = None) -> None:
        text = str(t)
        if max_width is not None and font.size(text)[0] > max_width:
            while text and font.size(text + "...")[0] > max_width:
                text = text[:-1]
            text += "..." if text else ""
        screen.blit(font.render(text, True, color), (int(x), int(y)))

    def box(rect: pygame.Rect, color=PANEL, radius=12, border=None):
        pygame.draw.rect(screen, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(screen, border, rect, 1, border_radius=radius)

    def reset_world() -> None:
        nonlocal world, selected_id, follow, cam_x, cam_y, pause, history, show_archive, show_micro, show_tree
        nonlocal chronicle, games, lab, show_cheats, show_games, show_chronicle, show_lab, show_dna, replay_index, tree_offset
        nonlocal dna_page, reg_page
        nonlocal cached_terrain_key, cached_terrain_surface, cached_archive_deaths
        world = World(world.config, seed=seed)
        selected_id = int(world.ids[0]) if world.population else None
        if selected_id is not None:
            world.watch(selected_id)
        cached_terrain_key, cached_terrain_surface, cached_archive_deaths = None, None, -1
        follow = False
        cam_x, cam_y = world.config.width / 2, world.config.height / 2
        sim_clock.carry = 0.0
        pause = False
        event_rings.clear()
        event_feed.clear()
        history = world.population_history
        show_archive, show_micro, show_tree = False, False, False
        show_cheats = show_games = show_chronicle = show_lab = show_dna = False
        dna_page, reg_page = "body", 0
        chronicle, games, lab, replay_index, tree_offset = Chronicle(), MiniGames(), None, -1, 0

    def zoom(change: int) -> None:
        nonlocal zoom_index
        zoom_index = max(0, min(len(zoom_steps) - 1, zoom_index + change))

    def intervene_config(**updates) -> None:
        """Log live environment changes so a save cannot masquerade as a control."""
        old_values = {k: getattr(world.config, k) for k in updates}
        world.config = replace(world.config, **updates)
        world.manual_interventions.append({
            "tick": world.tick, "kind": "live_environment_change",
            "before": old_values, "after": updates})
        announce("Live ecology changed: this run is now marked as intervened")

    def operate(action: str) -> None:
        nonlocal pause, show_food, show_help, show_journal, show_archive, show_micro, show_tree
        nonlocal sandbox_brush, pending_save, selected_id, follow, pause_on_events
        nonlocal side_tab, reset_confirmation, archive_offset
        nonlocal show_cheats, show_games, show_chronicle, show_lab, show_dna, lab, mini_kind, replay_index, tree_offset
        nonlocal dna_page, reg_page
        if action == "regulation_page":
            dna_page = "regulation" if dna_page == "body" else "body"
            reg_page = 0
            return
        if action == "reg_previous":
            reg_page = max(0, reg_page - 1)
            return
        if action == "reg_next":
            if selected_id is not None:
                detail = world.specimen(selected_id)
                if detail and (reg_page + 1) * 10 < len(detail.get("regulatory_genes", [])):
                    reg_page += 1
            return
        if action in ("cheat_menu", "games_menu", "chronicle_menu", "lab_menu", "dna_menu"):

            current = {"cheat_menu": show_cheats, "games_menu": show_games,
                       "chronicle_menu": show_chronicle, "lab_menu": show_lab, "dna_menu": show_dna}[action]
            show_cheats = show_games = show_chronicle = show_lab = show_dna = False
            show_help = show_archive = show_micro = show_tree = show_journal = False
            if not current:
                if action == "cheat_menu":
                    show_cheats = True
                elif action == "games_menu":
                    show_games = True
                    if games.challenge is None:
                        games.create(world, "berries")
                elif action == "chronicle_menu":
                    show_chronicle = True
                elif action == "dna_menu":
                    show_dna = True
                else:
                    show_lab = True
                    lab = PairedLab(world, "half_growth")
            return
        if action.startswith("cheat:"):
            before_events = len(world.observation_log)
            announce(cheat(world, action.split(":", 1)[1], selected_id))
            chronicle.events.extend(dict(e) for e in world.observation_log[before_events:])
            return
        if action.startswith("game:"):
            kind = action.split(":", 1)[1]
            try:
                games.create(world, kind)
                mini_kind = kind
            except ValueError as exc:
                announce(str(exc))
            return
        if action.startswith("answer:"):
            if games.challenge and games.challenge.chosen is None:
                answer = int(action.split(":", 1)[1])
                good = games.answer(answer)
                announce("Correct! +1 observation star" if good else
                         f"Not quite. Answer: {games.challenge.winner + 1}")
            return
        if action == "bookmark":
            if selected_id is None:
                announce("Select a specimen first")
            else:
                added = chronicle.toggle(world, selected_id)
                announce(("Bookmarked" if added else "Unbookmarked") + f" #{selected_id}")
            return
        if action == "replay":
            if selected_id is not None and chronicle.traces.get(str(selected_id)):
                replay_index = 0 if replay_index < 0 else -1
                announce("Read-only specimen movement replay" if replay_index == 0 else "Replay closed")
            else:
                announce("Bookmark a living creature and observe it to record a replay")
            return
        if action.startswith("lab:"):
            lab = PairedLab(world, action.split(":", 1)[1])
            announce("Started a matched A/B run in a separate, cloned habitat")
            return
        if action == "tree_next":
            if selected_id is not None and world.relatives(selected_id, limit=1, offset=tree_offset + 9):
                tree_offset += 9
            return
        if action == "tree_previous":
            tree_offset = max(0, tree_offset - 9)
            return
        if action == "pause":
            pause = not pause
        elif action == "step":
            if any((show_cheats, show_games, show_chronicle, show_lab, show_dna)):
                announce("Close this panel before advancing the source world")
                return
            pause = True
            advance(1)
        elif action == "faster":
            sim_clock.change(1)
        elif action == "slower":
            sim_clock.change(-1)
        elif action == "zoom_in":
            zoom(1)
        elif action == "zoom_out":
            zoom(-1)
        elif action == "map":
            show_food = not show_food
        elif action == "follow":
            follow = bool(selected_id is not None and not follow)
            if selected_id is None:
                announce("Choose an organism before following it")
        elif action == "sandbox":
            sandbox_brush = not sandbox_brush
            announce("Sandbox brush enabled: click terrain to grow food" if sandbox_brush else
                     "Sandbox brush disabled: click organisms to inspect")
        elif action == "save":
            pending_save = True
        elif action == "events_pause":
            pause_on_events = not pause_on_events
            announce("Pause on selected life events: " + ("ON" if pause_on_events else "OFF"))
        elif action == "archive":
            show_archive = not show_archive
            archive_offset = 0
            show_micro = show_tree = False
        elif action == "archive_older":
            archive_offset = min(max(0, len(world.life_archive) - 1), archive_offset + 8)
        elif action == "archive_newer":
            archive_offset = max(0, archive_offset - 8)
        elif action == "lineage_tree":
            show_tree = not show_tree
            show_micro = show_archive = False
            if selected_id is None:
                announce("Choose a specimen to view its lineage graph")
        elif action == "micro":
            show_micro = not show_micro
            show_archive = show_tree = False
            if selected_id is None:
                announce("Select a specimen to open its microscope")
        elif action.startswith("tab:"):
            side_tab = action[4:]
        elif action.startswith("select:"):
            candidate = int(action.split(":", 1)[1])
            if world.watch(candidate):
                selected_id = candidate
                tree_offset = 0
                follow = False
                side_tab = "specimen"
                show_archive = False
                announce(f"Examining specimen #{candidate}")
        elif action == "parent" and selected_id is not None:
            detail = world.specimen(selected_id)
            if detail and detail['parent_id'] >= 0:
                if world.specimen(detail['parent_id']) is None:
                    announce("Parent record not available in this historical checkpoint")
                else:
                    operate(f"select:{detail['parent_id']}")
        elif action == "child" and selected_id is not None:
            children = world.relatives(selected_id, limit=1, offset=-1)
            if children:
                operate(f"select:{children[-1]}")
        elif action == "help":
            show_help = not show_help
        elif action == "journal":
            show_journal = not show_journal
        elif action in ("restart", "layout"):
            current = time.monotonic()
            if reset_confirmation and reset_confirmation[0] == action and current <= reset_confirmation[1]:
                reset_confirmation = None
                if action == "layout":
                    world.config = toggle_resource_layout(world.config)
                reset_world()
                announce("Fresh world started. Prior organisms were not carried over.")
            else:
                reset_confirmation = (action, current + 6.)
                announce("Press " + ("I" if action == "layout" else "R") +
                         " again within 6 seconds to discard this population")
        elif action == "walls":
            intervene_config(boundary_mode=(
                "reflect" if world.config.boundary_mode == "wrap" else "wrap"))
            announce("Boundary mode: " + world.config.boundary_mode)
        elif action == "shift":
            intervene_config(patch_shift_interval=(
                0 if world.config.patch_shift_interval else 35))
        elif action == "cost":
            intervene_config(move_cost=(
                .065 if world.config.move_cost > .065 else .75))
        elif action in ("less_growth", "more_growth"):
            current = min(range(len(regrowth_presets)),
                          key=lambda i: abs(regrowth_presets[i] - world.config.growth_rate))
            current = max(0, min(len(regrowth_presets) - 1,
                                 current + (-1 if action == "less_growth" else 1)))
            intervene_config(growth_rate=regrowth_presets[current])

    def advance(ticks: int) -> None:
        nonlocal selected_id, follow, pause
        for _ in range(ticks):
            if not world.population:
                break
            world.step()
            chronicle.observe(world)
            if world.notable_events and world.notable_events[-1]['tick'] == world.tick:
                announce("Observation: " + world.notable_events[-1]['message'])
            births = [ev for ev in world.last_events if ev["kind"] == "birth"]
            deaths = [ev for ev in world.last_events if ev["kind"] == "death"]
            if births or deaths:
                now = time.monotonic()
                for ev in (births[:7] + deaths[:7]):
                    event_rings.append((now, ev["kind"], ev["x"], ev["y"]))
                event_feed.append((world.tick, f"{len(births)} births / {len(deaths)} deaths"))
                del event_feed[:-14]
                if selected_id is not None:
                    offspring = [ev for ev in births if ev.get("parent_id") == selected_id]
                    selected_dead = [ev for ev in deaths if ev["id"] == selected_id]
                    if offspring:
                        announce(f"#{selected_id} had {len(offspring)} offspring · tick {world.tick}")
                    if selected_dead:
                        follow = False
                        announce(f"Specimen #{selected_id} died: {selected_dead[0]['cause']}")
                    if (offspring or selected_dead) and pause_on_events:
                        pause = True
                        sim_clock.carry = 0.0
                        break
            if world.population == 0:
                event_feed.append((world.tick, "Population extinct"))
                pause = True
                break
        now = time.monotonic()
        event_rings[:] = [event for event in event_rings if now - event[0] < 4.5][-200:]

    def map_to_screen(x: float, y: float, ox: int, oy: int, pw: int, ph: int,
                      units: float) -> tuple[int, int]:
        dx, dy = x - cam_x, y - cam_y
        if world.config.boundary_mode == "wrap":
            dx = (dx + world.config.width / 2) % world.config.width - world.config.width / 2
            dy = (dy + world.config.height / 2) % world.config.height - world.config.height / 2
        return int(ox + pw / 2 + dx * units), int(oy + ph / 2 + dy * units)

    def screen_to_map(sx: float, sy: float, ox: int, oy: int, pw: int, ph: int,
                      units: float) -> tuple[float, float]:
        px = cam_x + (sx - ox - pw / 2) / units
        py = cam_y + (sy - oy - ph / 2) / units
        if world.config.boundary_mode == "wrap":
            return px % world.config.width, py % world.config.height
        return max(0.0, min(world.config.width - 1e-6, px)), max(0.0, min(world.config.height - 1e-6, py))

    def button(rect: pygame.Rect, name: str, caption_text: str, active=False) -> None:
        mx, my = pygame.mouse.get_pos()
        over = rect.collidepoint(mx, my)
        color = (48, 81, 76) if active else ((43, 63, 68) if over else PANEL)
        box(rect, color, 8, (94, 150, 135) if active else None)
        while caption_text and small.size(caption_text)[0] > rect.w - 9:
            caption_text = caption_text[:-1]
        surf = small.render(caption_text, True, GREEN if active else TEXT)
        screen.blit(surf, surf.get_rect(center=rect.center))
        buttons.append((rect, name))

    running = True
    frame_durations: list[float] = []
    while running:
        draw_start = time.perf_counter()
        frame += 1
        w, h = screen.get_size()
        L = layout_for(w, h, world.config.width, world.config.height)
        ox, oy, pw, ph = L.map_rect
        sx, sy, sw, sh = L.side_rect
        units = L.pixel_scale * zoom_steps[zoom_index]
        incoming = list(pygame.event.get())
        for spec in qa_actions.get(frame, []):
            if spec["action"] == "key":
                incoming.append(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, "K_" + spec["key"])))
            elif spec["action"] == "click":
                incoming.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                                   button=1, pos=(spec["x"], spec["y"])))
            elif spec["action"] == "resize":
                incoming.append(pygame.event.Event(pygame.VIDEORESIZE,
                                                   w=spec["width"], h=spec["height"]))
            elif spec["action"] == "wheel":
                incoming.append(pygame.event.Event(pygame.MOUSEWHEEL, y=spec["delta"]))
            qa_events_executed += 1
        for ev in incoming:
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.VIDEORESIZE:
                requested = (max(1020, ev.w), max(685, ev.h))
                if screen.get_size() != requested:
                    screen = pygame.display.set_mode(requested, pygame.RESIZABLE)
            elif ev.type == pygame.KEYDOWN:
                keymap = {pygame.K_SPACE: "pause", pygame.K_n: "step", pygame.K_j: "journal",
                          pygame.K_q: "cheat_menu", pygame.K_e: "games_menu",
                          pygame.K_d: "chronicle_menu", pygame.K_w: "lab_menu",
                          pygame.K_EQUALS: "faster", pygame.K_KP_PLUS: "faster",
                          pygame.K_MINUS: "slower", pygame.K_KP_MINUS: "slower",
                          pygame.K_z: "zoom_in", pygame.K_x: "zoom_out",
                          pygame.K_f: "map", pygame.K_l: "follow", pygame.K_t: "sandbox",
                          pygame.K_s: "save", pygame.K_h: "help", pygame.K_r: "restart",
                          pygame.K_i: "layout", pygame.K_b: "walls", pygame.K_m: "shift",
                          pygame.K_c: "cost", pygame.K_a: "archive", pygame.K_o: "micro",
                          pygame.K_p: "events_pause", pygame.K_u: "parent", pygame.K_k: "child",
                          pygame.K_y: "lineage_tree", pygame.K_PAGEDOWN: "archive_older",
                          pygame.K_PAGEUP: "archive_newer",
                          pygame.K_v: "tab:events", pygame.K_g: "dna_menu",
                          pygame.K_TAB: "tab:specimen", pygame.K_LEFTBRACKET: "less_growth",
                          pygame.K_RIGHTBRACKET: "more_growth"}
                if ev.key == pygame.K_ESCAPE:
                    if any((show_archive, show_micro, show_help, show_journal, show_tree,
                            show_cheats, show_games, show_chronicle, show_lab, show_dna)):
                        show_archive = show_micro = show_help = show_journal = show_tree = False
                        show_cheats = show_games = show_chronicle = show_lab = show_dna = False
                    else:
                        running = False
                elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                    k = ev.key - pygame.K_1
                    if show_cheats and k < 5:
                        operate("cheat:" + ("feast", "energy", "babies", "immortal", "gene_spark")[k])
                    elif show_games and k < 3:
                        operate(f"answer:{k}")
                    elif show_lab and k < 3:
                        operate("lab:" + tuple(LAB_VARIANTS)[k])
                elif ev.key in keymap:
                    operate(keymap[ev.key])
            elif ev.type == pygame.MOUSEWHEEL:
                if show_archive:
                    operate("archive_newer" if ev.y > 0 else "archive_older")
                else:
                    zoom(1 if ev.y > 0 else -1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
                if pygame.Rect(L.map_rect).collidepoint(ev.pos):
                    dragging, drag_origin, drag_camera = True, ev.pos, (cam_x, cam_y)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 3:
                dragging = False
            elif ev.type == pygame.MOUSEMOTION and dragging and drag_origin is not None:
                cam_x = drag_camera[0] - (ev.pos[0] - drag_origin[0]) / units
                cam_y = drag_camera[1] - (ev.pos[1] - drag_origin[1]) / units
                follow = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                hit = next((action for rect, action in buttons if rect.collidepoint(ev.pos)), None)
                if hit:
                    operate(hit)
                elif any((show_archive, show_tree, show_micro, show_help, show_journal,
                          show_cheats, show_games, show_chronicle, show_lab, show_dna)):
                    # Modal overlay should not click through into the habitat.
                    pass
                elif pygame.Rect(L.map_rect).collidepoint(ev.pos):
                    wx, wy = screen_to_map(*ev.pos, ox, oy, pw, ph, units)
                    if sandbox_brush:
                        amount = world.fertilize(wx, wy)
                        event_feed.append((world.tick, f"Sandbox nutrient bloom: +{amount:.0f} food capacity"))
                        event_feed[:] = event_feed[-8:]
                        announce("Sandbox modified: this world is no longer a control run")
                    elif world.population:
                        if world.config.boundary_mode == "wrap":
                            dx = np.abs(world.x - wx)
                            dy = np.abs(world.y - wy)
                            dx = np.minimum(dx, world.config.width - dx)
                            dy = np.minimum(dy, world.config.height - dy)
                        else:
                            dx, dy = np.abs(world.x - wx), np.abs(world.y - wy)
                        k = int(np.argmin(dx ** 2 + dy ** 2))
                        new_id = int(world.ids[k]) if (dx[k] ** 2 + dy[k] ** 2) ** .5 * units < 20 else None
                        selected_id = new_id
                        if selected_id is None:
                            follow = False
                        else:
                            world.watch(selected_id)
                            side_tab = "specimen"

        elapsed = clock.get_time() / 1000.0 if frame > 1 else 1.0 / 35
        # Paired lab and games freeze the source world; their UI is observational.
        modal_pause = any((show_cheats, show_games, show_chronicle, show_lab))
        steps = sim_clock.steps(elapsed, paused=pause or modal_pause or not bool(world.population))
        if show_lab and lab is not None and not lab.done:
            lab.advance(3)
        if replay_index >= 0 and selected_id is not None:
            trace = chronicle.traces.get(str(selected_id), [])
            if trace:
                replay_index = min(len(trace) - 1, replay_index + (1 if frame % 3 == 0 else 0))
            else:
                replay_index = -1
        if steps:
            advance(steps)
        if follow and selected_id is not None:
            where = np.flatnonzero(world.ids == selected_id)
            if len(where):
                cam_x, cam_y = float(world.x[where[0]]), float(world.y[where[0]])
        if world.config.boundary_mode == "reflect":
            halfx, halfy = pw / (2 * units), ph / (2 * units)
            cam_x = max(halfx, min(world.config.width - halfx, cam_x))
            cam_y = max(halfy, min(world.config.height - halfy, cam_y))
        else:
            cam_x %= world.config.width
            cam_y %= world.config.height

        screen.fill(BG)
        caption("THE ACCIDENTAL BIOSPHERE", 24, 17, TEXT, big)
        caption("PINK LIVING OBSERVATORY   /   INHERITED DNA + REAL ECOLOGICAL SELECTION", 25, 51, PINK, micro)
        caption(f"SEED {seed}    |    {world.config.resource_layout.upper()}    |    "
                f"{world.config.boundary_mode.upper()} BOUNDARIES", w - 403, 24, MUTED, small, 370)
        pygame.draw.line(screen, PLUM, (24, 86), (w - 24, 86), 1)

        # Habitat map: a scientific food/capacity field, with creatures rendered on top.
        pygame.draw.rect(screen, (14, 27, 34), (ox - 2, oy - 2, pw + 4, ph + 4), border_radius=8)
        tile_w, tile_h = max(1, int(world.config.width * units)), max(1, int(world.config.height * units))
        terrain_key = (id(world), world.tick, len(world.manual_interventions), show_food, tile_w, tile_h)
        if terrain_key != cached_terrain_key:
            rgb = terrain_rgb(world.food, world.capacity, show_food=show_food)
            base = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
            cached_terrain_surface = pygame.transform.smoothscale(base, (tile_w, tile_h))
            cached_terrain_key = terrain_key
        surface = cached_terrain_surface
        pygame.draw.rect(screen, (77, 110, 104), (ox - 2, oy - 2, pw + 4, ph + 4), 1, border_radius=8)
        screen.set_clip(pygame.Rect(ox, oy, pw, ph))
        left = ox + pw / 2 - cam_x * units
        top = oy + ph / 2 - cam_y * units
        shifts = (-1, 0, 1) if world.config.boundary_mode == "wrap" else (0,)
        for tx in shifts:
            for ty in shifts:
                xx, yy = int(left + tx * tile_w), int(top + ty * tile_h)
                if xx < ox + pw and xx + tile_w > ox and yy < oy + ph and yy + tile_h > oy:
                    screen.blit(surface, (xx, yy))
        # Draw a read-only replay cursor from saved specimen observations.
        if replay_index >= 0 and selected_id is not None:
            track = chronicle.traces.get(str(selected_id), [])
            if track:
                record = track[min(replay_index, len(track) - 1)]
                hx, hy = map_to_screen(record["x"], record["y"], ox, oy, pw, ph, units)
                pygame.draw.circle(screen, PINK, (hx, hy), 13, 3)
                pygame.draw.circle(screen, (255, 245, 253), (hx, hy), 4)
        # Real-time expiry works even while the simulation is paused.
        now = time.monotonic()
        event_rings[:] = [e for e in event_rings if now - e[0] < 4.5]
        # Native event markers are genuinely tied to births/deaths from World.step.
        for tick, kind, cx, cy in event_rings:
            px, py = map_to_screen(cx, cy, ox, oy, pw, ph, units)
            if ox <= px <= ox + pw and oy <= py <= oy + ph:
                r = max(2, int(3 + (time.monotonic() - tick) * 3.5))
                shade = GREEN if kind == "birth" else CORAL
                pygame.draw.circle(screen, shade, (px, py), r, 1)
        selected_path = world.watch_traces.get(selected_id, []) if selected_id is not None else []
        if len(selected_path) >= 2:
            for a, b in zip(selected_path, selected_path[1:]):
                ax, ay = map_to_screen(float(a['x']), float(a['y']), ox, oy, pw, ph, units)
                bx, by = map_to_screen(float(b['x']), float(b['y']), ox, oy, pw, ph, units)
                # Avoid falsely drawing a line across the wrap seam.
                if math.hypot(bx - ax, by - ay) < 12 * units:
                    pygame.draw.line(screen, (245, 201, 111), (ax, ay), (bx, by), 2)
        biology = world.biology() if world.config.genetics_enabled else None
        for j in range(world.population):
            px, py = map_to_screen(float(world.x[j]), float(world.y[j]), ox, oy, pw, ph, units)
            if not (ox + 3 <= px < ox + pw - 3 and oy + 3 <= py < oy + ph - 3):
                continue
            theta = float(world.angle[j])
            is_selected = selected_id is not None and int(world.ids[j]) == selected_id
            size_factor = float(biology["size"][j]) if biology is not None else 1.0
            body = max(4, min(13, int(units * 0.57 * size_factor)))
            color = creature_color(world.genomes[j], world.body_dna[j] if biology is not None else None,
                                   world.gene_copies[j] if biology is not None else None)
            if world.population > 650 and zoom_index == 0 and not is_selected:
                pygame.draw.circle(screen, color, (px, py), 3)
                pygame.draw.circle(screen, (255, 232, 245), (px - 1, py - 1), 1)
                continue
            has_spots = bool(world.body_dna[j, INDEX["spots"]] * world.gene_copies[j, INDEX["spots"]] > .25)
            draw_cute_organism(screen, pygame, px, py, theta, body,
                               color, selected=is_selected, spots=has_spots)
        screen.set_clip(None)
        map_label = "FOOD STOCK" if show_food else "FOOD CAPACITY"
        box(pygame.Rect(ox + 11, oy + 11, 188, 31), (15, 31, 37), 7)
        caption(f"● {map_label}  |  {zoom_steps[zoom_index]:g}x", ox + 21, oy + 16, GREEN, small)
        if world.manual_interventions:
            box(pygame.Rect(ox + 12, oy + ph - 42, 248, 30), (75, 44, 38), 8)
            caption("INTERVENED · not a control run", ox + 19, oy + ph - 36, (255, 207, 161), small)
        elif sandbox_brush:
            box(pygame.Rect(ox + 12, oy + ph - 42, 224, 30), (40, 62, 45), 8)
            caption("SANDBOX BRUSH · click to feed", ox + 19, oy + ph - 36, GREEN, small)
        if world.population == 0:
            box(pygame.Rect(ox + pw // 2 - 200, oy + ph // 2 - 52, 400, 108), (33, 34, 38), 14, CORAL)
            caption("EXTINCTION", ox + pw // 2 - 95, oy + ph // 2 - 38, CORAL, big)
            caption("No organisms survived. Press R to restart.", ox + pw // 2 - 156,
                    oy + ph // 2 + 8, TEXT, small)

        # Larger two-row click targets. Layout helpers are tested without Pygame.
        buttons.clear()
        # Always-accessible tabs for playful tools (also available by keyboard).
        nav_labels = (("cheat_menu", "CHEATS"), ("games_menu", "GAMES"),
                      ("chronicle_menu", "CHRONICLE"), ("lab_menu", "A/B LAB"),
                      ("dna_menu", "DNA"))
        nav_width = min(83, max(53, (pw - 230) // 5 - 5))
        for k, (action, label) in enumerate(nav_labels):
            rect = pygame.Rect(ox + 210 + k * (nav_width + 4), oy + 10, nav_width, 32)
            button(rect, action, label,
                   active=(show_cheats if k == 0 else show_games if k == 1 else
                           show_chronicle if k == 2 else show_lab if k == 3 else show_dna))
        compact = pw < 720
        commands = [("pause", "PLAY" if pause else "PAUSE"), ("step", "STEP"),
                    ("slower", "SLOW" if compact else "SLOWER"),
                    ("faster", "FAST" if compact else "FASTER"),
                    ("zoom_out", "ZOOM -"), ("zoom_in", "ZOOM +"),
                    ("follow", "FOLLOW"),
                    ("sandbox", "BRUSH" if compact else "FOOD BRUSH"),
                    ("map", "MAP" if compact else "HEATMAP"),
                    ("micro", "MICRO"), ("archive", "ARCHIVE"),
                    ("events_pause", "EVENTS" if compact else "AUTO PAUSE"),
                    ("save", "SAVE"), ("lineage_tree", "TREE")]
        for (action, name), geometry in zip(commands,
                                             toolbar_grid(ox, L.toolbar_y, pw, len(commands))):
            button(pygame.Rect(*geometry), action, name,
                   active=(sandbox_brush if action == "sandbox" else
                           follow if action == "follow" else
                           pause_on_events if action == "events_pause" else
                           show_micro if action == "micro" else
                           show_archive if action == "archive" else
                           show_tree if action == "lineage_tree" else False))

        # Contextual mouse hints make the short minimum-window labels understandable.
        hints = {"pause": "Play or pause (Space)", "step": "Advance one tick (N)",
                 "slower": "Decrease simulation speed (-)", "faster": "Increase simulation speed (+)",
                 "zoom_out": "Zoom out (X)", "zoom_in": "Zoom in (Z)",
                 "follow": "Follow selected organism (L)", "sandbox": "Sandbox food brush (T) · changes are logged",
                 "map": "Toggle food stock/capacity map (F)", "micro": "Inspect neural controller (O)",
                 "archive": "Browse extinct organisms (A)",
                 "events_pause": "Pause when selected organism gives birth or dies (P)",
                 "save": "Save world and screenshot (S)", "lineage_tree": "Explore family tree (Y)"}
        hovered = next((action for rect, action in buttons if rect.collidepoint(*pygame.mouse.get_pos())), None)
        if hovered in hints:
            tooltip_w = min(pw - 20, max(170, small.size(hints[hovered])[0] + 24))
            box(pygame.Rect(ox + 10, oy + ph - 43, tooltip_w, 31), (18, 38, 43), 8)
            caption(hints[hovered], ox + 20, oy + ph - 36, TEXT, small, tooltip_w - 22)

        # Status and trend always appear; remaining sidebar space is selectable
        # instead of hiding the event feed on short displays.
        caption("WORLD STATUS" + ("  ·  REGULATION ON" if world.config.regulation_enabled else
                                      "  ·  DNA ON" if world.config.genetics_enabled else ""),
                sx, sy, GREEN, small)
        box(pygame.Rect(sx, sy + 28, sw - 9, 126), PANEL, 12)
        metrics = (("ALIVE", f"{world.population:,}"), ("TICK", f"{world.tick:,}"),
                   ("BORN", f"{world.total_births:,}"), ("DIED", f"{world.total_deaths:,}"))
        for k, (title, value) in enumerate(metrics):
            cx = sx + 15 + (k % 2) * (sw - 18) / 2
            cy = sy + 37 + (k // 2) * 61
            caption(title, cx, cy, MUTED, micro)
            caption(value, cx, cy + 14, TEXT, num)
        line_y = sy + 166
        caption("POPULATION HISTORY", sx, line_y, GREEN, small, sw - 15)
        graph = pygame.Rect(sx, line_y + 24, sw - 9, 67)
        box(graph, PANEL, 9)
        if len(history) >= 2:
            t_min, t_max = history[0][0], max(history[0][0] + 1, history[-1][0])
            top_pop = max(20, max(n for _, n, _ in history) * 1.12)
            coords = [(graph.x + 8 + (tick - t_min) / (t_max - t_min) * (graph.w - 16),
                       graph.y + graph.h - 8 - pop / top_pop * (graph.h - 16))
                      for tick, pop, _ in history]
            pygame.draw.lines(screen, GREEN, False, coords, 2)
        section_y = graph.bottom + 13
        tabs = (("specimen", "SPECIMEN"), ("events", "EVENTS"), ("lineage", "LINEAGE"))
        tab_gap = 5
        tab_w = int((sw - 12 - 2 * tab_gap) / 3)
        for k, (name, display) in enumerate(tabs):
            button(pygame.Rect(sx + k * (tab_w + tab_gap), section_y, tab_w, 30),
                   "tab:" + name, display, active=side_tab == name)
        inspect_y = section_y + 39
        inspect_h = max(112, min(224, h - inspect_y - 76))
        box(pygame.Rect(sx, inspect_y, sw - 9, inspect_h), PANEL, 11)
        detail = world.specimen(selected_id) if selected_id is not None else None
        if side_tab == "specimen":
            if detail:
                caption(f"#{selected_id}  ·  GENERATION {detail['generation']}",
                        sx + 12, inspect_y + 12, GOLD, small, sw - 28)
                caption(("ALIVE" if detail['alive'] else f"DEAD · {detail['cause']}") +
                        f"  |  age {detail['age']}", sx + 12, inspect_y + 38, TEXT, small)
                caption((f"Parent #{detail['parent_id']}" if detail['parent_id'] >= 0 else "Founder") +
                        f"   ·   offspring {detail['offspring']}",
                        sx + 12, inspect_y + 64, MUTED, small, sw - 25)
                caption(f"Food eaten {detail['food_harvested']:.1f}   ·   distance {detail['distance_traveled']:.1f}",
                        sx + 12, inspect_y + 90, MUTED, small, sw - 25)
                caption(f"Born tick {detail['born_tick']}   ·   first food " +
                        (str(detail['first_meal_tick']) if detail['first_meal_tick'] >= 0 else "not observed"),
                        sx + 12, inspect_y + 115, MUTED, micro, sw - 24)
                if inspect_h >= 165:
                    caption(("G DNA  ·  Y family  ·  O brain" if world.config.genetics_enabled else
                             "O microscope  ·  Y family  ·  G DNA  ·  H help"), sx + 12,
                            inspect_y + 142, GREEN, micro, sw - 24)
                if inspect_h >= 190 and detail['alive']:
                    amount = min(1., max(0., detail['final_energy'] / world.config.reproduction_threshold))
                    caption(f"ENERGY {detail['final_energy']:.1f}", sx + 12, inspect_y + 171, MUTED, micro)
                    pygame.draw.rect(screen, (43, 62, 59), (sx + 112, inspect_y + 176, sw - 139, 10), border_radius=4)
                    pygame.draw.rect(screen, GREEN, (sx + 112, inspect_y + 176,
                                     int((sw - 139) * amount), 10), border_radius=4)
            else:
                caption("Select a creature on the map.", sx + 12, inspect_y + 24, TEXT, small, sw - 25)
                caption("Follow its lifetime, ancestry and decisions.", sx + 12,
                        inspect_y + 55, MUTED, small, sw - 25)
                caption("Use A for the extinct-specimen archive.", sx + 12,
                        inspect_y + 86, GREEN, small, sw - 25)
        elif side_tab == "events":
            recent = list(reversed(world.observation_log[-7:]))
            if not recent:
                caption("Births and deaths will be logged here.", sx + 12, inspect_y + 20, MUTED, small, sw - 25)
            for k, event in enumerate(recent[:max(2, (inspect_h - 16) // 24)]):
                text = (f"T{event['tick']}  " + (f"Born #{event['id']} ← #{event['parent_id']}"
                         if event['kind'] == 'birth' else f"#{event['id']} died · {event['cause']}"))
                caption(text, sx + 12, inspect_y + 12 + k * 24,
                        GREEN if event['kind'] == 'birth' else CORAL, micro, sw - 25)
        elif side_tab == "lineage":
            if detail:
                kids = world.relatives(selected_id)
                caption(f"#{selected_id}  ·  parent #{detail['parent_id']}" +
                        (f"  + #{detail.get('parent2_id', -1)}" if detail.get('parent2_id', -1) >= 0 else ""), sx + 12,
                        inspect_y + 14, GOLD, small)
                caption(f"Recorded children: {detail['offspring']}", sx + 12,
                        inspect_y + 41, MUTED, small)
                if detail['parent_id'] >= 0:
                    button(pygame.Rect(sx + 12, inspect_y + 72, sw - 35, 30),
                           'parent', f"INSPECT PARENT #{detail['parent_id']}")
                if kids and inspect_h >= 150:
                    button(pygame.Rect(sx + 12, inspect_y + 110, sw - 35, 30),
                           'child', f"LAST CHILD #{kids[-1]}")
                if inspect_h >= 167:
                    chain = world.ancestry(selected_id, limit=4)
                    caption("ANCESTORS " + (" ← ".join('#' + str(i) for i in chain) if chain else "founder"),
                            sx + 12, inspect_y + 155, GREEN, micro, sw - 25)
            else:
                caption("Choose an organism to explore its family.", sx + 12,
                        inspect_y + 24, MUTED, small, sw - 28)

        # Bottom strip has a visible mode and top interactions rather than a
        # giant scrolling text line with clipped shortcut instructions.
        footer = (f"{'PAUSED / GAME' if modal_pause else 'PAUSED' if pause else 'LIVE'}  ·  {sim_clock.rate:g} ticks/sec  ·  "
                  f"food growth {world.config.growth_rate:.3f}  ·  cost {world.config.move_cost:.2f}  ·  "
                  + ("Q cheats  ·  E games  ·  D chronicle  ·  G DNA  ·  H help" if w < 1260 else
                   "Q cheats  ·  E games  ·  D chronicle  ·  W A/B lab  ·  G DNA  ·  H help"))
        caption(footer, 27, h - 19, GREEN if not pause else GOLD, micro, w - 60)
        if time.monotonic() < notice_until:
            box(pygame.Rect(ox + 5, oy + ph - 88, min(pw - 10, 515), 33), (27, 53, 56), 8)
            caption(notice, ox + 16, oy + ph - 82, TEXT, small, min(pw - 40, 490))
        if show_help:
            hrect = pygame.Rect(ox + max(12, (pw - 555) // 2), oy + 34,
                                min(555, pw - 24), min(376, ph - 42))
            box(hrect, (18, 37, 44), 14, GREEN)
            caption("FIELD GUIDE  ·  PRESS H TO CLOSE", hrect.x + 18, hrect.y + 17, GREEN, ui)
            explanations = (
                "CLICK a cute creature to inspect it. L follows the selected creature.",
                "Q CHEATS · E GAMES (includes Genome Detective) · D CHRONICLE.",
                "MOUSE WHEEL zooms; RIGHT-DRAG pans; Z/X also zoom.",
                "SPACE pauses; N advances a tick; +/- changes ticks/second.",
                "P toggles pause when selected specimen has a child or dies.",
                "A extinct archive; O microscope; Y family tree; U/K relatives.",                "T toggles the SANDBOX BRUSH. Click terrain to add nutrients.",
                "SANDBOX interventions are logged in saved checkpoints.",
                "F changes terrain view; [ ] change growth live; I restarts layout.",
                "B switches wall mode; M moves patches; C changes motion cost.",
                "R restarts only after pressing twice; I terrain also confirms.",
                "S saves full state, specimen archive, traces and screenshot.",                "Genome rules, reproduction and mortality are NOT scripted.",
                "This is an evolving simulation, not evidence of consciousness.",
            )
            for k, line in enumerate(explanations):
                caption(line, hrect.x + 18, hrect.y + 51 + k * 21,
                        TEXT if k < 4 else MUTED, small, hrect.w - 40)
        if show_journal:
            jr = pygame.Rect(ox + max(20, (pw - 548) // 2), oy + 55,
                             min(pw - 40, 548), min(ph - 80, 425))
            box(jr, (17, 37, 44), 13, GREEN)
            caption("FIELD NOTES  ·  J TO CLOSE", jr.x + 17, jr.y + 13, GREEN, ui)
            discoveries = (
                ("First descendant", world.total_births > 0),
                ("Five-generation lineage", any(e['tag'] == 'five_generations' for e in world.notable_events)),
                ("Observed starvation", world.death_causes.get("starvation", 0) > 0),
                ("Observed old-age mortality", world.death_causes.get("age", 0) > 0),
                ("Observed relocation", world.patch_moves > 0),
                ("Changed the living environment", bool(world.manual_interventions)),
                ("A novel regulatory gene appeared", world.regulatory_new_genes > 0),
                ("A regulatory chromosome rearranged", world.regulatory_new_chromosomes > 0),
            )
            for k, (title, done) in enumerate(discoveries):
                caption(("✓  " if done else "○  ") + title,
                        jr.x + 22, jr.y + 55 + k * 35,
                        GREEN if done else MUTED, small, jr.w - 35)
            note = (world.notable_events[-1]['message'] if world.notable_events else
                    "Events are derived from the actual simulated population")
            caption("LATEST: " + note, jr.x + 17, jr.bottom - 30, MUTED, micro, jr.w - 24)
        # Detailed overlays use REAL organism state; no fictional dialogue.
        if show_archive:
            if cached_archive_deaths != world.total_deaths:
                cached_archive_rows = (world.life_archive.recent(2500) if
                                       hasattr(world.life_archive, "recent") else
                                       sorted(world.life_archive.values(),
                                             key=lambda item: (item['died_tick'], item['id']), reverse=True))
                cached_archive_deaths = world.total_deaths
            recent_dead = cached_archive_rows
            r = pygame.Rect(ox + 12, oy + 43, max(130, pw - 24), max(140, ph - 58))
            box(r, (17, 36, 43), 11, GREEN)
            caption(f"EXTINCT SPECIMENS  ·  {len(world.life_archive):,} archived  ·  A closes",
                    r.x + 13, r.y + 9, GREEN, ui, r.w - 25)
            if not recent_dead and world.total_deaths:
                caption("Historical deaths predate specimen archiving.",
                        r.x + 15, r.y + 65, MUTED, small, r.w - 30)
                caption("New deaths will appear here as the world continues.",
                        r.x + 15, r.y + 89, TEXT, small, r.w - 30)
            elif not recent_dead:
                caption("No deaths recorded yet. The archive will fill as organisms die.",
                        r.x + 15, r.y + 70, TEXT, small, r.w - 30)
            visible = min(len(recent_dead), max(1, (r.h - 100) // 31), 12)
            archive_offset = min(archive_offset, max(0, len(recent_dead) - visible))
            for k, specimen in enumerate(recent_dead[archive_offset:archive_offset + visible]):
                ly = r.y + 44 + k * 31
                row_rect = pygame.Rect(r.x + 10, ly, r.w - 20, 28)
                button(row_rect, f"select:{specimen['id']}",
                       f"#{specimen['id']:>5}   Gen {specimen['generation']:>2}   Age {specimen['age']:>3}   "
                       f"{specimen['cause']:<11}   Offspring {specimen['offspring']}",
                       active=selected_id == specimen['id'])
            button(pygame.Rect(r.x + 14, r.bottom - 42, 104, 30),
                   "archive_newer", "NEWER ↑")
            caption(f"{archive_offset + 1 if recent_dead else 0}–"
                    f"{min(len(recent_dead), archive_offset + visible)} of {len(recent_dead)}",
                    r.x + 132, r.bottom - 35, MUTED, small, r.w - 260)
            button(pygame.Rect(r.right - 119, r.bottom - 42, 104, 30),
                   "archive_older", "OLDER ↓")
        if show_tree:
            r = pygame.Rect(ox + 12, oy + 43, max(130, pw - 24), max(145, ph - 58))
            box(r, (17, 36, 43), 11, GREEN)
            caption("PERSISTENT LINEAGE TREE  ·  Y closes", r.x + 14, r.y + 10, GREEN, ui, r.w - 25)
            detail = world.specimen(selected_id) if selected_id is not None else None
            if detail is None:
                caption("Select an organism on the map or in the archive to view its family.",
                        r.x + 15, r.y + 73, TEXT, small, r.w - 28)
            else:
                ancestors = list(reversed(world.ancestry(selected_id, limit=4)))
                caption("ANCESTORS   oldest → parent", r.x + 16, r.y + 48, MUTED, micro)
                count = max(1, len(ancestors))
                ancestor_width = min(130, int((r.w - 32) / count) - 6)
                for k, anc in enumerate(ancestors):
                    a = world.specimen(anc)
                    rx = r.x + 15 + int((r.w - 36) * (k + .5) / count) - ancestor_width // 2
                    if a is not None:
                        button(pygame.Rect(rx, r.y + 69, ancestor_width, 29),
                               f"select:{anc}", f"#{anc} · G{a['generation']}")
                    else:
                        box(pygame.Rect(rx, r.y + 69, ancestor_width, 29), PANEL, 8)
                        caption(f"#{anc} unknown", rx + 6, r.y + 75, MUTED, micro,
                                ancestor_width - 12)
                    if k:
                        pygame.draw.line(screen, GREEN, (rx - 9, r.y + 83),
                                         (rx - 2, r.y + 83), 2)
                pygame.draw.line(screen, (88, 148, 119),
                                 (r.centerx, r.y + 102), (r.centerx, r.y + 129), 2)
                button(pygame.Rect(r.centerx - 105, r.y + 130, 210, 43),
                       f"select:{selected_id}",
                       f"#{selected_id}  ·  G{detail['generation']}  ·  " +
                       ("living" if detail['alive'] else "deceased"), active=True)
                pygame.draw.line(screen, (88, 148, 119),
                                 (r.centerx, r.y + 174), (r.centerx, r.y + 194), 2)
                children = world.relatives(selected_id, limit=9, offset=tree_offset)
                caption(f"KNOWN OFFSPRING   {detail['offspring']} recorded  ·  showing {tree_offset + 1}–{tree_offset + len(children)}", r.x + 16, r.y + 190,
                        MUTED, micro, r.w - 25)
                cols = 3
                cw = int((r.w - 38) / cols)
                for k, child in enumerate(children):
                    ly = r.y + 216 + (k // cols) * 37
                    lx = r.x + 12 + (k % cols) * cw
                    child_data = world.specimen(child)
                    button(pygame.Rect(lx, ly, cw - 6, 29), f"select:{child}",
                           f"#{child}  G{child_data['generation']} " +
                           ("alive" if child_data['alive'] else "dead"))
                if not children:
                    caption("No recorded offspring", r.x + 16, r.y + 226, TEXT, small)
                button(pygame.Rect(r.x + 12, r.bottom - 62, 135, 33),
                       "tree_previous", "← PREVIOUS 9")
                button(pygame.Rect(r.right - 150, r.bottom - 62, 136, 33),
                       "tree_next", "NEXT 9 →")
                caption("Relationships use parent IDs; historical biographies may be missing.",
                        r.x + 14, r.bottom - 22, MUTED, micro, r.w - 24)
        if show_micro:
            r = pygame.Rect(ox + 10, oy + 43, max(130, pw - 20), max(160, ph - 58))
            box(r, (17, 36, 43), 10, GREEN)
            caption("NEURAL MICROSCOPE  ·  O closes", r.x + 14, r.y + 11, GREEN, ui, r.w - 25)
            detail = world.specimen(selected_id) if selected_id is not None else None
            if detail is None:
                caption("Select an organism to inspect its inherited motor controller.",
                        r.x + 15, r.y + 63, TEXT, small, r.w - 30)
            else:
                genes = np.asarray(detail['genome'])
                idx = np.flatnonzero(world.ids == selected_id)
                sensors = None
                if len(idx):
                    turn, speed, perception = world.controls()
                    j = int(idx[0])
                    sensors = perception[j]
                    caption(f"#{selected_id}  TURN {turn[j]:+.3f} rad / tick   SPEED {speed[j]:.3f} units / tick",
                            r.x + 14, r.y + 43, GOLD, small, r.w - 28)
                else:
                    caption(f"#{selected_id}  ·  archived genome  ·  no live sensory readings",
                            r.x + 14, r.y + 43, GOLD, small, r.w - 28)
                from .simulation import SENSORS
                header_y = r.y + 78
                caption("SENSOR INPUT", r.x + 15, header_y, MUTED, micro)
                caption("TURN WEIGHT", r.x + r.w * .42, header_y, MUTED, micro)
                caption("SPEED WEIGHT", r.x + r.w * .70, header_y, MUTED, micro)
                row_h = max(22, min(30, (r.h - 156) // 8))
                for k, sensor_name in enumerate(SENSORS):
                    yy = header_y + 23 + k * row_h
                    caption(f"{sensor_name} " + (f"{sensors[k]:.2f}" if sensors is not None else "—"),
                            r.x + 14, yy, TEXT, micro, int(r.w * .40) - 22)
                    for m, left in ((0, .42), (1, .70)):
                        x0 = int(r.x + r.w * left)
                        value = float(genes[m, k])
                        center = x0 + 27
                        pygame.draw.line(screen, (68, 83, 86), (center, yy + 8), (center + 46, yy + 8), 1)
                        length = int(max(-34, min(34, value / 5 * 34)))
                        pygame.draw.line(screen, CORAL if value < 0 else GREEN,
                                         (center, yy + 8), (center + length, yy + 8), 4)
                        caption(f"{value:+.2f}", center + 53, yy, MUTED, micro, 54)
                trace = world.watch_traces.get(selected_id, [])
                caption(f"Trace: {len(trace)} recorded samples  ·  turn is not food-seeking by definition",
                        r.x + 14, r.bottom - 30, MUTED, micro, r.w - 22)
        if show_dna:
            r = pygame.Rect(ox + 12, oy + 44, max(130, pw - 24), max(185, ph - 58))
            box(r, (44, 29, 57), 12, PINK)
            caption("GENOME LAB  ·  G CLOSES  ·  INHERITED BIOLOGICAL TRAITS", r.x + 15, r.y + 12,
                    PINK, ui, r.w - 29)
            detail = world.specimen(selected_id) if selected_id is not None else None
            if not world.config.genetics_enabled:
                caption("This checkpoint uses the historical neural-only genome.",
                        r.x + 18, r.y + 83, TEXT, small, r.w - 35)
                caption("Start a fresh viewer without --resume to enable DNA.",
                        r.x + 18, r.y + 113, MUTED, small, r.w - 35)
            elif detail is None:
                caption("Click a creature to inspect its genes and family.", r.x + 18,
                        r.y + 84, TEXT, small, r.w - 36)
            else:
                dna = np.asarray(detail["body_dna"], dtype=float)
                copies = np.asarray(detail["gene_copies"], dtype=int)
                phen = phenotype_summary(dna, copies)
                caption(f"SPECIMEN #{selected_id}  ·  GEN {detail['generation']}   ·   " +
                        ("ALIVE" if detail["alive"] else "ARCHIVED"),
                        r.x + 18, r.y + 51, TEXT, small)
                caption(f"BIO LOCI {len(LOCI)}  ·  NEURAL 16  ·  BIO COPIES {int(copies.sum())}  "
                        f"·  REG GENES {len(detail.get('regulatory_genes', []))}",
                        r.x + 18, r.y + 76, MUTED, micro, r.w - 30)
                if world.config.regulation_enabled:
                    program = detail.get("regulatory_genes", [])
                    chromosome_count = len({g["chromosome"] for g in program})
                    caption(f"REGULATORY DNA: {len(program)} genes / {chromosome_count} chromosomes  ·  "
                            "mutations create new circuits", r.x + 18, r.y + 115, PINK, micro,
                            r.w - 35)
                caption("ANCESTRY: " + (f"#{detail['parent_id']}" if detail['parent_id'] >= 0 else "founder") +
                        (f"  +  #{detail.get('parent2_id')}" if detail.get('parent2_id', -1) >= 0 else ""),
                        r.x + 18, r.y + 98, GOLD, small)
                compact_genes = r.h < 440
                row_gap = 16 if compact_genes else 26
                base_y = r.y + (146 if world.config.regulation_enabled else 130)
                for k, name in enumerate(LOCI):
                    yy = base_y + k * row_gap
                    if yy + 18 >= r.bottom - 38:
                        break
                    gene = float(dna[k])
                    dose = int(copies[k])
                    caption(name.replace("_", " ").upper(), r.x + 18, yy, TEXT, micro, 155)
                    caption(f"{gene:+.2f}   x{dose}", r.x + 188, yy, MUTED, micro, 92)
                    center = r.x + 336
                    pygame.draw.line(screen, (108, 79, 122), (center - 34, yy + 9), (center + 34, yy + 9), 2)
                    length = int(max(-33, min(33, gene * dose / 2.5 * 33)))
                    pygame.draw.line(screen, GREEN if length >= 0 else CORAL,
                                     (center, yy + 9), (center + length, yy + 9), 5)
                    trait_key = {"body_size": "size", "metabolic_efficiency": "maintenance",
                                 "digestion": "food_gain", "turning": "agility"}.get(name, name)
                    if trait_key in phen and name not in ("pigment", "spots") and r.w >= 590:
                        caption(f"effect x{phen[trait_key]:.2f}", r.x + 410, yy, MUTED, micro, 160)
                if world.config.regulation_enabled and r.h >= 465:
                    first = detail.get("regulatory_genes", [])[:2]
                    for k, g in enumerate(first):
                        caption(f"Chr {g['chromosome']} · {g['reads']} → {g['affects']}  "
                                f"({g['operation']}, {g['strength']:+.2f})",
                                r.x + 18, r.bottom - 83 + k * 18, GOLD, micro, r.w - 35)
                caption(f"Body x{phen['size']:.2f}    Metabolism x{phen['maintenance']:.2f}    "
                        f"Digestion x{phen['food_gain']:.2f}    Lifespan x{phen['longevity']:.2f}",
                        r.x + 17, r.bottom - 31, GREEN, micro, r.w - 30)
        if show_dna and world.config.regulation_enabled and selected_id is not None:
            detail = world.specimen(selected_id)
            if detail is not None:
                button(pygame.Rect(r.right - 207, r.y + 9, 190, 32), "regulation_page",
                       "VIEW BIOLOGY" if dna_page == "regulation" else "VIEW REGULATORS")
                if dna_page == "regulation":
                    inner = pygame.Rect(r.x + 12, r.y + 46, r.w - 24, r.h - 59)
                    box(inner, (35, 27, 53), 9, PLUM)
                    genes = detail.get("regulatory_genes", [])
                    chromosomes = len(set(g["chromosome"] for g in genes))
                    caption(f"#{selected_id}: {len(genes)} inherited instructions, "
                            f"{chromosomes} chromosomes · ordered regulation program",
                            inner.x + 12, inner.y + 10, PINK, small, inner.w - 24)
                    caption("Each rule reads a signal and changes an allowed pathway; no Python execution",
                            inner.x + 12, inner.y + 34, MUTED, micro, inner.w - 24)
                    if detail["alive"]:
                        j = np.flatnonzero(world.ids == selected_id)
                        if len(j):
                            actual = world.regulation()[int(j[0])]
                            caption(f"LIVE EXPRESSION: maintenance {actual[0]:+.2f}  "
                                    f"digestion {actual[1]:+.2f}  propulsion {actual[2]:+.2f}  "
                                    f"steering {actual[7]:+.2f}",
                                    inner.x + 12, inner.y + 56, GREEN, micro, inner.w - 24)
                    start = 82
                    available = min(10, max(0, (inner.h - start - 39) // 24))
                    for offset, gene in enumerate(genes[reg_page * 10: reg_page * 10 + available]):
                        yy = inner.y + start + offset * 24
                        operation = ("NONCODING" if gene["operation"] == "noncoding"
                                     else gene["operation"].upper())
                        caption(f"CHR {gene['chromosome']}  ·  #{gene['id']}  {operation}  "
                                f"{gene['reads']} -> {gene['affects']}  {gene['strength']:+.2f}",
                                inner.x + 12, yy, MUTED if gene["operation"] == "noncoding" else TEXT,
                                micro, inner.w - 23)
                    if len(genes) > available:
                        button(pygame.Rect(inner.x + 12, inner.bottom - 34, 94, 27),
                               "reg_previous", "PREVIOUS")
                        button(pygame.Rect(inner.x + 115, inner.bottom - 34, 94, 27),
                               "reg_next", "NEXT")
                    caption(f"Program page {reg_page + 1} · noncoding DNA can mutate into active genes",
                            inner.right - 330, inner.bottom - 25, GOLD, micro, 320)
        # The play panels are deliberately outside the scientific simulation.
        if show_cheats or show_games or show_chronicle or show_lab:
            modal_w, modal_h = min(660, pw - 24), min(425, ph - 55)
            r = pygame.Rect(ox + (pw - modal_w) // 2, oy + 49, modal_w, modal_h)
            box(r, (45, 33, 61), 16, PINK)
            pygame.draw.line(screen, PLUM, (r.x + 17, r.y + 46),
                             (r.right - 17, r.y + 46), 1)
            if show_cheats:
                caption("SUGAR-RUSH CHEAT MENU  ·  Q CLOSES", r.x + 18, r.y + 12, PINK, ui)
                caption("CHEATS CHANGE THE WORLD. SAVE FILES ARE FLAGGED NON-SCIENTIFIC.",
                        r.x + 18, r.y + 55, CORAL, micro, r.w - 32)
                choices = (("feast", "1  CANDY RAIN", "Refill all habitat food"),
                           ("energy", "2  CUPCAKE BOOST", "Give selected creature +40 energy"),
                           ("babies", "3  BABY PARADE", "Make 8 genetically identical babies"),
                           ("immortal", "4  COZY FOREVER", "Disable aging and maintenance"),
                           ("gene_spark", "5  DNA SPARK", "Mutate selected creature (logged cheat)"))
                for i, (action, label, description) in enumerate(choices):
                    yy = r.y + 82 + i * 64
                    if yy + 60 > r.bottom - 4:
                        break
                    button(pygame.Rect(r.x + 17, yy, min(225, r.w - 40), 37),
                           "cheat:" + action, label)
                    caption(description, r.x + 23, yy + 43, MUTED, small, r.w - 38)
            elif show_games:
                caption("LITTLE LAB GAMES  ·  E CLOSES", r.x + 18, r.y + 12, PINK, ui)
                button(pygame.Rect(r.x + 17, r.y + 54, 152, 35), "game:berries", "BERRY HUNT")
                button(pygame.Rect(r.x + 180, r.y + 54, 178, 35), "game:speed", "SPEED DETECTIVE")
                button(pygame.Rect(r.x + 370, r.y + 54, max(100, r.w - 390), 35),
                       "game:genes", "GENOME DETECTIVE")
                caption(f"Observation stars  {games.correct} / {games.attempts}   ·   no ecological effects",
                        r.x + 19, r.y + 96, MUTED, small, r.w - 38)
                ch = games.challenge
                if ch is not None:
                    caption(ch.title + "   —   " + ch.prompt, r.x + 18, r.y + 126,
                            TEXT, small, r.w - 38)
                    row_start = r.y + 162
                    for i, label in enumerate(ch.labels):
                        yy = row_start + i * 70
                        if yy + 61 > r.bottom - 18:
                            break
                        box(pygame.Rect(r.x + 15, yy, r.w - 30, 60), (66, 49, 81), 9)
                        button(pygame.Rect(r.x + 20, yy + 9, 48, 42), f"answer:{i}", str(i + 1),
                               active=(ch.chosen == i))
                        caption(label, r.x + 84, yy + 9, TEXT, small, r.w - 130)
                        # Visual clues reflect REAL measurements, not random decoration.
                        # The actual numeric value is withheld until the answer.
                        value = max(0, ch.values[i])
                        if ch.kind == "berries":
                            qty = max(1, min(12, int(value * 1.35) + 1))
                            for dot in range(qty):
                                pgx = r.x + 87 + dot * 12
                                if pgx < r.right - 25:
                                    pygame.draw.circle(screen, (250, 139, 185), (pgx, yy + 42), 5)
                        else:
                            bar = int(min(180, value / (16 if ch.kind == "genes"
                                                   else max(.0001, world.config.max_speed)) * 180))
                            pygame.draw.line(screen, (255, 162, 205),
                                             (r.x + 90, yy + 45), (r.x + 90 + bar, yy + 45), 5)
                        if ch.chosen is not None:
                            caption(f"Measured: {ch.values[i]:.3f}", r.right - 160,
                                    yy + 11, GREEN if i == ch.winner else MUTED, micro, 140)
                    if ch.chosen is not None:
                        caption("Correct! ✦" if ch.award else f"Answer was card {ch.winner + 1}",
                                r.x + 20, r.bottom - 27, GREEN if ch.award else GOLD, small)
            elif show_chronicle:
                caption("LIVING CHRONICLE  ·  D CLOSES", r.x + 18, r.y + 12, PINK, ui)
                caption("Real events & specimen paths · recent positions replay, NOT world rewind",
                        r.x + 18, r.y + 54, MUTED, micro, r.w - 36)
                button(pygame.Rect(r.x + 16, r.y + 80, 155, 36), "bookmark", "★ BOOKMARK")
                button(pygame.Rect(r.x + 183, r.y + 80, 160, 36), "replay", "REPLAY TRACK")
                caption("BOOKMARKED SPECIMENS", r.x + 18, r.y + 137, PINK, micro)
                for j, specimen_id in enumerate(chronicle.bookmarks[-6:]):
                    xx = r.x + 17 + (j % 3) * min(165, (r.w - 30) // 3)
                    yy = r.y + 159 + (j // 3) * 40
                    button(pygame.Rect(xx, yy, min(152, (r.w - 35) // 3), 33),
                           f"select:{specimen_id}", f"#{specimen_id}  ♥")
                start_y = r.y + 252
                caption("LATEST VERIFIED EVENTS", r.x + 17, start_y, PINK, micro)
                for j, event in enumerate(reversed(chronicle.events[-5:])):
                    caption(f"T{event.get('tick','?')} · {event.get('kind','event')} · "
                            f"#{event.get('id','?')}", r.x + 20, start_y + 21 + j * 21,
                            MUTED, micro, r.w - 36)
                if replay_index >= 0 and selected_id is not None:
                    track = chronicle.traces.get(str(selected_id), [])
                    if track:
                        caption(f"REPLAY #{selected_id}: position {replay_index + 1} / {len(track)}",
                                r.x + 18, r.bottom - 30, GREEN, micro, r.w - 36)
            elif show_lab:
                caption("TWIN-WORLD LAB  ·  W CLOSES", r.x + 18, r.y + 12, PINK, ui)
                caption("Clone one world twice; change ONE rule in the right-hand copy.",
                        r.x + 18, r.y + 57, MUTED, small, r.w - 38)
                for i, (key, title) in enumerate(LAB_VARIANTS.items()):
                    y = r.y + 86 + i * 45
                    button(pygame.Rect(r.x + 17, y, r.w - 34, 37), "lab:" + key,
                           f"{i + 1}  {title}", active=lab is not None and lab.mode == key)
                if lab is not None:
                    caption(f"MATCHED TICKS: {lab.steps} / {lab.limit}   ·   " +
                            ("COMPLETE" if lab.done else "RUNNING"),
                            r.x + 20, r.y + 235, GREEN, small, r.w - 35)
                    for column, (name, sample) in enumerate((("CONTROL", lab.control),
                                                              ("ONE RULE CHANGED", lab.changed))):
                        xx = r.x + 20 + column * ((r.w - 45) // 2)
                        box(pygame.Rect(xx, r.y + 268, (r.w - 54) // 2, 88),
                            (58, 44, 78), 10)
                        caption(name, xx + 10, r.y + 277, PINK, micro)
                        caption(f"Alive {sample.population}   Born {sample.total_births - lab.initial_births}",
                                xx + 10, r.y + 304, TEXT, small, (r.w - 70) // 2)
                        caption(f"Dead {sample.total_deaths - lab.initial_deaths}", xx + 10, r.y + 328,
                                MUTED, micro)
                    caption("One paired demonstration, NOT a replicated scientific finding.",
                            r.x + 17, r.bottom - 31, MUTED, micro, r.w - 35)
        pygame.display.flip()
        frame_durations.append((time.perf_counter() - draw_start) * 1000)
        if getattr(args, "smoke_frames", 0) and frame >= args.smoke_frames:
            if getattr(args, "screenshot", None):
                Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)
                pygame.image.save(screen, str(args.screenshot))
            running = False
        if pending_save:
            # Save AFTER rendering: previous versions captured the prior frame,
            # or a blank screen if S was pressed on the first frame.
            pending_save = False
            directory = Path("results/viewer")
            try:
                directory.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                saving_path = directory / f"world_{stamp}.npz"
                world.save(saving_path)
                chronicle.save(str(saving_path) + ".observer.json", games, checkpoint=saving_path)
                pygame.image.save(screen, str(directory / f"screenshot_{stamp}.png"))
                if lab is not None:
                    (directory / f"lab_{stamp}.json").write_text(
                        json.dumps(lab.report(), indent=2), encoding="utf-8")
                announce(f"Saved world & screenshot to results/viewer/ · tick {world.tick}")
            except OSError as exc:
                announce(f"Save failed: {exc}")
        clock.tick(35)
    if getattr(args, "qa_report", None):
        report = {
            'frames': len(frame_durations),
            'render_mean_ms': float(np.mean(frame_durations)) if frame_durations else None,
            'render_p95_ms': float(np.percentile(frame_durations, 95)) if frame_durations else None,
            'world_tick': world.tick, 'population': world.population,
            'window_size': list(screen.get_size()),
            'ui': {'selected_id': selected_id, 'paused': pause, 'zoom': zoom_steps[zoom_index],
                   'active_overlay': ('archive' if show_archive else 'microscope' if show_micro else
                                      'tree' if show_tree else 'help' if show_help else
                                      'journal' if show_journal else
                                      'cheats' if show_cheats else 'games' if show_games else
                                      'chronicle' if show_chronicle else 'lab' if show_lab else 'dna' if show_dna else None),
                   'pause_on_events': pause_on_events, 'interventions': len(world.manual_interventions),
                   'mini_attempts': games.attempts, 'mini_correct': games.correct,
                   'bookmarks': len(chronicle.bookmarks),
                   'lab_steps': lab.steps if lab is not None else 0},
            'qa_actions_executed': qa_events_executed,
            'note': 'Measured render+event-frame work, excluding clock.tick wait and platform compositor',
        }
        Path(args.qa_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.qa_report).write_text(json.dumps(report, indent=2), encoding='utf-8')
    pygame.quit()
