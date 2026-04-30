import os
import random
import sys

import pygame


TILE_SIZE = 64
GRID_COLS = 12
GRID_ROWS = 9
WINDOW_WIDTH = GRID_COLS * TILE_SIZE
WINDOW_HEIGHT = GRID_ROWS * TILE_SIZE
FPS = 60

GRID_LINE_COLOR = (140, 140, 140, 45)
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


def get_random_open_cell(occupied_cells: set[tuple[int, int]]) -> tuple[int, int]:
    while True:
        cell = (random.randrange(1, GRID_COLS - 1), random.randrange(1, GRID_ROWS - 1))
        if cell not in occupied_cells:
            return cell


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

    player_col = GRID_COLS // 2
    player_row = GRID_ROWS // 2
    facing = "down"
    occupied_cells: set[tuple[int, int]] = {(player_col, player_row)}
    buildings: list[tuple[pygame.Surface, tuple[int, int]]] = []
    for filename in building_sprites:
        cell = get_random_open_cell(occupied_cells)
        occupied_cells.add(cell)
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
        for building_sprite, (building_col, building_row) in buildings:
            screen.blit(building_sprite, (building_col * TILE_SIZE, building_row * TILE_SIZE))
        screen.blit(sprites[facing], (player_col * TILE_SIZE, player_row * TILE_SIZE))
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
