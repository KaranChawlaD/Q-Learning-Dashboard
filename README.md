# Q-Learning Grid Prototype

This repository contains a lightweight Pygame prototype for a grid-based character movement environment. It is intended as a foundation for reinforcement learning experiments and gameplay iteration.

## Current Features

- Tile-based tarmac background using `assets/elems/tarmac.png`
- Manual keyboard movement mode (`run.py`)
- Direction-aware character sprite swapping (`forward`, `back`, `left`, `right`)
- Manual mode uses fixed map layout: player starts top-left, bank is bottom-right, and buildings are fixed obstacles
- Separate A* demo mode (`run_astar.py`) where buildings and bank are randomized each run
- A* layout generation guarantees a valid path from start to bank

## Project Structure

- `run.py`: Entry point for manual-control prototype
- `run_astar.py`: Entry point for A* pathfinding demo
- `src/main.py`: Manual-control Pygame loop and movement logic
- `src/astar_demo.py`: A* pathfinding demo and auto-movement logic
- `assets/elems/`: Environment assets (`tarmac`, `building_1..3`, `bank`)
- `assets/sprites/`: Character facing-direction sprites
- `assets/sprites/business_man_1_forward.png`: Character sprite facing down/forward
- `assets/sprites/business_man_1_back.png`: Character sprite facing up/backward
- `assets/sprites/business_man_1_left.png`: Character sprite facing left
- `assets/sprites/business_man_1_right.png`: Character sprite facing right

## Requirements

- Python 3.9+
- `pygame`

Install dependencies:

```bash
pip install pygame
```

## Run

From the project directory:

```bash
# Manual-control mode
python run.py

# A* pathfinding demo
python run_astar.py
```

## Controls

- `Arrow Up`: Move one tile up and face backward
- `Arrow Down`: Move one tile down and face forward
- `Arrow Left`: Move one tile left
- `Arrow Right`: Move one tile right
- `Esc`: Exit

## Roadmap

- Add continuous movement and interpolation between tiles
- Introduce obstacles, rewards, and terminal states
- Add Q-learning agent training loop
- Add episode logging and visual debugging tools

## Version History

### v0.1.0 - Initial Prototype

- Added checkerboard grid rendering with two green tones
- Added tile-based arrow-key movement
- Added orientation-aware sprite switching for all four directions
- Organized repository structure into `src/` and `assets/sprites/`
- Added project documentation and MIT license

### v0.2.0 - Tarmac and Obstacles

- Replaced checkerboard rendering with tiled tarmac background
- Added one random placement each for three building assets
- Added collision logic to prevent entering building-occupied tiles

### v0.2.1 - Grid Lines and Interior Spawns

- Added faint gray tile borders to preserve clear grid visibility over tarmac
- Restricted random building placement to interior cells (no edge placement)

### v0.2.2 - Full-Window Grid Fit

- Aligned window dimensions exactly to grid dimensions to remove right and bottom overflow
- Reduced grid border intensity using low-alpha gray overlay lines

### v0.2.3 - Bank and Spawn Layout

- Added `bank.png` placement at the bottom-right tile
- Updated player spawn to always start at the top-left tile
- Added gray base tiles under buildings and a green base tile under the bank

### v0.2.4 - Fixed Building Layout

- Replaced random building spawns with fixed grid coordinates for consistent map layout

### v0.3.0 - A* Pathfinding Demo

- Added separate `run_astar.py` entry point for autonomous pathfinding mode
- Implemented A* search in `src/astar_demo.py` to route from start to bank while avoiding obstacles
- Added animated step-by-step movement and facing updates along the computed path

### v0.3.1 - Denser A* Obstacles

- Updated A* demo map to place 4 instances each of `building_1`, `building_2`, and `building_3`

### v0.3.2 - Randomized A* Buildings

- Updated A* demo to randomly place 4 instances of each building type on each run
- Added layout validation so generated obstacles always leave a valid path to the bank

### v0.3.3 - Randomized A* Bank

- Updated A* demo to randomly place the bank on open interior tiles
- `R` now regenerates both bank and obstacle layout while preserving path solvability

## Contributing

Contributions are welcome. Please open an issue or pull request with a clear description of proposed changes.

## License

This project is licensed under the MIT License. See `LICENSE` for full text.
