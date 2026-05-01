import os
import sys

import pygame


TILE_SIZE = 64
GRID_COLS = 12
GRID_ROWS = 9
WINDOW_WIDTH = GRID_COLS * TILE_SIZE
WINDOW_HEIGHT = GRID_ROWS * TILE_SIZE
FPS = 60

GRID_LINE_COLOR = (140, 140, 140, 45)
BUILDING_BASE_COLOR = (110, 110, 110)
BANK_BASE_COLOR = (88, 168, 88)
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
ELEMS_DIR = os.path.join(PROJECT_ROOT, "assets", "elems")


def load_scaled_sprite(filename: str) -> pygame.Surface:
    path = os.path.join(SPRITES_DIR, filename)
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))


def load_scaled_elem(filename: str) -> pygame.Surface:
    path = os.path.join(ELEMS_DIR, filename)
    elem = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(elem, (TILE_SIZE, TILE_SIZE))


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(value, maximum))


def draw_tarmac_grid(screen: pygame.Surface, tarmac_tile: pygame.Surface) -> None:
    grid_overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            tile_x = col * TILE_SIZE
            tile_y = row * TILE_SIZE
            tile_rect = pygame.Rect(tile_x, tile_y, TILE_SIZE, TILE_SIZE)
            screen.blit(tarmac_tile, (tile_x, tile_y))
            pygame.draw.rect(grid_overlay, GRID_LINE_COLOR, tile_rect, 1)
    screen.blit(grid_overlay, (0, 0))


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
    tarmac_tile = load_scaled_elem("tarmac.png")
    building_sprites = {
        "building_1.png": load_scaled_elem("building_1.png"),
        "building_2.png": load_scaled_elem("building_2.png"),
        "building_3.png": load_scaled_elem("building_3.png"),
    }
    bank_sprite = load_scaled_elem("bank.png")
    bank_cell = (GRID_COLS - 1, GRID_ROWS - 1)
    fixed_building_cells: dict[str, tuple[int, int]] = {
        "building_1.png": (3, 2),
        "building_2.png": (6, 4),
        "building_3.png": (8, 6),
    }

    player_col = 0
    player_row = 0
    facing = "down"
    buildings: list[tuple[pygame.Surface, tuple[int, int]]] = []
    for filename, cell in fixed_building_cells.items():
        buildings.append((building_sprites[filename], cell))
    obstacle_cells = {cell for _, cell in buildings}

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    facing = "up"
                    next_col = player_col
                    next_row = player_row - 1
                elif event.key == pygame.K_DOWN:
                    facing = "down"
                    next_col = player_col
                    next_row = player_row + 1
                elif event.key == pygame.K_LEFT:
                    facing = "left"
                    next_col = player_col - 1
                    next_row = player_row
                elif event.key == pygame.K_RIGHT:
                    facing = "right"
                    next_col = player_col + 1
                    next_row = player_row
                else:
                    continue

                next_col = clamp(next_col, 0, GRID_COLS - 1)
                next_row = clamp(next_row, 0, GRID_ROWS - 1)
                if (next_col, next_row) not in obstacle_cells:
                    player_col = next_col
                    player_row = next_row

        draw_tarmac_grid(screen, tarmac_tile)
        for _, (building_col, building_row) in buildings:
            building_base_rect = pygame.Rect(
                building_col * TILE_SIZE, building_row * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )
            pygame.draw.rect(screen, BUILDING_BASE_COLOR, building_base_rect)

        bank_base_rect = pygame.Rect(bank_cell[0] * TILE_SIZE, bank_cell[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(screen, BANK_BASE_COLOR, bank_base_rect)

        for building_sprite, (building_col, building_row) in buildings:
            screen.blit(building_sprite, (building_col * TILE_SIZE, building_row * TILE_SIZE))
        screen.blit(bank_sprite, (bank_cell[0] * TILE_SIZE, bank_cell[1] * TILE_SIZE))
        screen.blit(sprites[facing], (player_col * TILE_SIZE, player_row * TILE_SIZE))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
