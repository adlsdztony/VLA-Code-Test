from typing import Dict

import mani_skill.envs.utils.randomization as randomization
import numpy as np
import sapien
import torch
from mani_skill.agents.robots.panda.panda_stick import PandaStick
from mani_skill.envs.sapien_env import BaseEnv
from mani_skill.sensors.camera import CameraConfig
from mani_skill.utils import sapien_utils
from mani_skill.utils.geometry.rotation_conversions import quaternion_to_matrix, matrix_to_quaternion
from mani_skill.utils.registration import register_env
from mani_skill.utils.scene_builder.table.scene_builder import TableSceneBuilder
from mani_skill.utils.structs.actor import Actor
from mani_skill.utils.structs.pose import Pose
from mani_skill.utils.structs.types import SceneConfig, SimConfig
from transforms3d.euler import euler2quat


@register_env("SimpleAddition-v1", max_episode_steps=500)
class SimpleAdditionEnv(BaseEnv):
    """
    **Task Description:**
    Instantiates a table with a white canvas on it and a robot with a brush attached to its end effector. 
    The robot's task is to draw the sum of two randomly generated numbers on the canvas. 
    The numbers are represented as SVGs.
    
    **Randomizations:**
    - the svg's position on the xy-plane is randomized
    - the numbers to be added are randomly generated
    
    **Success Conditions:**
    - The robot must draw the correct sum of the two numbers on the canvas.
    """

    MAX_DOTS = 1000
    """
    The total "ink" available to use and draw with before you need to call env.reset. NOTE that on GPU simulation it is not recommended to have a very high value for this as it can slow down rendering
    when too many objects are being rendered in many scenes.
    """
    DOT_THICKNESS = 0.003
    """thickness of the paint drawn on to the canvas"""
    CANVAS_THICKNESS = 0.02
    """How thick the canvas on the table is"""
    BRUSH_RADIUS = 0.01
    """The brushes radius"""
    BRUSH_COLORS = [[0.8, 0.2, 0.2, 1]]
    """The colors of the brushes. If there is more than one color, each parallel environment will have a randomly sampled color."""
    THRESHOLD = 0.1

    SUPPORTED_REWARD_MODES = ["sparse"]

    SUPPORTED_ROBOTS = ["panda_stick"]  # type: ignore
    agent: PandaStick

    def __init__(self, *args, svg=None, robot_uids="panda_stick", **kwargs):

        if svg == None:
            self.svg = """M7.875 0L0 7.875V55.125L7.875 63H23.763L23.7235 62.9292L11.8418 51.2859L11.8418 35.6268L21.1302 26.915L23.9193 11.6649L40.9773 6.3631L46.8835 16.5929L33.2356 19.926L32.6417 29.1349L41.1407 33.618L50.8511 23.465L56.6781 33.5577L43.5576 45.6794L28.9369 40.4365L26.1844 42.4266L26.1844 45.6794L43.2157 63H55.125L63 55.125V7.875L55.125 0H7.875Z"""
            self.continuous = True
        else:
            self.svg = svg
        self.svgs = {
            "0": """M12 20C14.7614 20 17 17.7614 17 15V9C17 6.23858 14.7614 4 12 4C9.23858 4 7 6.23858 7 9V15C7 17.7614 9.23858 20 12 20Z""",
            "1": """M12 20V4L9 7""",
            "2": """M8 8C8 6.97631 8.39052 5.95262 9.17157 5.17157C10.7337 3.60947 13.2663 3.60947 14.8284 5.17157C16.3905 6.73366 16.3905 9.26632 14.8284 10.8284L9.17157 16.4853C8.42143 17.2354 8 18.2528 8 19.3137L8 20L16 20""",
            "3": """M8 19.0004C8.83566 19.6281 9.87439 20 11 20C13.7614 20 16 17.7614 16 15C16 12.2386 13.7614 10 11 10L16 4H8""",
            "4": """M10 4L8.47845 11.6078C8.23093 12.8453 9.17752 14 10.4396 14H16M16 14V8M16 14V20""",
            "5": """M8 19.0004C8.83566 19.6281 9.87439 20 11 20C13.7614 20 16 17.7614 16 15C16 12.2386 13.7614 10 11 10C9.87439 10 8.83566 10.3719 8 10.9996L9 4H16""",
            "6": """M13 4L7.77313 12.3279M17 15C17 17.7614 14.7614 20 12 20C9.23858 20 7 17.7614 7 15C7 12.2386 9.23858 10 12 10C14.7614 10 17 12.2386 17 15Z""",
            "7": """M8 4H16L10 20""",
            "8": """M18,9H14a2,2,0,0,0-2,2V21a2,2,0,0,0,2,2h4a2,2,0,0,0,2-2V11A2,2,0,0,0,18,9Zm0,2v4H14V11ZM14,21V17h4v4Z""",
            "9": """M11 20L16.2269 11.6721M7 9C7 6.23858 9.23858 4 12 4C14.7614 4 17 6.23858 17 9C17 11.7614 14.7614 14 12 14C9.23858 14 7 11.7614 7 9Z""",
            "+": """M486 691h52V538h153v-52H538V333h-52v153H333v52h153z""",
            "=": """M17.5 9.813v2.25h-15.813v-2.25h15.813zM17.5 16.656v2.281h-15.813v-2.281h15.813z"""
        }
        super().__init__(*args, robot_uids=robot_uids, **kwargs)

    @property
    def _default_sim_config(self):
        # we set contact_offset to a small value as we are not expecting to make any contacts really apart from the brush hitting the canvas too hard.
        # We set solver iterations very low as this environment is not doing a ton of manipulation (the brush is attached to the robot after all)
        return SimConfig(
            sim_freq=100,
            control_freq=20,
            scene_config=SceneConfig(
                contact_offset=0.01,
                solver_position_iterations=4,
                solver_velocity_iterations=0,
            ),
        )

    @property
    def _default_sensor_configs(self):
        pose = sapien_utils.look_at(eye=[0.3, 0, 0.8], target=[0, 0, 0.1])
        return [
            CameraConfig(
                "base_camera",
                pose=pose,
                width=320,
                height=240,
                fov=1.2,
                near=0.01,
                far=100,
            )
        ]

    @property
    def _default_human_render_camera_configs(self):
        pose = sapien_utils.look_at(eye=[0.3, 0, 0.8], target=[0, 0, 0.1])
        return CameraConfig(
            "render_camera",
            pose=pose,
            width=1280,
            height=960,
            fov=1.2,
            near=0.01,
            far=100,
        )

    def _load_scene(self, options: dict):
        try:
            import svgpathtools
            from svgpathtools import CubicBezier, Line, QuadraticBezier
        except ImportError:
            raise ImportError(
                "svgpathtools not installed. Install with pip install svgpathtools"
            )

        self.table_scene = TableSceneBuilder(self, robot_init_qpos_noise=0)
        self.table_scene.build()
        self.original_points = {}

        def bezier_points(points, num_points=5):
            """
            Generate points along a quadratic or cubic Bezier curve using numpy.

            Args:
                *points: Variable number of control points as (x,y) tuples:
                        - For quadratic: (start, control, end)
                        - For cubic: (start, control1, control2, end)
                num_points: Number of points to generate along curve

            Returns:
                Array of points along the curve, shape (num_points, 2)
            """
            points = np.array(points)

            if len(points) not in [3, 4]:
                raise ValueError(
                    "Must provide either 3 points (quadratic) or 4 points (cubic)"
                )
            t = np.linspace(0, 1, num_points).reshape(-1, 1)

            if len(points) == 3:
                p0, p1, p2 = points
                points = (1 - t) ** 2 * p0 + 2 * t * (1 - t) * p1 + t**2 * p2
            else:
                p0, p1, p2, p3 = points
                points = (
                    (1 - t) ** 3 * p0
                    + 3 * t * (1 - t) ** 2 * p1
                    + 3 * t**2 * (1 - t) * p2
                    + t**3 * p3
                )

            return points

        def create_svg_outline(name="0", base_color=None):
            parsed_svg = svgpathtools.parse_path(self.svgs[name])

            lines = []
            for path in parsed_svg:
                if isinstance(path, QuadraticBezier) or isinstance(path, CubicBezier):
                    pts = bezier_points([[p.real, p.imag] for p in path.bpoints()])
                    for i in range(len(pts) - 1):
                        lines.append([pts[i], pts[i + 1]])
                if isinstance(path, Line):
                    lines.append([[p.real, p.imag] for p in path.bpoints()])
            lines = np.array(lines)  # n, 2, 2
            lines = (lines / np.max(lines)) * 0.25  # scale the svg down to fit
            lines = np.concatenate(
                [lines, np.ones((*lines.shape[:-1], 1)) * 0.01], -1
            )  # b, 2, 3
            center = lines[:, :1, :].mean(axis=0) * np.array(
                [[1, 1, 0]]
            )  # calculate transform to be in range of arm
            lines = lines - center
            if not parsed_svg.iscontinuous():

                disconts = lines[1:, 0] - lines[:-1, 1]
                self.disconts = list(
                    np.nonzero(np.logical_or(disconts[:, 0], disconts[:, 1]))[0]
                )  # indices of where the discontinuities are ie. [1,]: discont betw ind 1 and 2
                self.continuous = False

            self.original_points[name] = np.concatenate((lines[:1, 0], lines[:, 1, :]))

            midpoints = np.mean(lines, axis=1)  # midpoints of line segments
            box_half_ws = np.linalg.norm(lines[:, 1] - lines[:, 0], axis=1) / 2

            box_half_h = 0.01 / 2
            half_thickness = 0.001 / 2
            mids = midpoints[:, :2]
            ends = lines[:, 1, :2]  # n, 2

            # calculate rot angles abt z axis
            vec = ends - mids
            angles = np.arctan2(vec[:, 1], vec[:, 0])

            builder = self.scene.create_actor_builder()
            for i, m in enumerate(midpoints):
                pose = sapien.Pose(p=m, q=euler2quat(0, 0, angles[i]))

                builder.add_box_visual(
                    pose=pose,
                    half_size=[box_half_ws[i], box_half_h, half_thickness],  # type: ignore
                    material=sapien.render.RenderMaterial(
                        base_color=base_color,
                    ),
                )

            builder.initial_pose = sapien.Pose(p=[0, 0, -1])
            return builder.build_kinematic(name=name)

        # build a white canvas on the table
        self.canvas = self.scene.create_actor_builder()
        self.canvas.add_box_visual(
            half_size=[0.4, 0.6, self.CANVAS_THICKNESS / 2],
            material=sapien.render.RenderMaterial(base_color=[1, 1, 1, 1]),
        )
        self.canvas.add_box_collision(
            half_size=[0.4, 0.6, self.CANVAS_THICKNESS / 2],
        )
        self.canvas.initial_pose = sapien.Pose(p=[-0.1, 0, self.CANVAS_THICKNESS / 2])
        self.canvas = self.canvas.build_static(name="canvas")

        self.dots = []
        color_choices = torch.randint(0, len(self.BRUSH_COLORS), (self.num_envs,))
        for i in range(self.MAX_DOTS):
            actors = []
            if len(self.BRUSH_COLORS) > 1:
                for env_idx in range(self.num_envs):
                    builder = self.scene.create_actor_builder()
                    builder.add_cylinder_visual(
                        radius=self.BRUSH_RADIUS,
                        half_length=self.DOT_THICKNESS / 2,
                        material=sapien.render.RenderMaterial(
                            base_color=self.BRUSH_COLORS[color_choices[env_idx]]
                        ),
                    )
                    builder.set_scene_idxs([env_idx])
                    builder.initial_pose = sapien.Pose(p=[0, 0, 0.1])
                    actor = builder.build_kinematic(name=f"dot_{i}_{env_idx}")
                    actors.append(actor)
                self.dots.append(Actor.merge(actors))
            else:
                builder = self.scene.create_actor_builder()
                builder.add_cylinder_visual(
                    radius=self.BRUSH_RADIUS,
                    half_length=self.DOT_THICKNESS / 2,
                    material=sapien.render.RenderMaterial(
                        base_color=self.BRUSH_COLORS[0]
                    ),
                )
                builder.initial_pose = sapien.Pose(p=[0, 0, 0.1])
                actor = builder.build_kinematic(name=f"dot_{i}")
                self.dots.append(actor)

        self.svg_outlines = {key: create_svg_outline(name=key, base_color=np.array([10, 10, 10, 255]) / 255) for key in self.svgs.keys()}

        self.dots_dist = torch.ones((self.num_envs, 500), device=self.device) * -1

    def _initialize_episode(self, env_idx: torch.Tensor, options: dict):
        self.draw_step = 0
        with torch.device(self.device):
            b = len(env_idx)
            self.table_scene.initialize(env_idx)
            target_pos = torch.zeros((b, 3))

            target_pos[:, :2] = torch.rand((b, 2)) * 0.02 - 0.1
            target_pos[:, -1] = 0.01

            for outline in self.svg_outlines.values():
                outline.set_pose(Pose.create_from_pq(p=[0, 0, -1]))

            # random 2 numbers
            self.num1 = np.random.randint(0, 9)
            self.num2 = np.random.randint(0, 9 - self.num1)
            self.sum = self.num1 + self.num2
            self.goal_outline = self.svg_outlines[str(self.sum)]
            self.num1_outline = self.svg_outlines[str(self.num1)]
            self.num2_outline = self.svg_outlines[str(self.num2)]
            print(self.num1, self.num2, self.sum)

            # flip and rotate 90 degrees
            q = torch.tensor([0, np.sqrt(2) / 2, np.sqrt(2) / 2, 0])
            rot_mat = quaternion_to_matrix(q).to(self.device)

            # self.goal_outline.set_pose(Pose.create_from_pq(p=target_pos))
            self.num1_outline.set_pose(Pose.create_from_pq(p=target_pos + torch.tensor([0, -0.4, 0.02]), q=q))
            self.svg_outlines["+"].set_pose(Pose.create_from_pq(p=target_pos + torch.tensor([0, -0.2, 0.02]), q=q))
            self.num2_outline.set_pose(Pose.create_from_pq(p=target_pos + torch.tensor([0, 0, 0.02]), q=q))
            self.svg_outlines["="].set_pose(Pose.create_from_pq(p=target_pos + torch.tensor([0, 0.2, 0.02]), q=q))

            if hasattr(self, "vertices"):
                self.points[env_idx] = torch.from_numpy(
                    np.tile(self.original_points[str(self.sum)], (b, 1, 1))
                ).to(
                    self.device
                )  # b, 3, 3
            else:
                self.points = torch.from_numpy(
                    np.tile(self.original_points[str(self.sum)], (b, 1, 1))
                ).to(self.device)

            self.points[env_idx] = (
                rot_mat.double() @ self.points[env_idx].transpose(-1, -2).double()
            ).transpose(
                -1, -2
            )  # rotation matrix
            self.points[env_idx] += (target_pos+torch.tensor([0, 0.4, 0.02])).unsqueeze(1)
            self.dots_dist[env_idx] = torch.ones((self.num_envs, 500)) * -1

            for dot in self.dots:
                # initially spawn dots in the table so they aren't seen
                dot.set_pose(
                    sapien.Pose(
                        p=[0, 0, -self.DOT_THICKNESS], q=euler2quat(0, np.pi / 2, 0)
                    )
                )

    def _after_control_step(self):
        if self.gpu_sim_enabled:
            self.scene._gpu_fetch_all()

        # This is the actual, GPU parallelized, drawing code.
        # This is not real drawing but seeks to mimic drawing by placing dots on the canvas whenever the robot is close enough to the canvas surface
        # We do not actually check if the robot contacts the table (although that is possible) and instead use a fast method to check.
        # We add a 0.005 meter of leeway to make it easier for the robot to get close to the canvas and start drawing instead of having to be super close to the table.
        robot_touching_table = (
            self.agent.tcp.pose.p[:, 2]
            < self.CANVAS_THICKNESS + self.DOT_THICKNESS + 0.005
        )
        robot_brush_pos = torch.zeros((self.num_envs, 3), device=self.device)
        robot_brush_pos[:, 2] = -self.DOT_THICKNESS
        robot_brush_pos[robot_touching_table, :2] = self.agent.tcp.pose.p[
            robot_touching_table, :2
        ]
        robot_brush_pos[robot_touching_table, 2] = (
            self.DOT_THICKNESS / 2 + self.CANVAS_THICKNESS
        )
        # move the next unused dot to the robot's brush position. All unused dots are initialized inside the table so they aren't visible
        new_dot_pos = Pose.create_from_pq(robot_brush_pos, euler2quat(0, np.pi / 2, 0))
        self.dots[self.draw_step].set_pose(new_dot_pos)

        self.draw_step += 1

        # on GPU sim we have to call _gpu_apply_all() to apply the changes we make to object poses.
        if self.gpu_sim_enabled:
            self.scene._gpu_apply_all()

    def evaluate(self):
        out = self.success_check()
        return {"success": out}

    def _get_obs_extra(self, info: Dict):
        obs = dict(
            tcp_pose=self.agent.tcp.pose.raw_pose,
        )
        return obs

    def success_check(self):
        if self.draw_step > 0:
            current_dot = self.dots[self.draw_step - 1].pose.p.reshape(
                self.num_envs, 1, 3
            )  # b,3
            z_mask = current_dot[:, :, 2] < 0
            dist = (
                torch.sqrt(
                    torch.sum(
                        (current_dot[:, :, None, :2] - self.points[:, None, :, :2])
                        ** 2,
                        dim=-1,
                    )
                )
                < self.THRESHOLD
            )
            reshaped = dist.reshape((self.num_envs, -1))
            self.ref_dist = torch.zeros_like(reshaped, dtype=torch.bool, device=self.device)
            self.ref_dist = torch.logical_or(
                self.ref_dist, (1 - z_mask.int()) * reshaped
            )
            self.dots_dist[:, self.draw_step - 1] = torch.where(
                z_mask, -1, torch.any(dist, dim=-1)
            ).reshape(
                self.num_envs,
            )

            mask = self.dots_dist > -1
            # for valid drawn points
            return torch.logical_and(
                torch.all(self.dots_dist[mask], dim=-1),
                torch.all(self.ref_dist, dim=-1),
            )
        return torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
