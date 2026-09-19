import random

import pygame

from config import BLUE, GREEN, RED, WHITE, YELLOW


class Explosion:
    """Partícula de explosión sin física, solo visualización"""

    # Colores disponibles para las explosiones
    COLORS = [RED, YELLOW, GREEN, BLUE, WHITE, (255, 100, 0)]  # Naranja

    def __init__(self, x, y, num_particles=8):
        self.x = x
        self.y = y
        self.num_particles = num_particles
        self.particles = []
        self.lifetime = 30  # Frames que durará la explosión
        self.age = 0
        self.create_particles()

    def create_particles(self):
        """Crear partículas en todas las direcciones"""
        for _ in range(self.num_particles):
            # Ángulo aleatorio (0-360 grados)
            angle = random.uniform(0, 360)
            # Velocidad aleatoria entre 1 y 3 píxeles por frame
            speed = random.uniform(1, 3)
            # Tamaño aleatorio (2-6 píxeles)
            size = random.randint(2, 6)
            # Color aleatorio
            color = random.choice(self.COLORS)

            # Calcular velocidad en X e Y (más simple que trigonometría)
            vx = speed * (1 if random.random() > 0.5 else -1) * random.random()
            vy = speed * (1 if random.random() > 0.5 else -1) * random.random()

            self.particles.append(
                {
                    "x": self.x,
                    "y": self.y,
                    "vx": vx,
                    "vy": vy,
                    "size": size,
                    "color": color,
                    "alpha": 255,  # Transparencia (0-255)
                }
            )

    def update(self):
        """Actualizar edad y partículas"""
        self.age += 1

        # Mover partículas
        for particle in self.particles:
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            # Desvanecerse gradualmente
            particle["alpha"] = int(255 * (1 - self.age / self.lifetime))

    def draw(self, screen):
        """Dibujar todas las partículas"""
        for particle in self.particles:
            # Dibujar círculos pequeños
            pygame.draw.circle(
                screen,
                particle["color"],
                (int(particle["x"]), int(particle["y"])),
                particle["size"],
            )

    def is_dead(self):
        """Verificar si la explosión terminó"""
        return self.age >= self.lifetime
