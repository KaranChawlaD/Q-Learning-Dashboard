import heapq
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
STEP_INTERVAL_MS = 250

GRID_LINE_COLOR = (140, 140, 140, 45)
BUILDING_BASE_COLOR = (110, 110, 110)
BANK_BASE_COLOR = (88, 168, 88)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
ELEMS_DIR = os.path.join(PROJECT_ROOT, "assets", "elems")

GridCell = tuple[int, int]


def load_scaled_sprite(filename: str) -> pygame.Surface:
    path = os.path.join(SPRITES_DIR, filename)
    sprite = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))


def load_scaled_elem(filename: str) -> pygame.Surface:
    path = os.path.join(ELEMS_DIR, filename)
    elem = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(elem, (TILE_SIZE, TILE_SIZE))


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


def heuristic(cell: GridCell, goal: GridCell) -> int:
    return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])


def neighbors(cell: GridCell, obstacle_cells: set[GridCell]) -> list[GridCell]:
    col, row = cell
    candidates = [(col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)]
    valid: list[GridCell] = []
    for next_col, next_row in candidates:
        in_bounds = 0 <= next_col < GRID_COLS and 0 <= next_row < GRID_ROWS
        if in_bounds and (next_col, next_row) not in obstacle_cells:
            valid.append((next_col, next_row))
    return valid


def reconstruct_path(came_from: dict[GridCell, GridCell], goal: GridCell) -> list[GridCell]:
    path = [goal]
    current = goal
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def a_star(start: GridCell, goal: GridCell, obstacle_cells: set[GridCell]) -> list[GridCell]:
    frontier: list[tuple[int, int, GridCell]] = []
    counter = 0
    heapq.heappush(frontier, (heuristic(start, goal), counter, start))
    came_from: dict[GridCell, GridCell] = {}
    g_score: dict[GridCell, int] = {start: 0}

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            return reconstruct_path(came_from, goal)

        for next_cell in neighbors(current, obstacle_cells):
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(next_cell, 10**9):
                came_from[next_cell] = current
                g_score[next_cell] = tentative_g
                f_score = tentative_g + heuristic(next_cell, goal)
                counter += 1
                heapq.heappush(frontier, (f_score, counter, next_cell))

    return []


def direction_from_step(current: GridCell, next_cell: GridCell) -> str:
    delta_col = next_cell[0] - current[0]
    delta_row = next_cell[1] - current[1]
    if delta_col == 1:
        return "right"
    if delta_col == -1:
        return "left"
    if delta_row == 1:
        return "down"
    return "up"


def random_open_cell(occupied_cells: set[GridCell]) -> GridCell:
    while True:
        cell = (random.randrange(1, GRID_COLS - 1), random.randrange(1, GRID_ROWS - 1))
        if cell not in occupied_cells:
            return cell


def generate_random_layout(
    building_sprites: dict[str, pygame.Surface], start_cell: GridCell
) -> tuple[GridCell, list[tuple[pygame.Surface, GridCell]], set[GridCell], list[GridCell]]:
    building_names = (
        ["building_1.png"] * 4 + ["building_2.png"] * 4 + ["building_3.png"] * 4
    )
    while True:
        occupied_cells: set[GridCell] = {start_cell}
        bank_cell = random_open_cell(occupied_cells)
        occupied_cells.add(bank_cell)
        placed: list[tuple[str, GridCell]] = []
        for name in building_names:
            cell = random_open_cell(occupied_cells)
            occupied_cells.add(cell)
            placed.append((name, cell))

        obstacle_cells = {cell for _, cell in placed}
        path = a_star(start_cell, bank_cell, obstacle_cells)
        if path:
            buildings = [(building_sprites[name], cell) for name, cell in placed]
            return bank_cell, buildings, obstacle_cells, path


def main() -> None:
    pygame.init()
    pygame.display.set_caption("A* Pathfinding Demo")
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

    start_cell: GridCell = (0, 0)

    bank_cell, buildings, obstacle_cells, path = generate_random_layout(building_sprites, start_cell)
    player_cell = start_cell
    facing = "down"
    path_index = 0
    last_step_time = pygame.time.get_ticks()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    bank_cell, buildings, obstacle_cells, path = generate_random_layout(
                        building_sprites, start_cell
                    )
                    player_cell = start_cell
                    facing = "down"
                    path_index = 0
                    last_step_time = pygame.time.get_ticks()

        now = pygame.time.get_ticks()
        if path and path_index < len(path) - 1 and now - last_step_time >= STEP_INTERVAL_MS:
            next_cell = path[path_index + 1]
            facing = direction_from_step(player_cell, next_cell)
            player_cell = next_cell
            path_index += 1
            last_step_time = now

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
        screen.blit(sprites[facing], (player_cell[0] * TILE_SIZE, player_cell[1] * TILE_SIZE))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
