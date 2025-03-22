import gymnasium as gym
from examples.card_stack_env import CardStackEnv # noqa: F401
from envs.card_stack_env_with_robot_camera import CardStackWithRobotCameraEnv # noqa: F401

def test_env(env_id):
    env = gym.make(
        env_id, # there are more tasks e.g. "PushCube-v1", "PegInsertionSide-v1", ...
        num_envs=1,
        obs_mode="state", # there is also "state_dict", "rgbd", ...
        control_mode="pd_ee_delta_pose", # there is also "pd_joint_delta_pos", ...
        render_mode="human"
    )
    print("Observation space", env.observation_space)
    print("Action space", env.action_space)

    obs, _ = env.reset(seed=0) # reset with a seed for determinism
    done = False
    while not done:
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        # done = terminated or truncated
        env.render()  # a display is required to render
    env.close()

if __name__ == "__main__":
    test_env("CardStackWithRobotCamera-v1")