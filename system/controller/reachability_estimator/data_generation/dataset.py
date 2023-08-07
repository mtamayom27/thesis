''' This code has been adapted from:
***************************************************************************************
*    Title: "Scaling Local Control to Large Scale Topological Navigation"
*    Author: "Xiangyun Meng, Nathan Ratliff, Yu Xiang and Dieter Fox"
*    Date: 2020
*    Availability: https://github.com/xymeng/rmp_nav
*
***************************************************************************************
'''
import h5py
import torch.utils.data as data
import numpy as np
import itertools
import bisect
import random
import matplotlib.pyplot as plt

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.environment.map_occupancy_helpers.map_utils import path_length
from system.controller.local_controller.local_navigation import vector_navigation, create_gc_spiking, setup_gc_network
from system.plotting.plotResults import plotTrajectoryInEnvironment, plotStartGoalDataset


def get_path():
    """ returns path to data storage folder """
    dirname = os.path.join(os.path.dirname(__file__), "..")
    return dirname


plotting = False  # if True: plot every reachability rollout
debug = False  # if True: print debug output


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


class ReachabilityDataset(data.Dataset):
    '''
    Generate data for the reachability estimator training.
    
    arguments:
    hd5_files           -- hd5_files containing trajectories used to generate reachability data
                            format: attributes: agent, map; data per timestep: xy_coordinates, orientation, grid cell spiking
                            see gen_trajectories.py for details
                 
    distance_min/max    --  min/max distance between goal and start
    range_min/max       --  min/max timesteps between goal and start
    n_frame             --  number of frames in destination sequence
    frame_interval      --  number of timesteps between frames
    
    For details see original source code: https://github.com/xymeng/rmp_nav
    '''

    def __init__(self, hd5_files, distance_min, distance_max, range_min, range_max, n_frame, frame_interval):

        self.distance_min = distance_min
        self.distance_max = distance_max
        self.range_min = range_min
        self.range_max = range_max

        self.n_frame = n_frame
        self.frame_interval = frame_interval

        self.hd5_files = sorted(list(hd5_files))

        # open hd5 files
        maps = []
        fds = []
        for fn in self.hd5_files:
            try:
                fds.append(h5py.File(fn, 'r'))
                maps.append(fds[-1].attrs["map_type"])
            except:
                print('unable to open', fn)
                raise

        def flatten(ll):
            return list(itertools.chain.from_iterable(ll))

        # A list of tuples (dataset_idx, trajectory_id)
        self.traj_ids = flatten(
            zip(itertools.repeat(i),
                list(fds[i].keys())[0:len(fds[i])])
            for i in range(len(fds)))
        print_debug('total trajectories:', len(self.traj_ids))

        # Map (dataset_idx, traj_id) to trajectory length
        self.traj_len_dict = {(i, tid): fds[i][tid].shape[0] for i, tid in self.traj_ids}
        self.traj_len_cumsum = np.cumsum([self.traj_len_dict[_] for _ in self.traj_ids])

        def maybe_decode(s):
            # This is to deal with the breaking change in how h5py 3.0 deals with
            # strings.
            if type(s) == str:
                return s
            else:
                return s.decode('ascii')

        # Map (dataset_idx, traj_id) to its corresponding map
        traj_id_map = {(dset_idx, traj_id): maybe_decode(fds[dset_idx].attrs['map_type'])
                       for dset_idx, traj_id in self.traj_ids}

        self.map_names = maps
        map_name_set = set(maps)
        self.layout = MapLayout(self.map_names[0])

        traj_ids_per_map = {_: [] for _ in self.map_names}
        for dset_idx, traj_id in self.traj_ids:
            map_name = traj_id_map[(dset_idx, traj_id)]
            if map_name in map_name_set:
                traj_ids_per_map[map_name].append((dset_idx, traj_id))
        self.traj_ids_per_map = traj_ids_per_map

        self.samples_per_map = {
            map_name: sum([self.traj_len_dict[_] for _ in traj_ids])
            for map_name, traj_ids in traj_ids_per_map.items()}
        print_debug(self.samples_per_map)

        # Map a map name to cumulative sum of trajectory lengths.
        self.traj_len_cumsum_per_map = {
            # Note than when computing cumsum we must ensure the ordering. Hence we must
            # not use .values().
            map_name: np.cumsum([self.traj_len_dict[_] for _ in traj_ids])
            for map_name, traj_ids in traj_ids_per_map.items()}

        self.opened = False
        self.load_to_mem = False
        self.first = True

    def _init_once(self, seed):
        # Should be called after the dataset runs in a separate process
        if self.first:
            self._open_datasets()
            self.rng = np.random.RandomState(12345 + (seed % 1000000) * 666)
            self.first = False
            print("Init finished")

    # open the dataset
    def _open_datasets(self):
        if not self.opened:
            driver = None
            if self.load_to_mem:
                driver = 'core'
                print('loading dataset into memory... it may take a while')
            self.fds = [h5py.File(fn, 'r', driver=driver)
                        for fn in self.hd5_files]
            self.opened = True

    def locate_traj(self, traj_id):
        return self.fds[traj_id[0]][traj_id[1]]

    def _locate_sample(self, idx):
        traj_idx = bisect.bisect_right(self.traj_len_cumsum, idx)
        dataset_idx, traj_id = self.traj_ids[traj_idx]

        if traj_idx == 0:
            sample_idx = idx
        else:
            sample_idx = idx - self.traj_len_cumsum[traj_idx - 1]

        return dataset_idx, traj_id, sample_idx

    def _locate_sample_single_map(self, idx, map_name):
        """
        Similar to _locate_sample(), but only considers a single map.
        :param idx: sample index in the range of [0, total number of samples of this map - 1]
        """
        cumsum = self.traj_len_cumsum_per_map[map_name]
        assert 0 <= idx < cumsum[-1], 'Map index %d out of range [0, %d)' % (idx, cumsum[-1])

        trajs = self.traj_ids_per_map[map_name]

        traj_idx = bisect.bisect_right(cumsum, idx)
        dataset_idx, traj_id = trajs[traj_idx]

        if traj_idx == 0:
            sample_idx = idx
        else:
            sample_idx = idx - cumsum[traj_idx - 1]

        return dataset_idx, traj_id, sample_idx

    def __len__(self):
        return self.traj_len_cumsum[-1]

    def _draw_sample_same_traj(self, idx):
        """ Draw a source and goal sample from the same trajectory.
            Their distance will be between distance_min and distance_max.
            They will be seperated by timesteps in range of range_min to range_max.
        
        returns:
        name of map, source sample, destination sample
        """
        timerange = self.rng.uniform(self.range_min, self.range_max)
        distance = self.rng.uniform(self.distance_min, self.distance_max)
        inc = 1

        while True:
            # Get a good pair of samples
            src_dataset_idx, src_traj_id, src_idx = self._locate_sample(idx)

            src_traj = self.fds[src_dataset_idx][src_traj_id] # todo self.map_names[0] like in layout?
            map_name = self.fds[src_dataset_idx].attrs['map_type']

            src_sample = self._jitter(src_traj[src_idx], None)
            src_pos = src_sample[0]

            dst_idx = src_idx + inc
            flag = False
            while 0 <= dst_idx < len(src_traj):
                dst_sample = src_traj[dst_idx]
                dst_pos = dst_sample[0]
                x, y = dst_pos - src_pos
                # If the samples are far enough away from each other both spatially and timerange wise
                # a valid sample has been found.
                if dst_idx - src_idx > timerange and x ** 2 + y ** 2 > distance ** 2:
                    # return path_length
                    goal_pos = list(dst_pos)
                    src_pos = list(src_pos)
                    waypoints = self.layout.find_path(src_pos, goal_pos)
                    # no path found between source and goal -> skip this sample
                    if not waypoints:
                        print_debug("No path found.")
                        break
                    path_l = path_length(waypoints)
                    flag = True
                    break

                dst_idx += inc

            if flag and 0 <= dst_idx < len(src_traj):
                # Found valid dst_sample
                break

            # select another idx if this one doesn't work
            # TODO Johanna: Future Work: Sometimes the data generation gets livelocked.
            #                   This should fix it but could not be tested extensively.
            idx = (idx + self.rng.randint(1000)) % len(self)

        dst_samples = self._make_sample_seq(src_traj, dst_idx)

        return map_name, src_sample, dst_samples, path_l

    def _draw_sample_diff_traj(self, idx):
        """ Draw a source and goal sample from two different trajectories on the same map.
        
        returns:
        name of map, source sample, destination sample, length of path between start and goal
        """

        while True:
            # Get a good pair of samples
            src_dataset_idx, src_traj_id, src_idx = self._locate_sample(idx)

            src_traj = self.fds[src_dataset_idx][src_traj_id]
            map_name = self.fds[src_dataset_idx].attrs['map_type']

            idx2 = self.rng.randint(self.samples_per_map[map_name])
            dst_dataset_idx, dst_traj_id, dst_idx = self._locate_sample_single_map(idx2, map_name)
            dst_traj = self.fds[dst_dataset_idx][dst_traj_id]

            src_sample = self._jitter(src_traj[src_idx], None)
            dst_samples = self._make_sample_seq(dst_traj, dst_idx)

            # return path_length
            goal_pos = list(dst_samples[self.n_frame - 1][0])
            src_pos = list(src_sample[0])
            waypoints = self.layout.find_path(src_pos, goal_pos)
            # no path found between source and goal -> skip this sample
            if not waypoints:
                print_debug("No path found.")
                continue
            path_l = path_length(waypoints)
            return map_name, src_sample, dst_samples, path_l

    def _set_cur_ob(self, ob):
        self.cur_ob = ob

    def _get_ob(self, map_name):
        return self._render_agent_view(map_name)

    def _jitter(self, sample, map):
        # TODO Johanna: Future Work: implement jitter
        # No jitter needed for limited generating time.
        return sample

    def _set_agent_state(self, sample):
        self.agent_pos = sample[0]
        self.agent_orientation = sample[1]

    def _render_agent_view(self, env):
        agent_pos = self.agent_pos
        agent_orn = self.agent_orientation
        agent_pos_orn = (agent_pos, agent_orn)
        img = env.camera(agent_pos_orn)
        return img

    def _make(self, map_name, samples):
        # return img of position
        dt = 1e-2
        env = PybulletEnvironment(False, dt, map_name, "analytical", build_data_set=True)
        imgs = []
        for sample in samples:
            self._set_agent_state(sample)
            imgs.append(self._render_agent_view(env))

        env.end_simulation()
        return imgs

    def _make_sample_seq(self, traj, idx):
        samples = []
        for i in range(self.n_frame):
            samples.append(traj[max(idx - i * self.frame_interval, 0)])
        samples = samples[::-1]
        return samples

    def _compute_overlap(self, map_name, pos1, heading1, pos2, heading2):
        self.fov = 120 * np.pi / 180

        map_layout = MapLayout(map_name)

        overlap_ratios = map_layout.view_overlap(pos1, heading1, self.fov,
                                                 pos2, heading2, self.fov, mode='plane')
        return overlap_ratios

    def reachable(self, env_model, src_sample, dst_sample, same_traj, path_l):
        """ Tests whether the destination is reachable from the start. 
        
        arguments:
        env_model   -- environment used to generate data
        src_sample  --
        dst_sample  -- sample format
                        dtype = np.dtype([
                            ('xy_coordinates', (np.float32, 2)),
                            ('orientation', np.float32),
                            ('grid_cell_spiking', (np.float32, 9600))])
        same_traj   -- if True: sample taken from same trajectory
        
        returns:
        reached         -- 0.0 (agent did not reach the goal) or 1.0 (agent did reach the goal)
        final_distance  -- actual distance between agent and goal
        final_coordinates
        final_orientations -- used to create goal image sequence if necessary
        goal_vector  -- first goal vector the agent decoded at its starting position
        sample_after_turn  -- position and orientation after turning towards the goal
        """

        goal_pos = list(dst_sample[0])
        src_pos = list(src_sample[0])
        src_heading = src_sample[1]

        # Estimate roughly the number of steps required to reach the goal
        # Assume a mean velocity of 0.2 m/s
        # In general this is difficult to precisely estimate it, because it heavily depends on the
        # environment geometry. Here we choose a conservative value.
        mean_vel = 0.2
        step_limit = int((path_l / mean_vel) / 0.1 + 750)
        print_debug("The step_limit is: ", step_limit)

        # reset and init grid cell network, if the samples are from different
        # trajectories generate the necessary grid cell spikings
        dt = 1e-2
        gc_network = setup_gc_network(dt)
        if not same_traj:
            target_spiking = create_gc_spiking(src_pos, goal_pos)
        else:
            source_spiking = src_sample[2].reshape(6, 1600)
            gc_network.set_as_current_state(source_spiking)

            target_spiking = dst_sample[2].reshape(6, 1600)

        # Setup environment
        env = PybulletEnvironment(False, dt, env_model, "combo", build_data_set=True, start=src_pos,
                                  orientation=src_heading)

        if target_spiking is None:
            raise ValueError("There is no target spiking.")

        gc_network.set_as_target_state(target_spiking)

        # Attempt vector navigation from source to goal.
        over, data = vector_navigation(env, goal_pos, gc_network, target_spiking,
                                       model="analytical", step_limit=step_limit,
                                       plot_it=False, collect_data_reachable=True)

        sample_after_turn, goal_vector = data
        if over == -1:
            # Agent got stuck
            reached = 0.0
            title = "Agent stopped moving."
        if over == 1:
            # Agent thinks it reached the goal.
            overlap_ratios = self._compute_overlap(env_model,
                                                   env.xy_coordinates[-1], env.orientation_angle[-1],
                                                   dst_sample[0], dst_sample[1])
            if overlap_ratios[0] < 0.1 and overlap_ratios[1] < 0.1:
                # Agent is close to the goal, but seperated by a wall.
                reached = 0.0
                title = "Agent stuck behind wall."
            elif np.linalg.norm(dst_sample[0] - env.xy_coordinates[-1]) > 0.7:
                # Agent actually didn't reach the goal and is too far away.
                reached = 0.0
                title = "Agent more than 0.7 from actual goal. Distance: " + str(
                    np.round(np.linalg.norm(dst_sample[0] - env.xy_coordinates[-1]), 1))
            else:
                # Agent did actually reach the goal
                reached = 1.0
                title = "Agent reached the goal. Distance: " + str(
                    np.round(np.linalg.norm(dst_sample[0] - env.xy_coordinates[-1]), 1))
        if over == 0:
            # The step_limit was exceeded
            title = "Agent did not reach the goal in time."
            reached = 0.0

        if plotting:
            plotTrajectoryInEnvironment(env, title=title)

        final_coordinates = env.xy_coordinates[::self.frame_interval][
                            -self.n_frame:]  # taken in specified frame_interval
        final_orientations = env.orientation_angle[::self.frame_interval][-self.n_frame:]
        final_distance = str(np.linalg.norm(dst_sample[0] - env.xy_coordinates[-1]))

        return reached, final_distance, final_coordinates, final_orientations, goal_vector, sample_after_turn

    def __getitem__(self, idx):
        ''' Loads or creates a sample. Sample contains ... 
        
        returns:
        
        src_image
        n_frame dst_images
        reachability
        start and goal position
        first decoded goal vector
        src img after turn
        distance between goal and agent'''
        self._init_once(idx) #todo remove from here

        # choose with probability p from same/different trajectory
        p = self.rng.uniform(0.0, 1.0)

        self.sample_diff_traj_prob = 0.1
        if p < self.sample_diff_traj_prob:
            map_name, src_sample, dst_samples, path_l = self._draw_sample_diff_traj(idx)
            same = False
        else:
            map_name, src_sample, dst_samples, path_l = self._draw_sample_same_traj(idx)
            same = True

        dst_sample = dst_samples[self.n_frame - 1]

        src_img = self._make(map_name, [src_sample])[0]

        dst_imgs = self._make(map_name, dst_samples)

        print("Computing reachability")
        r, dist, coo, ori, first_gv, sample_after_turn = self.reachable(map_name, src_sample, dst_sample, same,
                                                                        path_l)
        print("Reachability computed")

        if r is None:
            raise ValueError("no reachability error")

        # render agent view after initial turn
        src_img_after_turn = self._make(map_name, [sample_after_turn])[0]

        # use actual arrival point for images if successful
        if r == 1.0:
            if len(coo) < self.n_frame:
                # Fill up to 10 images by repeating the last image
                coo += [coo[-1]] * (self.n_frame - len(coo))
                ori += [ori[-1]] * (self.n_frame - len(ori))
            samples = [(coo[i], ori[i]) for i in range(self.n_frame)]
            dst_imgs = self._make(map_name, samples)

        # image transformation
        dst_imgs = [np.array(i[2]) for i in dst_imgs]
        return src_img, dst_imgs, r, [src_sample[0], dst_sample[0]], [src_sample[1], dst_sample[1]], first_gv, src_img_after_turn, dist


