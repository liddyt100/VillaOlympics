# main.py
# Villa Olympics — Race Leaderboard (Pygame)
# Customise: swap assets/background.jpeg and avatar images in assets/avatars, edit players.csv

import os
import csv
import math
import time
import pygame
from pygame import gfxdraw
from PIL import Image

# =========================
# Config – tweak as desired
# =========================
WINDOW_W, WINDOW_H = 1200, 700
FPS = 60

ASSETS_DIR = "assets"
BACKGROUND_IMG = "assets/background.jpeg"
PLAYERS_CSV = "players.csv"

# Layout
TRACK_LEFT = 40
TRACK_RIGHT = 860            # race pane width ~820px; rest is leaderboard
TOP_MARGIN = 90
LANE_HEIGHT = 90
LANE_GAP = 18

LEADERBOARD_X = 880
LEADERBOARD_W = WINDOW_W - LEADERBOARD_X - 30

# Visuals
AVATAR_SIZE = 72
AVATAR_OUTLINE = (255, 255, 255)
AVATAR_OUTLINE_THICK = 3

NAME_COLOUR = (245, 245, 245)
SCORE_COLOUR = (220, 220, 220)
UI_ACCENT = (255, 215, 0)         # gold
PILL_BG = (0, 0, 0, 150)          # translucent pill behind leaderboard rows
ROW_RADIUS = 14
GRID_COLOUR = (255, 255, 255, 40)

# Anim
EASING_SPEED = 6.0  # higher = snappier interpolation

# =========================

def load_background(path, size):
    if not os.path.isfile(path):
        surf = pygame.Surface(size)
        surf.fill((25, 25, 30))
        return surf
    img = Image.open(path).convert("RGB").resize(size, Image.LANCZOS)
    mode_str = img.mode
    return pygame.image.fromstring(img.tobytes(), img.size, mode_str)

