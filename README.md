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
### TwoRobotCardStack-v1
- TwoRobotCardStack-v1 is built by adding an additional robot to the CardStack-v1.
- `_get_obs_extra` is modified to add the observation of the second robot.
- Reward function is modified to add a reward for the second robot.
