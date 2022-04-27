import numpy as np
from gym.envs.mujoco.ant_v3 import AntEnv

MAX_EPISODE_STEPS_ANTJUMP = 200


class ALRAntJumpEnv(AntEnv):
    """
    Initialization changes to normal Ant:
    - healthy_reward: 1.0 -> 0.01 -> 0.0 no healthy reward needed - Paul and Marc
    - ctrl_cost_weight 0.5 -> 0.0
    - contact_cost_weight: 5e-4 -> 0.0
    - healthy_z_range: (0.2, 1.0) -> (0.3, float('inf'))  !!!!! Does that make sense, limiting height?
    """

    def __init__(self,
                 xml_file='ant.xml',
                 ctrl_cost_weight=0.0,
                 contact_cost_weight=0.0,
                 healthy_reward=0.0,
                 terminate_when_unhealthy=True,
                 healthy_z_range=(0.3, float('inf')),
                 contact_force_range=(-1.0, 1.0),
                 reset_noise_scale=0.1,
                 context=True,  # variable to decide if context is used or not
                 exclude_current_positions_from_observation=True,
                 max_episode_steps=200):
        self.current_step = 0
        self.max_height = 0
        self.context = context
        self.max_episode_steps = max_episode_steps
        self.goal = 0  # goal when training with context
        super().__init__(xml_file, ctrl_cost_weight, contact_cost_weight, healthy_reward, terminate_when_unhealthy,
                         healthy_z_range, contact_force_range, reset_noise_scale,
                         exclude_current_positions_from_observation)

    def step(self, action):

        self.current_step += 1
        self.do_simulation(action, self.frame_skip)

        height = self.get_body_com("torso")[2].copy()

        self.max_height = max(height, self.max_height)

        rewards = 0

        ctrl_cost = self.control_cost(action)
        contact_cost = self.contact_cost

        costs = ctrl_cost + contact_cost

        done = height < 0.3 # fall over -> is the 0.3 value from healthy_z_range? TODO change 0.3 to the value of healthy z angle

        if self.current_step == self.max_episode_steps or done:
            if self.context:
                # -10 for scaling the value of the distance between the max_height and the goal height; only used when context is enabled
                # height_reward = -10 * (np.linalg.norm(self.max_height - self.goal))
                height_reward = -10*np.linalg.norm(self.max_height - self.goal)
                # no healthy reward when using context, because we optimize a negative value
                healthy_reward = 0
            else:
                height_reward = self.max_height - 0.7
                healthy_reward = self.healthy_reward * self.current_step

            rewards = height_reward + healthy_reward

        obs = self._get_obs()
        reward = rewards - costs

        info = {
            'height': height,
            'max_height': self.max_height,
            'goal': self.goal
        }

        return obs, reward, done, info

    def _get_obs(self):
        return np.append(super()._get_obs(), self.goal)

    def reset(self):
        self.current_step = 0
        self.max_height = 0
        self.goal = np.random.uniform(1.0, 2.5,
                                      1)  # goal heights from 1.0 to 2.5; can be increased, but didnt work well with CMORE
        return super().reset()

    # reset_model had to be implemented in every env to make it deterministic
    def reset_model(self):
        noise_low = -self._reset_noise_scale
        noise_high = self._reset_noise_scale

        qpos = self.init_qpos  # + self.np_random.uniform(low=noise_low, high=noise_high, size=self.model.nq)
        qvel = self.init_qvel  # + self.np_random.uniform(low=noise_low, high=noise_high, size=self.model.nv)

        self.set_state(qpos, qvel)

        observation = self._get_obs()
        return observation

if __name__ == '__main__':
    render_mode = "human"  # "human" or "partial" or "final"
    env = ALRAntJumpEnv()
    obs = env.reset()

    for i in range(2000):
        # objective.load_result("/tmp/cma")
        # test with random actions
        ac = env.action_space.sample()
        obs, rew, d, info = env.step(ac)
        if i % 10 == 0:
            env.render(mode=render_mode)
        if d:
            env.reset()

    env.close()