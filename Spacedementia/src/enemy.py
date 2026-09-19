import math

import pygame

from bullet import Bullet
from config import HEIGHT, RED, YELLOW


class Enemy:
    def __init__(self, x, y, size, speed, agil=False):
        self.x = x
        self.y = y
        self.size = size
        # Limitar velocidad: enemigos nunca más rápidos que sus balas (10)
        self.speed = min(speed, 9)
        self.agil = agil  # True para enemigos rápidos
        self.direction_x = 1  # 1 o -1 para zigzag

    def shoot(self):
        # Anterior: Bullet(..., "DOWN")
        # Actual: Bullet(..., "LEFT") hacia la izquierda
        return Bullet(self.x, self.y, 10, "LEFT")

    def move(self):
        # Anterior: self.y += self.speed (movimiento hacia abajo)
        # Actual: self.x -= self.speed (movimiento hacia la izquierda)
        self.x -= self.speed

        # Enemigos ágiles se mueven en zigzag (now vertical)
        if self.agil:
            self.y += self.direction_x * 2
            # Cambiar dirección si sale del rango (anterior: 30-770 para WIDTH=800)
            if self.y < 30 or self.y > HEIGHT - 30:
                self.direction_x *= -1

    def rotate_point(self, point, angle):
        """Rotar un punto alrededor del origen (0,0)"""
        s = math.sin(angle)
        c = math.cos(angle)
        x, y = point
        return (x * c - y * s, x * s + y * c)

    def draw(self, screen, player_x=None, player_y=None):
        # Cambiar color según si es ágil
        color = YELLOW if self.agil else RED

        # Apuntar en la dirección de movimiento (hacia la izquierda)
        # Ángulo fijo: π radianes = 180 grados = izquierda
        angle = math.pi

        # Puntos del triángulo sin rotar (apunta hacia la derecha por defecto)
        points = [
            (self.size / 2, 0),  # Punta (derecha)
            (-self.size / 2, -self.size / 2),  # Arriba-izquierda
            (-self.size / 2, self.size / 2),  # Abajo-izquierda
        ]

        # Rotar puntos hacia el ángulo de movimiento
        rotated_points = [self.rotate_point(p, angle) for p in points]

        # Trasladar al centro (self.x, self.y)
        final_points = [(p[0] + self.x, p[1] + self.y) for p in rotated_points]

        pygame.draw.polygon(screen, color, final_points)
