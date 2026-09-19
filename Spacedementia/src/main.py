import pygame

# Inicializar pygame ANTES de importar config para detectar pantalla
pygame.init()
_info = pygame.display.Info()

import config
config.WIDTH = min(config.WIDTH, _info.current_w - 50)
config.HEIGHT = min(config.HEIGHT, _info.current_h - 100)

from config import FPS, HEIGHT, WIDTH
from game import Game
from menu import Menu
from sound_manager import SoundManager


def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Space Dementia")
    clock = pygame.time.Clock()

    sound_manager = SoundManager()
    sound_manager.play_music()
    menu = Menu(screen, sound_manager)

    state = "menu"  # "menu" o "playing"
    game = None

    running = True
    while running:
        if state == "menu":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                result = menu.handle_event(event)
                if result:
                    action, data = result
                    if action == "play":
                        game = Game(screen, sound_manager, start_level=data)
                        state = "playing"

            menu.update()
            menu.draw()
            pygame.display.flip()
            clock.tick(FPS)

        elif state == "playing":
            result = game.run_frame(clock)
            if result == "quit":
                running = False
            elif result == "menu":
                state = "menu"
                game = None

    sound_manager.cleanup()
    pygame.quit()


if __name__ == "__main__":
    main()
