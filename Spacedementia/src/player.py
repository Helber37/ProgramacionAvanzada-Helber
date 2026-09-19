import pygame

from config import BLUE, PURPLE


class Player:
    def __init__(self, x, y, size, speed, life):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed
        self.life = life
        self.powerups = {}  # Diccionario de power-ups activos {tipo: True}
        self.__shield_frames = 0  # Frames restantes de escudo activo (privado)

    def activar_escudo(self, duracion_frames=180):
        """Única forma de activar el escudo desde fuera de la clase."""
        self.__shield_frames = duracion_frames

    def esta_protegido(self):
        """Consulta de solo lectura: informa si el escudo esta activo."""
        return self.__shield_frames > 0

    def actualizar_escudo(self):
        """Reduce el contador de escudo en 1, hasta llegar a 0."""
        if self.__shield_frames > 0:
            self.__shield_frames -= 1

    def add_powerup(self, powerup_type):
        """Agregar un power-up (hasta 5 para WEAPON_RIGHT, 3 para otros frontales, 1 para otros)"""
        # WEAPON_RIGHT puede acumular hasta 5 (dispara en patrón: 1, 2, 3, 4, 5 balas)
        # WEAPON_LEFT hasta 3
        if powerup_type == "WEAPON_RIGHT":
            max_count = 5
        elif powerup_type == "WEAPON_LEFT":
            max_count = 3
        else:
            max_count = 1

        if powerup_type not in self.powerups:
            self.powerups[powerup_type] = 0

        if self.powerups[powerup_type] < max_count:
            self.powerups[powerup_type] += 1

    def remove_powerup(self, powerup_type):
        """Remover un power-up"""
        if powerup_type in self.powerups and self.powerups[powerup_type] > 0:
            self.powerups[powerup_type] -= 1
            if self.powerups[powerup_type] == 0:
                del self.powerups[powerup_type]

    def has_powerup(self, powerup_type):
        """Verificar si tiene un power-up específico"""
        return powerup_type in self.powerups and self.powerups[powerup_type] > 0

    def get_powerups_list(self):
        """Obtener lista de power-ups activos con contadores"""
        result = []
        for ptype, count in self.powerups.items():
            if count > 0:
                result.append(f"{ptype}x{count}")
        return result

    def move(self, direction):
        if direction == "LEFT":
            self.x -= self.speed
        elif direction == "RIGHT":
            self.x += self.speed
        elif direction == "UP":
            self.y -= self.speed
        elif direction == "DOWN":
            self.y += self.speed

    def draw(self, screen):
        if self.esta_protegido():
            # Anillo pulsante alrededor del jugador mientras el escudo esta activo
            pulso = 4 + int(3 * abs((self.__shield_frames % 20) - 10) / 10)
            pygame.draw.circle(
                screen, PURPLE, (self.x, self.y), self.size + 8, pulso
            )
        pygame.draw.circle(screen, BLUE, (self.x, self.y), self.size)