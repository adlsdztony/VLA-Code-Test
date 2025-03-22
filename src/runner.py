import os
import gymnasium as gym
import time
from mani_skill.utils.wrappers.record import RecordEpisode
from mani_skill.utils.wrappers import FlattenActionSpaceWrapper
# TODO: Change this to import your env
from examples.card_stack_env import CardStackEnv  # noqa: F401
from envs.two_robot_card_stack_env import TwoRobotCardStackEnv  # noqa: F401
from envs.card_stack_env_with_robot_camera import CardStackWithRobotCameraEnv  # noqa: F401

def generate_videos(env_id, n_episodes=10, max_steps_per_episode=100):
    """
    Generate and save videos of random agent interactions in the CardStack environment.
    """
    video_dir = f"videos/{env_id}"
    env = gym.make(env_id, obs_mode="state", render_mode="rgb_array", num_envs=1)
    video_dir = os.path.join(video_dir, time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(video_dir, exist_ok=True)

    # Flatten action space is required when environment has multi-robot
    if "TwoRobot" in env_id:
        env = FlattenActionSpaceWrapper(env)

    env = RecordEpisode(env, output_dir=video_dir, save_video=True, 
                        trajectory_name="random_actions", max_steps_per_video=max_steps_per_episode)
    for _ in range(n_episodes):
        obs, info = env.reset()
        for _ in range(max_steps_per_episode):
            action = env.action_space.sample()  # Take random action
            obs, reward, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                break
    env.close()

if __name__ == "__main__":
    generate_videos("CardStackWithRobotCamera-v1", n_episodes=2)
