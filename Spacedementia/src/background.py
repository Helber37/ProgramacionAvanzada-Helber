import random
import math
import sys
import os

import pygame

# Permitir importar agujeronegro.py desde la raíz del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from agujeronegro import BlackHole
from config import HEIGHT, WIDTH


class Background:
    """Campo de estrellas parallax con colores sutiles y efecto de brillo."""

    # Paletas de color por nivel (colores sutiles para estrellas especiales)
    LEVEL_ACCENTS = [
        # Nivel 1: azules fríos
        [(100, 140, 255), (80, 120, 200), (150, 180, 255)],
        # Nivel 2: cyans
        [(80, 220, 220), (100, 255, 200), (60, 180, 180)],
        # Nivel 3: verdes/amarillos
        [(120, 255, 80), (200, 255, 100), (180, 220, 60)],
        # Nivel 4: naranjas/rojos
        [(255, 160, 60), (255, 100, 60), (255, 200, 80)],
        # Nivel 5+: magentas/rojos intensos
        [(255, 80, 120), (200, 60, 255), (255, 60, 80)],
    ]

    def __init__(self, level=1):
        self.level = level
        self.frame_count = 0
        self.stars = []
        self.nebula_particles = []
        self.black_hole = None
        self._generate(level)

    def _generate(self, level):
        """Genera el campo de estrellas según el nivel."""
        self.level = level
        self.stars = []
        self.nebula_particles = []

        accents = self.LEVEL_ACCENTS[min(level - 1, 4)]

        # 3 capas de parallax con diferentes velocidades
        # Capa 1: estrellas lejanas (lentas, pequeñas, tenues)
        for _ in range(120):
            self.stars.append(self._make_star(
                speed_range=(0.3, 0.8),
                size_range=(1, 1),
                brightness_range=(60, 120),
                accents=accents,
                color_chance=0.05,
                twinkle_chance=0.02,
            ))

        # Capa 2: estrellas medias
        for _ in range(80 + level * 10):
            self.stars.append(self._make_star(
                speed_range=(1.0, 2.0),
                size_range=(1, 2),
                brightness_range=(100, 180),
                accents=accents,
                color_chance=0.12,
                twinkle_chance=0.08,
            ))

        # Capa 3: estrellas cercanas (rápidas, grandes, brillantes)
        for _ in range(30 + level * 5):
            self.stars.append(self._make_star(
                speed_range=(2.5, 4.0 + level * 0.3),
                size_range=(2, 3),
                brightness_range=(160, 255),
                accents=accents,
                color_chance=0.2,
                twinkle_chance=0.15,
            ))

        # Partículas de nebulosa sutil (solo niveles 3+)
        if level >= 3:
            accent = random.choice(accents)
            for _ in range(15 + (level - 3) * 8):
                self.nebula_particles.append({
                    "x": random.randint(0, WIDTH),
                    "y": random.randint(0, HEIGHT),
                    "speed": random.uniform(0.2, 0.6),
                    "size": random.randint(15, 40),
                    "color": accent,
                    "alpha": random.randint(8, 20),
                })

        # Agujero negro de fondo (posición estratégica según nivel)
        # Aparece desde nivel 2, se hace más grande en niveles altos
        if level >= 2:
            bh_radius = 35 + level * 8  # crece con el nivel
            # Posición: zona derecha-superior, lejos del jugador (que está a la izquierda)
            bh_x = int(WIDTH * 0.72)
            bh_y = int(HEIGHT * 0.35)
            self.black_hole = BlackHole(bh_x, bh_y, radius=bh_radius)
        else:
            self.black_hole = None

    def _make_star(self, speed_range, size_range, brightness_range,
                   accents, color_chance, twinkle_chance):
        b = random.randint(*brightness_range)

        # Decidir color
        r = random.random()
        if r < color_chance * 0.4:
            # Roja sutil
            color = (min(255, b + 80), max(0, b - 60), max(0, b - 80))
        elif r < color_chance * 0.7:
            # Naranja/amarilla sutil
            color = (min(255, b + 40), min(255, b + 10), max(0, b - 60))
        elif r < color_chance * 0.9:
            # Azulada sutil
            color = (max(0, b - 40), max(0, b - 20), min(255, b + 60))
        elif r < color_chance:
            # Color del acento del nivel
            accent = random.choice(accents)
            ratio = b / 255
            color = (int(accent[0] * ratio), int(accent[1] * ratio), int(accent[2] * ratio))
        else:
            # Blanca normal
            color = (b, b, b)

        return {
            "x": random.randint(0, WIDTH),
            "y": random.randint(0, HEIGHT),
            "speed": random.uniform(*speed_range),
            "size": random.choice(range(size_range[0], size_range[1] + 1)),
            "color": color,
            "base_color": color,
            "twinkle": random.random() < twinkle_chance,
            "twinkle_speed": random.uniform(0.03, 0.12),
            "twinkle_offset": random.uniform(0, math.pi * 2),
        }

    def update(self, level=None):
        if level is not None and level != self.level:
            self._generate(level)

        for star in self.stars:
            star["x"] -= star["speed"]
            if star["x"] < -5:
                star["x"] = WIDTH + random.randint(0, 20)
                star["y"] = random.randint(0, HEIGHT)

        for p in self.nebula_particles:
            p["x"] -= p["speed"]
            if p["x"] < -p["size"]:
                p["x"] = WIDTH + p["size"]
                p["y"] = random.randint(0, HEIGHT)

        # Actualizar agujero negro
        if self.black_hole:
            self.black_hole.update(1.0)

        self.frame_count += 1

    def _draw_star(self, screen, star):
        """Dibuja una estrella individual con efecto twinkle."""
        x = int(star["x"])
        y = int(star["y"])
        color = star["base_color"]
        size = star["size"]

        if star["twinkle"]:
            t = self.frame_count * star["twinkle_speed"] + star["twinkle_offset"]
            glow = (math.sin(t) + 1) / 2
            r = min(255, int(color[0] * (0.4 + glow * 0.6)))
            g = min(255, int(color[1] * (0.4 + glow * 0.6)))
            b = min(255, int(color[2] * (0.4 + glow * 0.6)))
            color = (r, g, b)

            if glow > 0.85 and size >= 2:
                halo_alpha = int(30 * (glow - 0.85) / 0.15)
                halo_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(
                    halo_surf,
                    (color[0], color[1], color[2], halo_alpha),
                    (4, 4), 4,
                )
                screen.blit(halo_surf, (x - 4, y - 4))

        if size <= 1:
            screen.set_at((x, y), color)
        else:
            pygame.draw.circle(screen, color, (x, y), size)

    def draw(self, screen):
        # 1. Nebulosa de fondo (lo más lejano)
        for p in self.nebula_particles:
            surf = pygame.Surface((p["size"] * 2, p["size"] * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                surf,
                (p["color"][0], p["color"][1], p["color"][2], p["alpha"]),
                (p["size"], p["size"]),
                p["size"],
            )
            screen.blit(surf, (int(p["x"]) - p["size"], int(p["y"]) - p["size"]))

        # 2. Estrellas lejanas (capa 1: size == 1, speed < 1)
        for star in self.stars:
            if star["size"] <= 1:
                self._draw_star(screen, star)

        # 3. AGUJERO NEGRO (entre estrellas lejanas y cercanas = profundidad)
        if self.black_hole:
            self.black_hole.draw(screen)

        # 4. Estrellas medias y cercanas (capas 2 y 3: pasan por delante)
        for star in self.stars:
            if star["size"] > 1:
                self._draw_star(screen, star)
