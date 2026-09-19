"""Menú principal retro para Space Dementia."""

import math
import random

import pygame

from config import BLACK, BLUE, CYAN, GREEN, HEIGHT, MAGENTA, RED, WHITE, WIDTH, YELLOW


class StarField:
    """Campo de estrellas animado para el fondo del menú."""

    def __init__(self):
        self.stars = []
        for _ in range(200):
            self.stars.append({
                "x": random.randint(0, WIDTH),
                "y": random.randint(0, HEIGHT),
                "speed": random.uniform(0.5, 3),
                "size": random.choice([1, 1, 1, 2]),
                "brightness": random.randint(100, 255),
            })

    def update(self):
        for star in self.stars:
            star["x"] -= star["speed"]
            if star["x"] < 0:
                star["x"] = WIDTH
                star["y"] = random.randint(0, HEIGHT)

    def draw(self, screen):
        for star in self.stars:
            b = star["brightness"]
            color = (b, b, b)
            if star["size"] == 1:
                screen.set_at((int(star["x"]), int(star["y"])), color)
            else:
                pygame.draw.circle(screen, color, (int(star["x"]), int(star["y"])), star["size"])


class RetroButton:
    """Botón retro con bordes pixelados y efecto de brillo."""

    def __init__(self, x, y, width, height, text, color=CYAN, text_color=BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.hover = False
        self.selected = False
        self.pulse_frame = 0

    def draw(self, screen):
        self.pulse_frame += 1

        if self.selected:
            # Brillo pulsante cuando está seleccionado
            pulse = abs(math.sin(self.pulse_frame * 0.08)) * 0.4 + 0.6
            r = min(255, int(self.color[0] * pulse + 80))
            g = min(255, int(self.color[1] * pulse + 80))
            b = min(255, int(self.color[2] * pulse + 80))
            fill_color = (r, g, b)
        else:
            # Color base más oscuro cuando no está seleccionado
            fill_color = (self.color[0] // 3, self.color[1] // 3, self.color[2] // 3)

        # Sombra (efecto 3D retro)
        shadow_rect = self.rect.move(4, 4)
        pygame.draw.rect(screen, (20, 20, 20), shadow_rect)

        # Fondo del botón
        pygame.draw.rect(screen, fill_color, self.rect)

        # Borde exterior
        border_color = self.color if self.selected else (self.color[0] // 2, self.color[1] // 2, self.color[2] // 2)
        pygame.draw.rect(screen, border_color, self.rect, 3)

        # Borde interior highlight (efecto bisel retro)
        if self.selected:
            inner = self.rect.inflate(-6, -6)
            pygame.draw.rect(screen, (255, 255, 255, 100), inner, 1)

        # Texto centrado
        font_size = min(32, self.rect.height - 16)
        font = pygame.font.SysFont("monospace", font_size, bold=True)
        txt_color = WHITE if self.selected else (180, 180, 180)
        label = font.render(self.text, True, txt_color)
        label_rect = label.get_rect(center=self.rect.center)
        screen.blit(label, label_rect)

        # Flechitas indicadoras cuando está seleccionado
        if self.selected:
            arrow_font = pygame.font.SysFont("monospace", font_size, bold=True)
            # Flecha izquierda
            left_arrow = arrow_font.render(">", True, YELLOW)
            screen.blit(left_arrow, (self.rect.left - 30, self.rect.centery - left_arrow.get_height() // 2))
            # Flecha derecha
            right_arrow = arrow_font.render("<", True, YELLOW)
            screen.blit(right_arrow, (self.rect.right + 10, self.rect.centery - right_arrow.get_height() // 2))


class SliderWidget:
    """Slider retro para volumen."""

    def __init__(self, x, y, width, label, value=0.5, color=CYAN):
        self.x = x
        self.y = y
        self.width = width
        self.height = 20
        self.label = label
        self.value = value
        self.color = color
        self.selected = False

    def draw(self, screen):
        font = pygame.font.SysFont("monospace", 22, bold=True)
        txt_color = WHITE if self.selected else (150, 150, 150)

        # Label
        label_surf = font.render(self.label, True, txt_color)
        screen.blit(label_surf, (self.x, self.y - 30))

        # Porcentaje
        pct = font.render(f"{int(self.value * 100)}%", True, txt_color)
        screen.blit(pct, (self.x + self.width + 15, self.y - 5))

        # Barra de fondo
        bar_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(screen, (40, 40, 40), bar_rect)

        # Barra de progreso
        fill_width = int(self.width * self.value)
        if fill_width > 0:
            fill_color = self.color if self.selected else (self.color[0] // 2, self.color[1] // 2, self.color[2] // 2)
            pygame.draw.rect(screen, fill_color, (self.x, self.y, fill_width, self.height))

        # Borde
        border_color = self.color if self.selected else (80, 80, 80)
        pygame.draw.rect(screen, border_color, bar_rect, 2)

        # Marcas de segmento
        for i in range(1, 10):
            mark_x = self.x + int(self.width * i / 10)
            pygame.draw.line(screen, (80, 80, 80), (mark_x, self.y), (mark_x, self.y + self.height))

        # Indicador
        if self.selected:
            knob_x = self.x + fill_width
            pygame.draw.rect(screen, WHITE, (knob_x - 3, self.y - 4, 6, self.height + 8))


class Menu:
    """Menú principal del juego con submenús."""

    # Estados del menú
    STATE_MAIN = "main"
    STATE_LEVELS = "levels"
    STATE_SOUND = "sound"
    STATE_SETTINGS = "settings"

    def __init__(self, screen, sound_manager):
        self.screen = screen
        self.sound = sound_manager
        self.state = self.STATE_MAIN
        self.starfield = StarField()
        self.frame = 0
        self.selected_level = 1
        self.max_levels = 5

        # Configuraciones
        self.fullscreen = False
        self.show_fps = False

        # Botones del menú principal
        btn_w, btn_h = 320, 60
        btn_x = WIDTH // 2 - btn_w // 2
        start_y = HEIGHT // 2 + 20
        gap = 80

        self.main_buttons = [
            RetroButton(btn_x, start_y, btn_w, btn_h, "PLAY", CYAN),
            RetroButton(btn_x, start_y + gap, btn_w, btn_h, "LEVELS", GREEN),
            RetroButton(btn_x, start_y + gap * 2, btn_w, btn_h, "SOUND", MAGENTA),
            RetroButton(btn_x, start_y + gap * 3, btn_w, btn_h, "SETTINGS", YELLOW),
        ]
        self.main_index = 0
        self.main_buttons[0].selected = True

        # Botones de nivel
        self.level_buttons = []
        self._build_level_buttons()

        # Sliders de sonido
        slider_x = WIDTH // 2 - 200
        slider_y = HEIGHT // 2 - 40
        self.sound_sliders = [
            SliderWidget(slider_x, slider_y, 400, "SFX VOLUME", sound_manager.get_sfx_volume(), CYAN),
            SliderWidget(slider_x, slider_y + 80, 400, "MUSIC VOLUME", sound_manager.get_music_volume(), MAGENTA),
        ]
        self.sound_index = 0
        self.sound_sliders[0].selected = True

        # Opciones de settings
        self.settings_options = ["FULLSCREEN: OFF", "SHOW FPS: OFF", "BACK"]
        self.settings_index = 0

    def _build_level_buttons(self):
        self.level_buttons = []
        cols = 5
        btn_w, btn_h = 140, 100
        total_w = cols * btn_w + (cols - 1) * 30
        start_x = WIDTH // 2 - total_w // 2
        start_y = HEIGHT // 2 - 40

        for i in range(self.max_levels):
            col = i % cols
            row = i // cols
            x = start_x + col * (btn_w + 30)
            y = start_y + row * (btn_h + 30)
            color = CYAN if i == 0 else (60, 60, 60)
            self.level_buttons.append(
                RetroButton(x, y, btn_w, btn_h, f"LVL {i + 1}", color)
            )
        self.level_index = 0
        if self.level_buttons:
            self.level_buttons[0].selected = True

    def handle_event(self, event):
        """Maneja eventos de teclado. Retorna (action, data) o None."""
        if event.type != pygame.KEYDOWN:
            return None

        if self.state == self.STATE_MAIN:
            return self._handle_main(event)
        elif self.state == self.STATE_LEVELS:
            return self._handle_levels(event)
        elif self.state == self.STATE_SOUND:
            return self._handle_sound(event)
        elif self.state == self.STATE_SETTINGS:
            return self._handle_settings(event)
        return None

    def _handle_main(self, event):
        if event.key in (pygame.K_UP, pygame.K_w):
            self.main_buttons[self.main_index].selected = False
            self.main_index = (self.main_index - 1) % len(self.main_buttons)
            self.main_buttons[self.main_index].selected = True
            self.sound.play("menu_select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.main_buttons[self.main_index].selected = False
            self.main_index = (self.main_index + 1) % len(self.main_buttons)
            self.main_buttons[self.main_index].selected = True
            self.sound.play("menu_select")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.sound.play("menu_confirm")
            if self.main_index == 0:  # PLAY
                return ("play", self.selected_level)
            elif self.main_index == 1:  # LEVELS
                self.state = self.STATE_LEVELS
                self._select_level_button(self.level_index)
            elif self.main_index == 2:  # SOUND
                self.state = self.STATE_SOUND
                self._select_sound_slider(self.sound_index)
            elif self.main_index == 3:  # SETTINGS
                self.state = self.STATE_SETTINGS
                self.settings_index = 0
        return None

    def _handle_levels(self, event):
        if event.key == pygame.K_ESCAPE:
            self.state = self.STATE_MAIN
            self.sound.play("menu_select")
            return None

        cols = 5
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._select_level_button(-1, relative=True)
            self.sound.play("menu_select")
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._select_level_button(1, relative=True)
            self.sound.play("menu_select")
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._select_level_button(-cols, relative=True)
            self.sound.play("menu_select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._select_level_button(cols, relative=True)
            self.sound.play("menu_select")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.selected_level = self.level_index + 1
            self.sound.play("menu_confirm")
            # Actualizar colores para indicar nivel seleccionado
            for i, btn in enumerate(self.level_buttons):
                btn.color = CYAN if i == self.level_index else (60, 60, 60)
        return None

    def _handle_sound(self, event):
        if event.key == pygame.K_ESCAPE:
            self.state = self.STATE_MAIN
            self.sound.play("menu_select")
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self._select_sound_slider((self.sound_index - 1) % len(self.sound_sliders))
            self.sound.play("menu_select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._select_sound_slider((self.sound_index + 1) % len(self.sound_sliders))
            self.sound.play("menu_select")
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._adjust_slider(-0.1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._adjust_slider(0.1)
        return None

    def _handle_settings(self, event):
        if event.key == pygame.K_ESCAPE:
            self.state = self.STATE_MAIN
            self.sound.play("menu_select")
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self.settings_index = (self.settings_index - 1) % len(self.settings_options)
            self.sound.play("menu_select")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.settings_index = (self.settings_index + 1) % len(self.settings_options)
            self.sound.play("menu_select")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.sound.play("menu_confirm")
            if self.settings_index == 0:  # Fullscreen
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
                else:
                    pygame.display.set_mode((WIDTH, HEIGHT))
                self.settings_options[0] = f"FULLSCREEN: {'ON' if self.fullscreen else 'OFF'}"
            elif self.settings_index == 1:  # Show FPS
                self.show_fps = not self.show_fps
                self.settings_options[1] = f"SHOW FPS: {'ON' if self.show_fps else 'OFF'}"
            elif self.settings_index == 2:  # Back
                self.state = self.STATE_MAIN
        return None

    def _select_level_button(self, index_or_delta, relative=False):
        if self.level_buttons:
            self.level_buttons[self.level_index].selected = False
        if relative:
            new_idx = self.level_index + index_or_delta
            new_idx = max(0, min(new_idx, len(self.level_buttons) - 1))
            self.level_index = new_idx
        else:
            self.level_index = max(0, min(index_or_delta, len(self.level_buttons) - 1))
        if self.level_buttons:
            self.level_buttons[self.level_index].selected = True

    def _select_sound_slider(self, index):
        for s in self.sound_sliders:
            s.selected = False
        self.sound_index = index
        self.sound_sliders[self.sound_index].selected = True

    def _adjust_slider(self, delta):
        slider = self.sound_sliders[self.sound_index]
        slider.value = max(0.0, min(1.0, slider.value + delta))
        if self.sound_index == 0:
            self.sound.set_sfx_volume(slider.value)
        else:
            self.sound.set_music_volume(slider.value)
        self.sound.play("menu_select")

    def update(self):
        self.frame += 1
        self.starfield.update()

    def draw(self):
        self.screen.fill((5, 5, 15))
        self.starfield.draw(self.screen)

        if self.state == self.STATE_MAIN:
            self._draw_main()
        elif self.state == self.STATE_LEVELS:
            self._draw_levels()
        elif self.state == self.STATE_SOUND:
            self._draw_sound()
        elif self.state == self.STATE_SETTINGS:
            self._draw_settings()

    def _draw_title(self):
        """Dibuja el título con efecto retro."""
        title = "SPACE DEMENTIA"
        font_big = pygame.font.SysFont("monospace", 72, bold=True)

        # Sombra
        shadow = font_big.render(title, True, (30, 0, 60))
        shadow_rect = shadow.get_rect(center=(WIDTH // 2 + 4, 180 + 4))
        self.screen.blit(shadow, shadow_rect)

        # Efecto de color pulsante
        t = self.frame * 0.03
        r = int(abs(math.sin(t)) * 100 + 155)
        g = int(abs(math.sin(t + 1)) * 80 + 40)
        b = int(abs(math.sin(t + 2)) * 155 + 100)
        title_color = (min(255, r), min(255, g), min(255, b))

        title_surf = font_big.render(title, True, title_color)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 180))
        self.screen.blit(title_surf, title_rect)

        # Línea decorativa debajo del título
        line_y = 230
        line_w = 500
        line_x = WIDTH // 2 - line_w // 2
        pulse = abs(math.sin(self.frame * 0.05))
        line_color = (int(pulse * 100 + 50), int(pulse * 200 + 55), int(pulse * 255))
        pygame.draw.line(self.screen, line_color, (line_x, line_y), (line_x + line_w, line_y), 2)

    def _draw_subtitle(self, text):
        """Dibuja un subtítulo centrado."""
        font = pygame.font.SysFont("monospace", 36, bold=True)
        surf = font.render(text, True, WHITE)
        rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 120))
        self.screen.blit(surf, rect)

    def _draw_back_hint(self):
        """Dibuja indicación de cómo volver."""
        font = pygame.font.SysFont("monospace", 18)
        hint = font.render("[ESC] BACK", True, (100, 100, 100))
        self.screen.blit(hint, (20, HEIGHT - 40))

    def _draw_main(self):
        self._draw_title()

        # Subtítulo
        font_sub = pygame.font.SysFont("monospace", 20)
        sub_text = f"SELECTED: LEVEL {self.selected_level}"
        sub_surf = font_sub.render(sub_text, True, (120, 120, 120))
        sub_rect = sub_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10))
        self.screen.blit(sub_surf, sub_rect)

        for btn in self.main_buttons:
            btn.draw(self.screen)

        # Controles
        font_ctrl = pygame.font.SysFont("monospace", 16)
        controls = font_ctrl.render("[UP/DOWN] Navigate   [ENTER] Select   [Q] Quit", True, (80, 80, 80))
        ctrl_rect = controls.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        self.screen.blit(controls, ctrl_rect)

    def _draw_levels(self):
        self._draw_subtitle("SELECT LEVEL")
        self._draw_back_hint()

        for btn in self.level_buttons:
            btn.draw(self.screen)

        # Indicador de nivel seleccionado
        font = pygame.font.SysFont("monospace", 22)
        info = font.render(f"Current: Level {self.selected_level}", True, CYAN)
        info_rect = info.get_rect(center=(WIDTH // 2, HEIGHT - 80))
        self.screen.blit(info, info_rect)

        # Controles
        font_ctrl = pygame.font.SysFont("monospace", 16)
        controls = font_ctrl.render("[ARROWS] Navigate   [ENTER] Select   [ESC] Back", True, (80, 80, 80))
        ctrl_rect = controls.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        self.screen.blit(controls, ctrl_rect)

    def _draw_sound(self):
        self._draw_subtitle("SOUND")
        self._draw_back_hint()

        for slider in self.sound_sliders:
            slider.draw(self.screen)

        # Controles
        font_ctrl = pygame.font.SysFont("monospace", 16)
        controls = font_ctrl.render("[UP/DOWN] Select   [LEFT/RIGHT] Adjust   [ESC] Back", True, (80, 80, 80))
        ctrl_rect = controls.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        self.screen.blit(controls, ctrl_rect)

    def _draw_settings(self):
        self._draw_subtitle("SETTINGS")
        self._draw_back_hint()

        font = pygame.font.SysFont("monospace", 28, bold=True)
        start_y = HEIGHT // 2 - 40
        gap = 60

        for i, option in enumerate(self.settings_options):
            selected = i == self.settings_index
            color = WHITE if selected else (100, 100, 100)

            text_surf = font.render(option, True, color)
            text_rect = text_surf.get_rect(center=(WIDTH // 2, start_y + i * gap))
            self.screen.blit(text_surf, text_rect)

            if selected:
                # Flechitas
                arrow_font = pygame.font.SysFont("monospace", 28, bold=True)
                left = arrow_font.render(">", True, YELLOW)
                right = arrow_font.render("<", True, YELLOW)
                self.screen.blit(left, (text_rect.left - 35, text_rect.y))
                self.screen.blit(right, (text_rect.right + 15, text_rect.y))

        # Controles
        font_ctrl = pygame.font.SysFont("monospace", 16)
        controls = font_ctrl.render("[UP/DOWN] Navigate   [ENTER] Toggle   [ESC] Back", True, (80, 80, 80))
        ctrl_rect = controls.get_rect(center=(WIDTH // 2, HEIGHT - 40))
        self.screen.blit(controls, ctrl_rect)
