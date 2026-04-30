# Q-Learning Grid Prototype

This repository contains a lightweight Pygame prototype for a grid-based character movement environment. It is intended as a foundation for reinforcement learning experiments and gameplay iteration.

## Current Features

- Tile-based tarmac background using `assets/elems/tarmac.png`
- Keyboard movement using arrow keys
- Direction-aware character sprite swapping (`forward`, `back`, `left`, `right`)
- Randomized building placement (`building_1`, `building_2`, `building_3`) with one of each per run
- Movement constrained to the visible grid bounds and blocked by building obstacles

## Project Structure

- `run.py`: Entry point to start the prototype
- `src/main.py`: Main Pygame loop, rendering, input handling, and movement logic
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
python run.py
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

## Contributing

Contributions are welcome. Please open an issue or pull request with a clear description of proposed changes.

## License

This project is licensed under the MIT License. See `LICENSE` for full text.