def circle_avatar(path, diameter):
    """Load an image and return a circular-cropped pygame.Surface of given diameter, with high quality."""
    if not os.path.isfile(path):
        surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(surf, (120, 120, 140), (diameter//2, diameter//2), diameter//2)
        return surf

    img = Image.open(path).convert("RGBA")
    # Crop to square first (center crop)
    min_side = min(img.size)
    left = (img.width - min_side) // 2
    top = (img.height - min_side) // 2
    img = img.crop((left, top, left + min_side, top + min_side))
    img = img.resize((diameter, diameter), Image.LANCZOS)

    # High-quality antialiased mask
    mask_size = diameter * 3
    mask = Image.new("L", (mask_size, mask_size), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).ellipse((0, 0, mask_size-1, mask_size-1), fill=255)
    mask = mask.resize((diameter, diameter), Image.LANCZOS)
    img.putalpha(mask)

    mode_str = img.mode
    pgsurf = pygame.image.fromstring(img.tobytes(), img.size, mode_str)
    return pgsurf

def draw_rounded_rect_alpha(surf, rect, colour_rgba, radius):
    """Draw a rounded rect with alpha onto surf."""
    x, y, w, h = rect
    temp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(temp, colour_rgba, pygame.Rect(0, 0, w, h), border_radius=radius)
    surf.blit(temp, (x, y))

class Player:
    def __init__(self, name, points, avatar_path):
        self.name = name
        self.points = points
        self.avatar_path = avatar_path
        self.avatar = circle_avatar(avatar_path, AVATAR_SIZE)
        # race progress [0..1] target and smoothed current for animation
        self.progress_target = 0.0
        self.progress_current = 0.0

    def set_avatar(self, path):
        self.avatar_path = path
        self.avatar = circle_avatar(path, AVATAR_SIZE)

class Scoreboard:
    def __init__(self):
        self.players = []  # list[Player]
        self.last_loaded = 0

    def load_from_csv(self, path):
        players = []
        if not os.path.isfile(path):
            return
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                name = row.get("name", "").strip()
                pts_str = row.get("points", "0").strip()
                avatar = row.get("avatar", "").strip()
                if not name:
                    continue
                try:
                    pts = float(pts_str)
                except:
                    pts = 0.0
                players.append(Player(name, pts, avatar))
        self.players = players
        self.last_loaded = time.time()

    def set_target_progresses(self):
        if not self.players:
            return
        max_pts = 100.0  # Fixed finish line at 100 points
        # Avoid divide by zero; if all zero, everyone at start
        for p in self.players:
            p.progress_target = 0.0 if max_pts <= 0 else (p.points / max_pts)

    def update_animation(self, dt):
        # Smoothly approach target
        for p in self.players:
            # simple exponential smoothing
            p.progress_current += (p.progress_target - p.progress_current) * min(1.0, EASING_SPEED * dt)

    def sort_for_leaderboard(self):
        # Highest first, tie-break by name
        return sorted(self.players, key=lambda p: (-p.points, p.name.lower()))

class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Villa Olympics — Leaderboard")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()
        self.bg = load_background(BACKGROUND_IMG, (WINDOW_W, WINDOW_H))
        self.sb = Scoreboard()
        self.sb.load_from_csv(PLAYERS_CSV)
        self.sb.set_target_progresses()
        self.inc_buttons = []  # (rect, player_index, delta)

        # Fonts
        self.font_big = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 22)
        self.font_small = pygame.font.SysFont("Arial", 18)

        self.running = True

    def reset_animation(self):
        for p in self.sb.players:
            p.progress_current = 0.0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.sb.load_from_csv(PLAYERS_CSV)
                    self.sb.set_target_progresses()
                elif event.key == pygame.K_SPACE:
                    self.reset_animation()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                for rect, player, delta in self.inc_buttons:
                    if rect.collidepoint(mouse_pos):
                        player.points += delta
                        self.sb.set_target_progresses()

    def draw_grid(self, surf):
        # vertical tick marks at 0%, 25%, 50%, 75%, 100%
        grid = pygame.Surface((TRACK_RIGHT - TRACK_LEFT, WINDOW_H), pygame.SRCALPHA)
        for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
            x = int((TRACK_LEFT) + frac * (TRACK_RIGHT - TRACK_LEFT))
            pygame.draw.line(grid, GRID_COLOUR, (x - TRACK_LEFT, TOP_MARGIN - 30), (x - TRACK_LEFT, WINDOW_H - 40), 1)
        surf.blit(grid, (TRACK_LEFT, 0))

    def draw_race(self):
        # Title
        title = self.font_big.render("Villa Olympics", True, NAME_COLOUR)
        self.screen.blit(title, (TRACK_LEFT, 24))

        # Grid lines
        self.draw_grid(self.screen)

        # Dynamically calculate lane height and gap
        n = len(self.sb.players)
        available_height = WINDOW_H - TOP_MARGIN - 40  # leave space at bottom
        min_lane_h = 40
        max_lane_h = 90
        min_gap = 6
        max_gap = 18

        if n > 0:
            # Try to fit all lanes and gaps in available space
            lane_h = min(max_lane_h, max(min_lane_h, (available_height - (n - 1) * min_gap) // n))
            gap = min(max_gap, max(min_gap, (available_height - n * lane_h) // max(1, n - 1)))
        else:
            lane_h = max_lane_h
            gap = max_gap

        for i, p in enumerate(self.sb.players):
            lane_y = TOP_MARGIN + i * (lane_h + gap)

            # Lane baseline
            pygame.draw.line(self.screen, (255, 255, 255, 50), (TRACK_LEFT, lane_y + lane_h), (TRACK_RIGHT, lane_y + lane_h), 1)

            # Racer position (with padding so avatars don’t clip)
            min_x = TRACK_LEFT + AVATAR_SIZE//2
            max_x = TRACK_RIGHT - AVATAR_SIZE//2
            x = min_x + int(p.progress_current * (max_x - min_x))
            y = lane_y + lane_h//2

            # Avatar outline
            pygame.gfxdraw.aacircle(self.screen, x, y, AVATAR_SIZE//2 + AVATAR_OUTLINE_THICK, AVATAR_OUTLINE)
            pygame.gfxdraw.filled_circle(self.screen, x, y, AVATAR_SIZE//2 + AVATAR_OUTLINE_THICK, AVATAR_OUTLINE)

            # Avatar image
            self.screen.blit(p.avatar, (x - AVATAR_SIZE//2, y - AVATAR_SIZE//2))

            # Name tag above
            name_surf = self.font_small.render(p.name, True, NAME_COLOUR)
            name_rect = name_surf.get_rect(center=(x, y - AVATAR_SIZE//2 - 16))
            draw_rounded_rect_alpha(self.screen, (name_rect.x - 8, name_rect.y - 4, name_rect.w + 16, name_rect.h + 8), (0, 0, 0, 140), 10)
            self.screen.blit(name_surf, name_rect)

            # Finish flag for each lane
            flag_x = TRACK_RIGHT
            pygame.draw.line(self.screen, (255, 255, 255), (flag_x, lane_y), (flag_x, lane_y + lane_h), 3)
            for j in range(6):
                col = (255, 255, 255) if j % 2 == 0 else (0, 0, 0)
                pygame.draw.rect(self.screen, col, pygame.Rect(flag_x - 16, lane_y + j*int(lane_h/6), 16, int(lane_h/6)))

    def draw_leaderboard(self):
        self.inc_buttons = []
        title = self.font_big.render("Leaderboard", True, UI_ACCENT)
        self.screen.blit(title, (LEADERBOARD_X, 24))

        sorted_players = self.sb.sort_for_leaderboard()
        n = len(sorted_players)
        available_height = WINDOW_H - 100  # leave space for title and footer
        min_row_h = 40
        max_row_h = 76
        spacing = 8

        # Dynamically calculate row height and spacing
        if n > 0:
            row_h = min(max_row_h, max(min_row_h, (available_height - (n - 1) * spacing) // n))
            start_y = 70
        else:
            row_h = max_row_h
            start_y = 70

        for idx, p in enumerate(sorted_players):
            y = start_y + idx * (row_h + spacing)
            rect = (LEADERBOARD_X, y, LEADERBOARD_W, row_h)
            draw_rounded_rect_alpha(self.screen, rect, PILL_BG, ROW_RADIUS)

            # Rank circle
            rank = idx + 1
            rank_text = self.font_med.render(f"{rank}", True, (30, 30, 35))
            circle_r = max(14, row_h // 3)
            circle_x = LEADERBOARD_X + 18 + circle_r
            circle_y = y + row_h // 2
            pygame.gfxdraw.filled_circle(self.screen, circle_x, circle_y, circle_r, UI_ACCENT)
            pygame.gfxdraw.aacircle(self.screen, circle_x, circle_y, circle_r, UI_ACCENT)
            self.screen.blit(rank_text, rank_text.get_rect(center=(circle_x, circle_y)))

            # Mini avatar
            mini_size = max(24, row_h - 28)
            mini = pygame.transform.smoothscale(p.avatar, (mini_size, mini_size))
            self.screen.blit(mini, (LEADERBOARD_X + 60, y + (row_h - mini_size)//2))

            # Name & points
            name_s = self.font_med.render(p.name, True, NAME_COLOUR)
            self.screen.blit(name_s, (LEADERBOARD_X + 120, y + 8))

            pts_txt = f"{int(p.points) if float(p.points).is_integer() else p.points}"
            pts_s = self.font_small.render(f"{pts_txt} pts", True, SCORE_COLOUR)
            self.screen.blit(pts_s, (LEADERBOARD_X + 120, y + row_h // 2))

            # Button and score sizing/positioning
            button_size = max(16, row_h // 3)
            button_gap = 16
            right_margin = 24

            plus_x = LEADERBOARD_X + LEADERBOARD_W - right_margin - button_size
            score_y = y + row_h // 2
            minus_x = plus_x - button_size - button_gap

            # Draw minus button
            minus_rect = pygame.Rect(minus_x, score_y - button_size // 2, button_size, button_size)
            pygame.draw.rect(self.screen, (200, 60, 60), minus_rect, border_radius=4)
            minus_surf = self.font_small.render("–", True, (255, 255, 255))
            minus_surf_rect = minus_surf.get_rect(center=minus_rect.center)
            self.screen.blit(minus_surf, minus_surf_rect)
            self.inc_buttons.append((minus_rect, p, -1))

            # Draw plus button
            plus_rect = pygame.Rect(plus_x, score_y - button_size // 2, button_size, button_size)
            pygame.draw.rect(self.screen, (60, 200, 60), plus_rect, border_radius=4)
            plus_surf = self.font_small.render("+", True, (255, 255, 255))
            plus_surf_rect = plus_surf.get_rect(center=plus_rect.center)
            self.screen.blit(plus_surf, plus_surf_rect)
            self.inc_buttons.append((plus_rect, p, +1))

            # # Center the score between the two buttons
            # score_center_x = (minus_rect.right + plus_rect.left) // 2
            # score_surf = self.font_small.render(str(p.points), True, SCORE_COLOUR)
            # score_rect = score_surf.get_rect(center=(score_center_x, score_y))
            # self.screen.blit(score_surf, score_rect)

    def update(self, dt):
        self.sb.update_animation(dt)

    def draw(self):
        self.screen.blit(self.bg, (0, 0))
        self.draw_race()
        self.draw_leaderboard()

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                self.running = False
            self.update(dt)
            self.draw()
        pygame.quit()

if __name__ == "__main__":
    App().run()
