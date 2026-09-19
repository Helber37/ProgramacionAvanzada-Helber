import math
import random

import pygame


class BlackHole:
    """Agujero negro estilo Interstellar con partículas retro arcade."""

    def __init__(self, x, y, radius=80):
        self.x = x
        self.y = y
        self.radius = radius
        self.angle = 0
        self.tilt = 0.28  # inclinación del disco (perspectiva)

        # --- Disco de acreción horizontal (partículas orbitando) ---
        self.disk_particles = []
        for _ in range(350):
            dist = random.uniform(radius * 1.15, radius * 2.2)
            self.disk_particles.append({
                "dist": dist,
                "angle": random.uniform(0, 2 * math.pi),
                "size": random.randint(1, 3),
                "speed": random.uniform(0.015, 0.07) * (radius / dist),
                "layer": random.choice(["back", "front"]),
            })

        # --- Arco de lensing (luz doblada por encima y debajo) ---
        self.lensing_particles = []
        for _ in range(180):
            ang = random.uniform(-math.pi * 0.85, math.pi * 0.85)
            self.lensing_particles.append({
                "base_angle": ang,
                "dist": random.uniform(radius * 1.02, radius * 1.35),
                "size": random.randint(1, 2),
                "brightness": random.uniform(0.5, 1.0),
                "speed_offset": random.uniform(0.005, 0.02),
            })

        # --- Partículas cayendo en espiral ---
        self.falling = []
        for _ in range(40):
            self.falling.append({
                "dist": random.uniform(radius * 1.2, radius * 2.5),
                "angle": random.uniform(0, 2 * math.pi),
                "radial_speed": -random.uniform(0.3, 1.2),
                "size": random.randint(1, 3),
                "angle_speed": random.uniform(0.03, 0.08),
            })

        # Pre-render de la esfera 3D (no cambia cada frame)
        self._sphere_surf = None
        self._build_sphere()

    def _build_sphere(self):
        """Pre-renderiza la esfera oscura con gradiente 3D."""
        r = self.radius
        size = r * 2 + 20
        self._sphere_surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx, cy = size // 2, size // 2

        # Glow exterior tenue (naranja/rojo)
        for i in range(8):
            gr = r + 8 - i
            alpha = max(0, 15 - i * 2)
            pygame.draw.circle(
                self._sphere_surf, (180, 60, 10, alpha), (cx, cy), gr
            )

        # Gradiente esférico: capas concéntricas
        layers = 25
        for i in range(layers):
            t = i / layers
            lr = int(r * (1 - t * 0.92))
            # Borde: rojo/naranja tenue → centro: negro puro
            red = max(0, int(50 * (1 - t) ** 2.5))
            green = max(0, int(15 * (1 - t) ** 3))
            blue = max(0, int(20 * (1 - t) ** 3))
            pygame.draw.circle(self._sphere_surf, (red, green, blue), (cx, cy), lr)

        # Centro negro absoluto
        pygame.draw.circle(self._sphere_surf, (0, 0, 0), (cx, cy), int(r * 0.55))

        # Reflejo sutil arriba-izquierda (simula luz 3D)
        hx = cx - int(r * 0.22)
        hy = cy - int(r * 0.28)
        for j in range(int(r * 0.25), 0, -1):
            alpha = int(8 * (1 - j / (r * 0.25)))
            pygame.draw.circle(
                self._sphere_surf, (100, 50, 70, alpha), (hx, hy), j
            )

    def _disk_color(self, dist):
        """Color del disco según distancia: blanco/amarillo cerca → rojo/naranja lejos."""
        t = (dist - self.radius) / (self.radius * 1.2)
        t = max(0.0, min(1.0, t))
        r = 255
        g = int(200 * (1 - t * 0.7))
        b = int(120 * (1 - t))
        return (r, g, b)

    def update(self, dt):
        self.angle += 0.012 * dt

        for p in self.disk_particles:
            p["angle"] += p["speed"] * dt

        for lp in self.lensing_particles:
            lp["base_angle"] += lp["speed_offset"] * dt

        for f in self.falling:
            f["dist"] += f["radial_speed"] * dt
            f["angle"] += f["angle_speed"] * dt
            if f["dist"] <= self.radius * 0.9:
                f["dist"] = random.uniform(self.radius * 1.5, self.radius * 2.5)
                f["radial_speed"] = -random.uniform(0.3, 1.2)
                f["angle"] = random.uniform(0, 2 * math.pi)

    def draw(self, screen):
        # === CAPA TRASERA del disco (partículas detrás de la esfera) ===
        for p in self.disk_particles:
            if p["layer"] == "back":
                self._draw_disk_particle(screen, p)

        # === Partículas cayendo (detrás) ===
        for f in self.falling:
            ang = f["angle"] + self.angle
            sin_a = math.sin(ang)
            if sin_a > 0:  # detrás
                self._draw_falling(screen, f, ang)

        # === ESFERA 3D ===
        r = self.radius
        screen.blit(
            self._sphere_surf,
            (self.x - r - 10, self.y - r - 10)
        )

        # === ANILLO de fotones (lensing gravitacional) ===
        # Arco superior
        self._draw_lensing_arc(screen, top=True)
        # Arco inferior
        self._draw_lensing_arc(screen, top=False)

        # === CAPA FRONTAL del disco (partículas delante de la esfera) ===
        for p in self.disk_particles:
            if p["layer"] == "front":
                self._draw_disk_particle(screen, p)

        # === Partículas cayendo (delante) ===
        for f in self.falling:
            ang = f["angle"] + self.angle
            sin_a = math.sin(ang)
            if sin_a <= 0:  # delante
                self._draw_falling(screen, f, ang)

    def _draw_disk_particle(self, screen, p):
        """Dibuja una partícula del disco de acreción."""
        rad = p["dist"]
        ang = p["angle"] + self.angle
        px = self.x + rad * math.cos(ang)
        py = self.y + rad * math.sin(ang) * self.tilt

        # No dibujar si está oculta detrás de la esfera
        dx = px - self.x
        dy = py - self.y
        if dx * dx + dy * dy < (self.radius * 0.8) ** 2:
            return

        color = self._disk_color(rad)
        pygame.draw.circle(screen, color, (int(px), int(py)), p["size"])

        # Glow sutil para partículas cercanas
        if rad < self.radius * 1.5 and p["size"] >= 2:
            glow_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 150, 40, 25), (4, 4), 4)
            screen.blit(glow_surf, (int(px) - 4, int(py) - 4))

    def _draw_falling(self, screen, f, ang):
        """Dibuja partícula cayendo en espiral."""
        rad = f["dist"]
        px = self.x + rad * math.cos(ang)
        py = self.y + rad * math.sin(ang) * self.tilt
        t = max(0.0, min(1.0, 1 - (rad - self.radius) / (self.radius * 0.8)))
        intensity = min(255, int(120 + 135 * t))
        color = (intensity, min(255, int(intensity * 0.5)), min(255, int(intensity * 0.15)))
        pygame.draw.circle(screen, color, (int(px), int(py)), f["size"])

    def _draw_lensing_arc(self, screen, top=True):
        """Dibuja el arco de lensing (luz doblada sobre/bajo la esfera)."""
        for lp in self.lensing_particles:
            ang = lp["base_angle"]
            dist = lp["dist"]

            # Posición en arco vertical (simula luz curvándose)
            px = self.x + dist * math.sin(ang) * 0.9
            if top:
                py = self.y - abs(dist * math.cos(ang)) * 0.95
            else:
                py = self.y + abs(dist * math.cos(ang)) * 0.95

            # Solo dibujar fuera de la esfera
            dx = px - self.x
            dy = py - self.y
            if dx * dx + dy * dy < (self.radius * 0.85) ** 2:
                continue

            b = lp["brightness"]
            r = int(255 * b)
            g = int(180 * b)
            bl = int(80 * b)
            pygame.draw.circle(screen, (r, g, bl), (int(px), int(py)), lp["size"])


if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Black Hole - Interstellar Arcade")
    clock = pygame.time.Clock()
    bh = BlackHole(400, 300, radius=80)

    running = True
    while running:
        dt = clock.tick(60) / 16.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        bh.update(dt)
        screen.fill((5, 2, 10))
        bh.draw(screen)
        pygame.display.flip()

    pygame.quit()
