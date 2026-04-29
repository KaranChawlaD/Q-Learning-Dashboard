import os
import sys

import pygame


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
TILE_SIZE = 64
GRID_COLS = WINDOW_WIDTH // TILE_SIZE
GRID_ROWS = WINDOW_HEIGHT // TILE_SIZE
FPS = 60

LIGHT_GREEN = (170, 215, 81)
DARK_GREEN = (162, 209, 73)
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")


def load_scaled_sprite(filename: str) -> pygame.Surface:
    path = os.path.join(SPRITES_DIR, filename)
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def draw_checkerboard(screen: pygame.Surface) -> None:
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            color = LIGHT_GREEN if (row + col) % 2 == 0 else DARK_GREEN
            tile = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, color, tile)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Q-learning Environment")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    sprites = {
        "up": load_scaled_sprite("business_man_1_back.png"),
        "down": load_scaled_sprite("business_man_1_forward.png"),
        "left": load_scaled_sprite("business_man_1_left.png"),
        "right": load_scaled_sprite("business_man_1_right.png"),
    }

    player_col = GRID_COLS // 2
    player_row = GRID_ROWS // 2
    facing = "down"

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    player_row -= 1
                    facing = "up"
                elif event.key == pygame.K_DOWN:
                    player_row += 1
                    facing = "down"
                elif event.key == pygame.K_LEFT:
                    player_col -= 1
                    facing = "left"
                elif event.key == pygame.K_RIGHT:
                    player_col += 1
                    facing = "right"

                player_col = clamp(player_col, 0, GRID_COLS - 1)
                player_row = clamp(player_row, 0, GRID_ROWS - 1)

        draw_checkerboard(screen)
        screen.blit(sprites[facing], (player_col * TILE_SIZE, player_row * TILE_SIZE))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
