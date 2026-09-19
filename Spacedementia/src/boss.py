import random

import pygame

from bullet import Bullet
from config import BOSS_HP, HEIGHT, WHITE, WIDTH


class Boss:
    """Clase base para todos los jefes finales.

    Subclases deben implementar:
        - draw(screen): renderizado visual del boss
        - _create_bullets(): patron de disparo especifico
    Opcionalmente pueden sobreescribir:
        - get_hit_rect(): hitbox personalizado
        - move(): comportamiento de movimiento extra
    """

    def __init__(self, level, name="BOSS", size=80):
        self.name = name
        self.size = size
        self.x = WIDTH - self.size - 40
        self.y = HEIGHT // 2
        self.base_x = self.x
        self.hp = BOSS_HP + (level - 1) * 50
        self.max_hp = self.hp
        self.speed_y = 2
        self.direction_y = 1  # 1 = abajo, -1 = arriba
        self.alive = True
        self.level = level

        # IA de carga (embestida hacia la izquierda)
        self.charging = False
        self.charge_speed = 6
        self.charge_target_x = WIDTH // 2
        self.charge_cooldown = 0
        self.charge_cooldown_max = 150
        self.returning = False

        # Disparo
        self.shoot_cooldown = 0
        self.shoot_rate = 20

    def take_damage(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def move(self):
        if not self.alive:
            return

        if not self.charging and not self.returning:
            self.y += self.speed_y * self.direction_y
            if self.y <= self.size:
                self.direction_y = 1
            elif self.y >= HEIGHT - self.size:
                self.direction_y = -1

            self.charge_cooldown -= 1
            if self.charge_cooldown <= 0 and random.randint(0, 100) < 2:
                self.charging = True

        elif self.charging:
            self.x -= self.charge_speed
            if self.x <= self.charge_target_x:
                self.charging = False
                self.returning = True

        elif self.returning:
            self.x += self.charge_speed
            if self.x >= self.base_x:
                self.x = self.base_x
                self.returning = False
                self.charge_cooldown = self.charge_cooldown_max

    def shoot(self):
        """Dispara balas segun el patron del boss."""
        if not self.alive:
            return []

        self.shoot_cooldown -= 1
        if self.shoot_cooldown > 0:
            return []

        self.shoot_cooldown = self.shoot_rate
        return self._create_bullets()

    def _create_bullets(self):
        """Sobreescribir en subclases para definir patron de disparo."""
        return [
            Bullet(self.x - self.size // 2, self.y, 12, "LEFT"),
        ]

    def draw(self, screen):
        """Sobreescribir en subclases para el renderizado."""
        pass

    def get_hit_rect(self):
        """Retorna el hitbox como pygame.Rect. Sobreescribir si es necesario."""
        return pygame.Rect(
            self.x - self.size // 2,
            self.y - self.size // 2,
            self.size,
            self.size,
        )

    def draw_health_bar(self, screen):
        """Dibuja la barra de vida del jefe en la parte superior de la pantalla."""
        if not self.alive:
            return

        bar_width = 400
        bar_height = 20
        bar_x = WIDTH // 2 - bar_width // 2
        bar_y = 10

        # Fondo de la barra (gris oscuro)
        pygame.draw.rect(
            screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height)
        )

        # Barra de vida (rojo -> amarillo -> verde segun HP)
        hp_ratio = self.hp / self.max_hp
        fill_width = int(bar_width * hp_ratio)
        if hp_ratio > 0.5:
            bar_color = (int(255 * (1 - hp_ratio) * 2), 255, 0)
        else:
            bar_color = (255, int(255 * hp_ratio * 2), 0)
        pygame.draw.rect(
            screen, bar_color, (bar_x, bar_y, fill_width, bar_height)
        )

        # Borde de la barra
        pygame.draw.rect(
            screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 2
        )

        # Texto del jefe
        font = pygame.font.SysFont("monospace", 14, bold=True)
        label = font.render(
            f"{self.name}  {self.hp}/{self.max_hp}", 1, WHITE
        )
        label_rect = label.get_rect(center=(WIDTH // 2, bar_y + bar_height // 2))
        screen.blit(label, label_rect)
