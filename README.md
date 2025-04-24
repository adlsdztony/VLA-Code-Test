# VLA-Code-Test

## dependencies and virtual environment
[uv](https://docs.astral.sh/uv/) is used to manage the virtual environment and the dependencies.

If uv is installed, simply run
```bash
# Create a virtual environment and install the dependencies
uv sync --prerelease=allow # --prerelease=allow is needed to install mani_skill
uv run src/runner.py
```

If you don't have uv installed, simply ignore the following files:
- `.python-version`
- `pyproject.toml`
- `uv.lock`

## Issue with RecordEpisode on multi-robot environment
According to this [issue](https://github.com/haosulab/ManiSkill/issues/776), `RecordEpisode` does not work on the environment with multiple robots, `FlattenActionSpaceWrapper` is required to be used in the environment to make it work. 

## Modifications in runner.py
`generate_videos` is modified to use `FlattenActionSpaceWrapper` when the envid contains `TwoRobot`. (just for the test)

The save path of the video is changed to `./videos/` instead of `./` so in gitignore, `videos/` is added.

## Envs built
All the environments are located in `src/envs/`.
### TwoRobotCardStack-v1
- TwoRobotCardStack-v1 is built by adding an additional robot to the CardStack-v1.
- `_get_obs_extra` is modified to add the observation of the second robot.
- Reward function is modified to add a reward for the second robot.
### CardStackWithRobotCamera-v1
- CardStackWithRobotCamera-v1 is built by adding a camera to the CardStack-v1.
- Rendering the video with the camera on the robot.
### SimpleAddition-v1
- SimpleAddition-v1 is built on DrawSVG-v1.
- The task is to add two numbers and write the result on the whiteboard.
- An extra dependancy `svgpathtools` should be installed to run this environment.

<!-- # Name	Description	Objects	Atomic Actions	Reasoning Process	Sim2Real Gap
# CardSelection-v1	The robot must identify the target card (marked with green underneath) from a 3×4 grid of 12 cards and move it to a designated blue target area. Other cards have yellow (near target) or red (no target nearby) markers as hints.	<ul><li>12 gray movable cards</li><li>12 static colored markers</li><li>1 blue target marker</li></ul>	<ul><li>Observe card colors</li><li>Grasp card</li><li>Move card</li><li>Place card</li></ul>	1. Observation Phase: Scan the card grid to locate the green marker (target). If not directly visible, prioritize yellow-marked cards (proximity hints).
# 2. Decision Phase: Move the green-marked card first; if unavailable, explore yellow-marked cards and their surroundings.
# 3. Execution Phase:
# a) Precise grasping of the target card without disturbing others.
# b) Smooth transportation to the blue target zone.
# c) Ensure full coverage of the target area with no collisions.
# 4. Verification: Confirm only the target card is placed correctly.	<ul><li>Card physics (thickness/flexibility) may differ in reality.</li><li>Visual marker recognition gaps (camera vs. simulation).</li><li>Real-world grid alignment errors.</li><li>Multi-card interaction physics (e.g., sliding/friction).</li></ul> -->