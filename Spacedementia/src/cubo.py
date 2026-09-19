import math

import pygame

from boss import Boss
from bullet import Bullet


class CubeBoss(Boss):
    """Primer jefe final: cubo 3D rotante que dispara desde sus caras visibles."""

    FACE_COLORS = [
        (255, 0, 0),      # Rojo - inferior
        (0, 255, 0),      # Verde - derecha
        (0, 0, 255),      # Azul - superior
        (255, 255, 0),    # Amarillo - izquierda
        (255, 0, 255),    # Magenta - frente
        (0, 255, 255),    # Cian - atras
    ]

    # 8 vertices del cubo centrado en el origen (lado = 2)
    VERTICES = [
        (-1, -1, -1),  # 0
        ( 1, -1, -1),  # 1
        ( 1, -1,  1),  # 2
        (-1, -1,  1),  # 3
        (-1,  1, -1),  # 4
        ( 1,  1, -1),  # 5
        ( 1,  1,  1),  # 6
        (-1,  1,  1),  # 7
    ]

    # 6 caras (4 indices de vertices cada una)
    FACES = [
        [0, 1, 2, 3],  # inferior (y=-1)
        [1, 5, 6, 2],  # derecha (x=1)
        [4, 5, 6, 7],  # superior (y=1)
        [0, 4, 7, 3],  # izquierda (x=-1)
        [3, 2, 6, 7],  # frente (z=1)
        [0, 1, 5, 4],  # atras (z=-1)
    ]

    # Vectores normales de cada cara (antes de rotar)
    FACE_NORMALS = [
        ( 0, -1,  0),  # inferior
        ( 1,  0,  0),  # derecha
        ( 0,  1,  0),  # superior
        (-1,  0,  0),  # izquierda
        ( 0,  0,  1),  # frente
        ( 0,  0, -1),  # atras
    ]

    def __init__(self, level):
        super().__init__(level, name="CUBO", size=80)
        self.angle_x = 0
        self.angle_y = 0
        self.rot_speed = 0.02
        self.fov = 256
        self.z_distance = 4

    def _rotate(self, point, ang_x, ang_y):
        """Rota un punto 3D alrededor de los ejes X e Y."""
        x, y, z = point
        # Rotacion en X
        cos_x, sin_x = math.cos(ang_x), math.sin(ang_x)
        y1 = y * cos_x - z * sin_x
        z1 = y * sin_x + z * cos_x
        y, z = y1, z1
        # Rotacion en Y
        cos_y, sin_y = math.cos(ang_y), math.sin(ang_y)
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        return (x1, y, z1)

    def _project(self, point_3d):
        """Proyecta un punto 3D a coordenadas 2D en pantalla."""
        factor = self.fov / (self.z_distance + point_3d[2])
        x_proj = point_3d[0] * factor + self.x
        y_proj = -point_3d[1] * factor + self.y
        return (int(x_proj), int(y_proj))

    def move(self):
        super().move()
        if self.alive:
            self.angle_x += self.rot_speed * 0.5
            self.angle_y += self.rot_speed

    def _get_rotated_normals(self):
        """Retorna las normales de cada cara despues de rotar."""
        return [self._rotate(n, self.angle_x, self.angle_y) for n in self.FACE_NORMALS]

    def _get_face_centers_2d(self):
        """Retorna el centro 2D proyectado de cada cara."""
        rotated = [self._rotate(v, self.angle_x, self.angle_y) for v in self.VERTICES]
        centers = []
        for face in self.FACES:
            cx = sum(rotated[i][0] for i in face) / 4
            cy = sum(rotated[i][1] for i in face) / 4
            cz = sum(rotated[i][2] for i in face) / 4
            centers.append(self._project((cx, cy, cz)))
        return centers

    def _create_bullets(self):
        """Dispara desde las caras visibles segun la direccion de su normal rotada."""
        bullets = []
        normals = self._get_rotated_normals()
        centers = self._get_face_centers_2d()

        for i, normal in enumerate(normals):
            nx, ny, nz = normal

            # Solo disparar desde caras visibles (normal apuntando hacia la camara: nz < 0)
            if nz >= 0:
                continue

            # Convertir normal a direccion en pantalla
            # En la proyeccion, Y se invierte (-y), asi que screen_ny = -ny
            screen_nx = nx
            screen_ny = -ny

            # Determinar direccion de disparo segun componente dominante
            if abs(screen_nx) > abs(screen_ny):
                direction = "LEFT" if screen_nx < 0 else "RIGHT"
            else:
                direction = "UP" if screen_ny < 0 else "DOWN"

            # No disparar hacia la derecha (lejos del jugador)
            if direction == "RIGHT":
                continue

            cx, cy = centers[i]
            bullets.append(Bullet(cx, cy, 10, direction))

        return bullets

    def draw(self, screen):
        if not self.alive:
            return

        rotated = [self._rotate(v, self.angle_x, self.angle_y) for v in self.VERTICES]
        projected = [self._project(v) for v in rotated]

        # Ordenar caras por profundidad (atras hacia adelante)
        face_depths = []
        for idx, face in enumerate(self.FACES):
            z_avg = sum(rotated[i][2] for i in face) / 4
            face_depths.append((z_avg, idx, face))
        face_depths.sort(key=lambda x: x[0], reverse=True)

        for _, idx, face in face_depths:
            points = [projected[i] for i in face]
            color = self.FACE_COLORS[idx]
            pygame.draw.polygon(screen, color, points, 0)
            pygame.draw.polygon(screen, (255, 255, 255), points, 2)