def create_and_save_reachability_samples(filename, nr_samples, traj_file):
    """ Create reachability samples.
    
    arguments:
    filename    -- save the data in filename
    nr_samples  -- the number of samples that will be generated
    traj_file   -- name of the file used for trajectories
    """
    dirname = get_path()
    dirname = os.path.join(dirname, "data/reachability")
    directory = os.path.join(dirname, filename)
    filepath = os.path.realpath(directory)
    f = h5py.File(filepath + ".hd5", 'a')

    distance_min = 0
    distance_max = 5
    range_min = 0
    range_max = 100
    n_frames = 10
    frame_interval = 3

    # Trajectories
    dirname = get_path()
    dirname = os.path.join(dirname, "data/trajectories")
    directory = os.path.join(dirname, traj_file)
    filename = os.path.realpath(directory)

    rd = ReachabilityDataset([filename], distance_min, distance_max, range_min, range_max, n_frames, frame_interval)

    env_model = rd.map_names[0]
    print_debug("env_model: ", env_model)
    f.attrs.create('map_type', env_model)

    dtype = np.dtype([
        ('start_observation', (np.int32, 16384)),
        ('goal_observation', (np.int32, 16384 * n_frames)),
        ('reached', np.float32),
        ('start', (np.float32, 2)),  # x, y
        ('goal', (np.float32, 2)),  # x, y
        ('start_orientation', np.float32),  # theta
        ('goal_orientation', np.float32),  # theta
        ('decoded_goal_vector', (np.float32, 2)),  # dx, dy
        ('rotation', np.float32),  # dtheta
        ('start_observation_after_turn', (np.int32, 16384)),
        ('distance', (np.float32, 2))
    ])

    seed = 555556
    rng_sampleid = np.random.RandomState(seed)

    for i in range(nr_samples):
        import time
        start_time = time.time()
        sample_id = rng_sampleid.randint(0xfffffff)
        dset_name = '/%08x' % sample_id

        print('processing sample %d id: %08x' % (i, sample_id))

        if dset_name in f:
            print('dataset %s exists. skipped' % dset_name)
            continue

        random_index = random.randrange(rd.traj_len_cumsum[-1])
        item = rd.__getitem__(random_index)
        if not item:
            raise ValueError("no item found")
        src_img, dst_imgs, r, s, orientations, first_gv, img_after_turn, dist = item

        only_dst_imgs = np.array([x.flatten() for x in dst_imgs])

        sample = (
            src_img[2].flatten(),
            only_dst_imgs.flatten(),
            r,
            s[0],
            s[1],
            orientations[0],
            orientations[1],
            first_gv,
            orientations[1] - orientations[0],
            img_after_turn[2].flatten(),
            dist
        )

        dset = f.create_dataset(
            dset_name,
            data=np.array([sample], dtype=dtype),
            maxshape=(None,), dtype=dtype)

        f.flush()
        print("--- %s seconds --- to create this sample" % (time.time() - start_time))


