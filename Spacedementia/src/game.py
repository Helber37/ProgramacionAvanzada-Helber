import random

import pygame

from background import Background
from bullet import Bullet
from cubo import CubeBoss
from config import BLACK, BULLET_DAMAGE, FPS, HEIGHT, LEVEL_DURATION, PURPLE, RED, WHITE, WIDTH
from enemy import Enemy
from explosion import Explosion
from player import Player
from powerup import PowerUp


class Game:
    def __init__(self, screen, sound_manager=None, start_level=1):
        self.screen = screen
        self.sound = sound_manager
        self.player = Player(40, HEIGHT // 2, 20, 10, 3)
        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.powerups = []
        self.explosions = []
        self.score = 0
        self.level = start_level
        self.max_enemies = 5 + (3 * self.level)
        self.background = Background(self.level)
        self.paused = False
        self.auto_shoot_timer = 0
        self.game_over = False
        self.game_over_timer = 0

        # Timer de nivel (cuenta regresiva)
        self.level_timer = LEVEL_DURATION * FPS  # Frames totales del nivel
        self.boss_phase = False  # True cuando el timer llega a 0
        self.boss = None
        self.boss_minion_timer = 0

    def run_frame(self, clock):
        """Ejecuta un frame del juego. Retorna 'quit', 'menu', o None."""
        self.screen.fill(BLACK)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return "quit"
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                if event.key == pygame.K_p and not self.game_over:
                    self.paused = not self.paused

        if self.game_over:
            self.game_over_timer += 1
            self.draw_game_elements()
            pygame.display.flip()
            clock.tick(FPS)
            # Volver al menú después de 3 segundos
            if self.game_over_timer >= FPS * 3:
                return "menu"
            return None

        if not self.paused:
            self.player.actualizar_escudo()
            keys = pygame.key.get_pressed()
            if (
                keys[pygame.K_LEFT]
                and self.player.x > self.player.speed
                and self.player.life > 0
            ):
                self.player.move("LEFT")
            if (
                keys[pygame.K_RIGHT]
                and self.player.x < WIDTH - self.player.speed
                and self.player.life > 0
            ):
                self.player.move("RIGHT")
            if (
                keys[pygame.K_UP]
                and self.player.y > self.player.speed
                and self.player.life > 0
            ):
                self.player.move("UP")
            if (
                keys[pygame.K_DOWN]
                and self.player.y < HEIGHT - self.player.speed
                and self.player.life > 0
            ):
                self.player.move("DOWN")
            if keys[pygame.K_SPACE] and self.player.life > 0:
                self.bullets.append(
                    Bullet(self.player.x, self.player.y, 20, "RIGHT")
                )
                self._play_sound("shoot")

            self.update_game_state()

        self.draw_game_elements()
        pygame.display.flip()
        clock.tick(FPS)
        return None

    # Mantener compatibilidad con el loop anterior
    def run(self):
        running = True
        clock = pygame.time.Clock()
        while running:
            result = self.run_frame(clock)
            if result in ("quit", "menu"):
                running = False
        pygame.quit()

    def _play_sound(self, name):
        if self.sound:
            self.sound.play(name)

    def spawn_enemy(self):
        """Crea un enemigo con propiedades según el nivel"""
        base_speed = 5 + (self.level - 1) * 0.5
        agil_chance = min(100, 10 + (20 * self.level))
        agil = random.randint(0, 100) < agil_chance
        speed = base_speed + 2 if agil else base_speed
        x = WIDTH
        y = random.randint(30, HEIGHT - 30)
        self.enemies.append(Enemy(x, y, 30, speed, agil))

    def spawn_powerup(self, x, y):
        """Crea un power-up aleatorio"""
        powerup_types = [
            PowerUp.WEAPON_LEFT,
            PowerUp.WEAPON_RIGHT,
            PowerUp.WEAPON_DIAG_RIGHT,
            PowerUp.WEAPON_DIAG_LEFT,
            PowerUp.WEAPON_DIAG_DOWN_RIGHT,
            PowerUp.WEAPON_DIAG_DOWN_LEFT,
            PowerUp.WEAPON_UP,
            PowerUp.WEAPON_DOWN,
            PowerUp.LIFE,
            PowerUp.SHIELD,
        ]
        powerup_type = random.choice(powerup_types)
        self.powerups.append(PowerUp(x, y, powerup_type))

    def auto_shoot_weapons(self):
        """Dispara automáticamente según los power-ups activos"""
        if PowerUp.WEAPON_LEFT in self.player.powerups:
            count = self.player.powerups[PowerUp.WEAPON_LEFT]
            for i in range(count):
                offset = (
                    i - (count - 1) / 2
                ) * 8
                self.bullets.append(
                    Bullet(self.player.x, self.player.y + offset, 20, "LEFT")
                )

        if PowerUp.WEAPON_RIGHT in self.player.powerups:
            count = self.player.powerups[PowerUp.WEAPON_RIGHT]

            if count == 0:
                self.bullets.append(Bullet(self.player.x, self.player.y, 20, "RIGHT"))
            elif count == 1:
                self.bullets.append(
                    Bullet(self.player.x, self.player.y - 8, 20, "RIGHT")
                )
                self.bullets.append(
                    Bullet(self.player.x, self.player.y + 8, 20, "RIGHT")
                )
            elif count == 2:
                self.bullets.append(
                    Bullet(self.player.x, self.player.y - 12, 20, "RIGHT")
                )
                self.bullets.append(Bullet(self.player.x, self.player.y, 20, "RIGHT"))
                self.bullets.append(
                    Bullet(self.player.x, self.player.y + 12, 20, "RIGHT")
                )
            else:
                self.bullets.append(
                    Bullet(self.player.x, self.player.y - 16, 20, "RIGHT")
                )
                self.bullets.append(
                    Bullet(self.player.x, self.player.y - 4, 20, "RIGHT")
                )
                self.bullets.append(
                    Bullet(self.player.x, self.player.y + 8, 20, "RIGHT")
                )

                if count >= 3:
                    self.bullets.append(
                        Bullet(self.player.x + 20, self.player.y, 20, "RIGHT")
                    )
                if count >= 4:
                    self.bullets.append(
                        Bullet(self.player.x + 30, self.player.y, 20, "RIGHT")
                    )
                if count >= 5:
                    self.bullets.append(
                        Bullet(self.player.x + 40, self.player.y, 20, "RIGHT")
                    )

        if PowerUp.WEAPON_DIAG_LEFT in self.player.powerups:
            self.bullets.append(Bullet(self.player.x, self.player.y, 15, "DIAG_LEFT"))
        if PowerUp.WEAPON_DIAG_RIGHT in self.player.powerups:
            self.bullets.append(Bullet(self.player.x, self.player.y, 15, "DIAG_RIGHT"))
        if PowerUp.WEAPON_DIAG_DOWN_LEFT in self.player.powerups:
            self.bullets.append(Bullet(self.player.x, self.player.y, 15, "DIAG_DOWN_LEFT"))
        if PowerUp.WEAPON_DIAG_DOWN_RIGHT in self.player.powerups:
            self.bullets.append(Bullet(self.player.x, self.player.y, 15, "DIAG_DOWN_RIGHT"))
        if PowerUp.WEAPON_UP in self.player.powerups:
            self.bullets.append(Bullet(self.player.x, self.player.y, 20, "UP"))
        if PowerUp.WEAPON_DOWN in self.player.powerups:
            self.bullets.append(Bullet(self.player.x, self.player.y, 20, "DOWN"))

    def update_game_state(self):
        for bullet in self.bullets[:]:
            bullet.move()
            if bullet.y < 0 or bullet.y > HEIGHT or bullet.x < 0 or bullet.x > WIDTH:
                self.bullets.remove(bullet)

        # Disparo automático con power-ups
        if self.player.life > 0 and self.player.powerups:
            self.auto_shoot_timer += 1
            if self.auto_shoot_timer >= 10:
                self.auto_shoot_timer = 0
                self.auto_shoot_weapons()

        if self.player.life > 0 and not self.boss_phase and len(self.enemies) < self.max_enemies:
            self.spawn_enemy()

        # Subditos del boss
        if self.boss_phase and self.boss and self.boss.alive and self.player.life > 0:
            self.boss_minion_timer += 1
            if self.boss_minion_timer >= 90 and len(self.enemies) < 3:
                self.boss_minion_timer = 0
                self.spawn_enemy()

        for enemy in self.enemies[:]:
            enemy.move()
            if enemy.x < 0:
                self.enemies.remove(enemy)
            for bullet in self.bullets[:]:
                if self.check_collision(bullet, enemy):
                    self.bullets.remove(bullet)
                    self.explosions.append(
                        Explosion(enemy.x, enemy.y, num_particles=16)
                    )
                    self.enemies.remove(enemy)
                    self.score += 10
                    self._play_sound("explosion")
                    if random.randint(0, 100) < 50:
                        self.spawn_powerup(enemy.x, enemy.y)
                    break
            if self.check_attack(enemy, self.player):
                self.enemies.remove(enemy)
                if self.player.powerups:
                    loseable_powerups = [
                        p
                        for p in self.player.powerups.keys()
                        if p != PowerUp.WEAPON_RIGHT
                    ]
                    if loseable_powerups:
                        powerup_to_lose = random.choice(loseable_powerups)
                        self.player.remove_powerup(powerup_to_lose)
                    elif not self.player.esta_protegido():
                        self.player.life = max(self.player.life - 1, 0)
                elif not self.player.esta_protegido():
                    self.player.life = max(self.player.life - 1, 0)
                self._play_sound("hit")

        if self.player.life > 0:
            for enemy in self.enemies:
                if random.randint(0, 100) < 5:
                    self.enemy_bullets.append(enemy.shoot())
                    self._play_sound("enemy_shoot")

        for bullet in self.enemy_bullets[:]:
            bullet.move()
            if bullet.x < 0 or bullet.x > WIDTH or bullet.y < 0 or bullet.y > HEIGHT:
                self.enemy_bullets.remove(bullet)

        # Colisiones entre balas del jugador y del enemigo
        for player_bullet in self.bullets[:]:
            for enemy_bullet in self.enemy_bullets[:]:
                if self.check_collision(player_bullet, enemy_bullet):
                    if player_bullet in self.bullets:
                        self.bullets.remove(player_bullet)
                    if enemy_bullet in self.enemy_bullets:
                        self.enemy_bullets.remove(enemy_bullet)
                        self.score += 2
                    break

        for bullet in self.enemy_bullets[:]:
            if self.check_collision(bullet, self.player):
                self.enemy_bullets.remove(bullet)
                if not self.player.esta_protegido():
                    self.player.life = max(self.player.life - 1, 0)
                self._play_sound("hit")

        # Mover y colisionar power-ups
        for powerup in self.powerups[:]:
            powerup.move()
            if powerup.x < 0 or powerup.x > WIDTH:
                self.powerups.remove(powerup)
            elif self.check_collision(powerup, self.player):
                if powerup.powerup_type == PowerUp.LIFE:
                    self.player.life += 1
                elif powerup.powerup_type == PowerUp.SHIELD:
                    self.player.activar_escudo()
                else:
                    self.player.add_powerup(powerup.powerup_type)
                self.powerups.remove(powerup)
                self._play_sound("powerup")

        # Actualizar explosiones
        for explosion in self.explosions[:]:
            explosion.update()
            if explosion.is_dead():
                self.explosions.remove(explosion)

        # Timer de nivel y fase de boss
        if not self.boss_phase:
            self.level_timer -= 1
            if self.level_timer <= 0:
                self.level_timer = 0
                self.boss_phase = True
                self.boss = self._create_boss(self.level)
                self.enemies.clear()
                self._play_sound("boss_appear")
        else:
            self._update_boss()

        self.background.update(self.level)

        # Detectar game over
        if self.player.life <= 0 and not self.game_over:
            self.game_over = True
            self.game_over_timer = 0
            self._play_sound("game_over")

    def _update_boss(self):
        """Actualiza la lógica del boss: movimiento, disparos, colisiones, victoria."""
        if not self.boss or not self.boss.alive:
            return

        self.boss.move()

        new_bullets = self.boss.shoot()
        self.enemy_bullets.extend(new_bullets)

        for bullet in self.bullets[:]:
            boss_rect = self.boss.get_hit_rect()
            bullet_rect = pygame.Rect(bullet.x, bullet.y, bullet.width, bullet.height)
            if boss_rect.colliderect(bullet_rect):
                self.bullets.remove(bullet)
                self.boss.take_damage(BULLET_DAMAGE)
                if not self.boss.alive:
                    for _ in range(5):
                        ox = self.boss.x + random.randint(-40, 40)
                        oy = self.boss.y + random.randint(-40, 40)
                        self.explosions.append(Explosion(ox, oy, num_particles=24))
                    self._play_sound("boss_defeat")
                    self._advance_level()
                    break

        if self.boss and self.boss.alive:
            boss_rect = self.boss.get_hit_rect()
            player_rect = pygame.Rect(
                self.player.x - self.player.size,
                self.player.y - self.player.size,
                self.player.size * 2,
                self.player.size * 2,
            )
            if boss_rect.colliderect(player_rect):
                if not self.player.esta_protegido():
                    self.player.life = max(self.player.life - 1, 0)
                self._play_sound("hit")

    def _create_boss(self, level):
        return CubeBoss(level)

    def _advance_level(self):
        self.level += 1
        self.max_enemies = 5 + (3 * self.level)
        self.player.size += 2
        self.score = 0
        self.player.life += 1
        self.boss_phase = False
        self.boss = None
        self.level_timer = LEVEL_DURATION * FPS
        self.boss_minion_timer = 0
        self._play_sound("level_up")

    def draw_game_elements(self):
        self.background.draw(self.screen)
        self.player.draw(self.screen)
        for bullet in self.bullets:
            bullet.draw(self.screen)
        for enemy in self.enemies:
            enemy.draw(self.screen, self.player.x, self.player.y)
        for bullet in self.enemy_bullets:
            bullet.draw(self.screen)
        for powerup in self.powerups:
            powerup.draw(self.screen)
        for explosion in self.explosions:
            explosion.draw(self.screen)

        if self.boss and self.boss.alive:
            self.boss.draw(self.screen)
            self.boss.draw_health_bar(self.screen)

        self.draw_text(f"Score: {self.score}", (5, 5), 16)
        self.draw_text(f"Level: {self.level}", (5, 25), 16)
        self.draw_text(f"Lifes: {self.player.life}", (5, 45), 16)
        if self.player.esta_protegido():
            self.draw_text("ESCUDO ACTIVO", (5, 95), 16, color=PURPLE)

        if not self.boss_phase:
            seconds_left = self.level_timer // FPS
            minutes = seconds_left // 60
            secs = seconds_left % 60
            timer_color = RED if seconds_left <= 10 else WHITE
            font = pygame.font.SysFont("monospace", 20, bold=True)
            timer_text = font.render(f"{minutes:02d}:{secs:02d}", 1, timer_color)
            self.screen.blit(timer_text, (WIDTH - 100, 5))
        else:
            font = pygame.font.SysFont("monospace", 20, bold=True)
            boss_text = font.render("BOSS FIGHT!", 1, RED)
            self.screen.blit(boss_text, (WIDTH - 160, 5))

        if self.player.powerups:
            self.draw_powerups_visual()

        if self.paused:
            self.draw_text("PAUSED", (WIDTH // 2 - 100, HEIGHT // 2 - 24), 48)

        if self.player.life <= 0:
            self.draw_text("GAME OVER", (WIDTH // 2 - 150, HEIGHT // 2 - 24), 48)
            # Texto de retorno al menú
            font_small = pygame.font.SysFont("monospace", 20)
            back_text = font_small.render("Returning to menu...", True, (150, 150, 150))
            back_rect = back_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30))
            self.screen.blit(back_text, back_rect)

    def check_collision(self, obj1, obj2):
        if hasattr(obj1, "size"):
            x1_min = obj1.x - obj1.size // 2
            x1_max = obj1.x + obj1.size // 2
            y1_min = obj1.y
            y1_max = obj1.y + obj1.size
        else:
            x1_min = obj1.x
            x1_max = obj1.x + obj1.width
            y1_min = obj1.y
            y1_max = obj1.y + obj1.height

        if hasattr(obj2, "size"):
            x2_min = obj2.x - obj2.size // 2
            x2_max = obj2.x + obj2.size // 2
            y2_min = obj2.y
            y2_max = obj2.y + obj2.size
        else:
            x2_min = obj2.x
            x2_max = obj2.x + obj2.width
            y2_min = obj2.y
            y2_max = obj2.y + obj2.height

        return (
            x1_min < x2_max and x1_max > x2_min and y1_min < y2_max and y1_max > y2_min
        )

    def check_attack(self, enemy, player):
        enemy_left = enemy.x - enemy.size // 2 - player.size
        enemy_right = enemy.x + enemy.size // 2 + player.size
        enemy_top = enemy.y - enemy.size // 2
        enemy_bottom = enemy.y + enemy.size

        player_left = player.x
        player_right = player.x
        player_top = player.y - player.size
        player_bottom = player.y

        return (
            player_left >= enemy_left
            and player_right <= enemy_right
            and player_top >= enemy_top
            and player_bottom <= enemy_bottom
        )

    def draw_text(self, text, position, size, color=WHITE):
        font = pygame.font.SysFont("monospace", size)
        label = font.render(text, 1, color)
        self.screen.blit(label, position)

    def draw_powerups_visual(self):
        """Dibuja los power-ups con insignias visuales e iconos"""
        x_pos = 5
        y_pos = 65
        spacing = 35

        for powerup_type, count in self.player.powerups.items():
            color = PowerUp.COLORS.get(powerup_type, WHITE)
            symbol = PowerUp.SYMBOLS.get(powerup_type, "?")

            pygame.draw.circle(self.screen, color, (x_pos + 8, y_pos + 8), 10, 2)

            font_symbol = pygame.font.SysFont("monospace", 14, bold=True)
            symbol_text = font_symbol.render(symbol, 1, color)
            symbol_rect = symbol_text.get_rect(center=(x_pos + 8, y_pos + 8))
            self.screen.blit(symbol_text, symbol_rect)

            font_count = pygame.font.SysFont("monospace", 12)
            count_text = font_count.render(str(count), 1, color)
            self.screen.blit(count_text, (x_pos + 12, y_pos + 2))

            x_pos += spacing