def display_samples(filename, imageplot=False, startgoalplot=False):
    """ Display information about dataset file
    
    if imageplot: plot the stored images
    if startgoalplot: plot first 5000 start,goal pairs on a map of the environment
    Calculate the percentage of reached/failed samples.
    """

    dirname = get_path()
    directory = os.path.join(dirname, "data/reachability")
    directory = os.path.realpath(directory)
    hf = h5py.File(directory + "/" + filename, 'r')
    env_model = hf.attrs["map_type"]

    print("Number of samples: " + str(len(hf.keys())))

    reach = []
    starts_goals = []
    for key in list(hf.keys()):
        if len(reach) % 50 == 0:
            print("At sample number", len(reach))
        if len(reach) > 5000:
            break
        d = hf[key][()][0]

        if imageplot:
            img = np.reshape(d[0], (64, 64, 4))
            imgplot = plt.imshow(img)
            plt.show()

            dat = np.array_split(d[1], 10)
            for dt in dat:
                img = np.reshape(dt, (64, 64, 4))
                imgplot = plt.imshow(img)
                plt.show()

        starts_goals.append((d[3], d[4]))
        reach.append(d[2])
    print("reached", reach.count(1.0))
    print("failed", reach.count(0.0))
    print("percentage reached/failed", reach.count(1.0) / len(reach))
    plotStartGoalDataset(env_model, starts_goals)


if __name__ == "__main__":
    """ Generate a dataset of reachability samples or load from an existing one.
    
    Testing:
    Generate or load and display a few samples.
    
    Parameterized call:
        Save to/load from filename
        Generate until there are num_samples samples
        Use trajectories from traj_file
        
    Default: time the generation of 50 samples
    """
    test = True
    if test:
        create_and_save_reachability_samples("test10", 10, "test_10.hd5")
        display_samples("test10.hd5")
        # create_and_save_reachability_samples("test2", 1, "test_2.hd5")
        # display_samples("test2.hd5")
        # create_and_save_reachability_samples("test3", 1, "test_3.hd5")
        # display_samples("test3.hd5")
    elif len(sys.argv) == 4:
        _, filename, num_samples, traj_file = sys.argv
        print_debug(sys.argv)
        create_and_save_reachability_samples(filename, int(num_samples), traj_file)
    else:
        import time

        start = time.time()
        create_and_save_reachability_samples("reachability_fifty_sampels", 50, "trajectories_Savinov3.hd5")
        end = time.time()
        print(end - start)
