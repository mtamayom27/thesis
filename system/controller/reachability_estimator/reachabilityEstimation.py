""" This code has been adapted from:
***************************************************************************************
*    Title: "Scaling Local Control to Large Scale Topological Navigation"
*    Author: "Xiangyun Meng, Nathan Ratliff, Yu Xiang and Dieter Fox"
*    Date: 2020
*    Availability: https://github.com/xymeng/rmp_nav
*
***************************************************************************************
"""
import numpy
import torch
import numpy as np
import tabulate

import sys
import os
import system.controller.reachability_estimator.networks as networks
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.bio_model.placecellModel import PlaceCell

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def get_path():
    """ returns path to data storage folder """
    dirname = os.path.dirname(__file__)
    return dirname


def reachability_estimator_factory(type: str = 'distance', **kwargs):
    """ Returns an instance of the reachability estimator interface

    arguments:
    type: str -- type of the reachability estimator, possible values:
                 ['distance' (default), 'neural_network', 'simulation', 'view_overlap']
    kwargs:
        device: str         -- type of the computations, possible values: ['cpu' (default), 'gpu']
        weights_file: str   -- filename of the weights for network-based estimator if exists
        with_spikings: bool -- parameter for network-based estimator, flag to include grid cell spikings into input
        env_model: str      -- model of the environment for simulation-based estimator

    returns:
        ReachabilityEstimator object of the corresponding type
    """
    if type == 'distance':
        return DistanceReachabilityEstimator(kwargs.get('device', 'cpu'), kwargs.get('debug', False))
    elif type == 'neural_network':
        return NetworkReachabilityEstimator(kwargs.get('device', 'cpu'), kwargs.get('debug', False),
                                            kwargs.get('weights_file', None), kwargs.get('with_spikings', False))
    elif type == 'simulation':
        return SimulationReachabilityEstimator(kwargs.get('device', 'cpu'), kwargs.get('debug', False),
                                               kwargs.get('env_model', None))
    elif type == 'view_overlap':
        return ViewOverlapReachabilityEstimator(kwargs.get('device', 'cpu'), kwargs.get('debug', False))
    print("Reachability estimator type not defined: " + type)
    return None


class ReachabilityEstimator:
    def __init__(self, threshold_same: float, threshold_reachable: float, device: str = 'cpu', debug: bool = False):
        """ Abstract base class defining the interface for reachability estimator implementations.

        arguments:
        threshold_same: float      -- threshold for determining when nodes are close enough to be considered same node
        threshold_reachable: float -- threshold for determining when nodes are close enough to be considered reachable
        device                     -- device used for calculations (default cpu)
        debug: bool                -- enables logging
        """
        self.device = device
        self.debug = debug
        self.threshold_same = threshold_same
        self.threshold_reachable = threshold_reachable

    def print_debug(self, *params):
        """ Helper function, outputs only when in debug mode """
        if self.debug:
            print(*params)

    def predict_reachability(self, start: PlaceCell, goal: PlaceCell) -> float:
        """ Abstract function, determines reachability factor between two locations """
        pass

    def get_reachability(self, p: PlaceCell, q: PlaceCell) -> (bool, float):
        """ Determines whether two nodes are reachable based on the reachability threshold

        returns:
        bool  -- flag that indicates that locations are reachable
        float -- reachability probability
        """
        reachability_factor = self.predict_reachability(p, q)
        return self.pass_threshold(reachability_factor, self.threshold_reachable), reachability_factor

    def pass_threshold(self, reachability_factor, threshold) -> bool:
        """ Abstract function, decides if the reachability value passes the threshold """
        pass

    def is_same(self, p: PlaceCell, q: PlaceCell) -> bool:
        """ Determine whether two nodes are close to each other sufficiently to consider them the same node """
        return self.pass_threshold(self.predict_reachability(p, q), self.threshold_same)

    def get_connectivity_probability(self, reachability_factor):
        """ Computes connectivity probability based on reachability factor """
        return reachability_factor


class DistanceReachabilityEstimator(ReachabilityEstimator):
    def __init__(self, device='cpu', debug=False):
        """ Creates a reachability estimator that judges reachability between two locations based on the distance
            
        arguments:
        device -- device used for calculations (default cpu)
        debug  -- is in debug mode
        """
        super().__init__(threshold_same=0.4, threshold_reachable=0.75, device=device, debug=debug)

    def predict_reachability(self, start: PlaceCell, goal: PlaceCell) -> float:
        """ Returns distance between start and goal as an estimation of reachability"""
        return np.linalg.norm(start.env_coordinates - goal.env_coordinates)

    def pass_threshold(self, reachability_factor: float, threshold: float) -> bool:
        """ Two nodes are reachable if the distance is less than the threshold """
        return reachability_factor < threshold


class NetworkReachabilityEstimator(ReachabilityEstimator):
    def __init__(self, device: str = 'cpu', debug: bool = True, weights_file: str = None, with_spikings: bool = False,
                 weights_folder: str = get_path(), backbone: str = 'convolutional', batch_size: int = 64):
        """ Creates a network-based reachability estimator that judges reachability
            between two locations based on observations and grid cell spikings

        arguments:
        device: str         -- device used for calculations (default cpu)
        debug: bool         -- is in debug mode
        weights_file: str   -- file with weights to load the snapshot from
        with_spikings: bool -- flag indicates whether to include grid cell firing to input
        weights_folder: sre -- path to the folder with weights files
        backbone: str       -- variant of the neural network, used when not loading from a snapshot, possible values:
                               ['convolutional' (default), 'resnet', 'siamese']
        batch_size: int     -- size of batches (default 64), used when not loading from a snapshot
        """
        super().__init__(threshold_same=0.933, threshold_reachable=0.4, device=device, debug=debug)

        self.with_spikings = with_spikings
        weights_filepath = os.path.join(weights_folder, weights_file)
        state_dict = torch.load(weights_filepath, map_location='cpu')
        self.print_debug('loaded %s' % weights_file)
        global_args = state_dict.get('global_args', {})
        self.print_debug('global args:')
        self.print_debug(tabulate.tabulate(global_args.items()))

        self.backbone = global_args.get('backbone', backbone)
        self.model_variant = global_args['model_variant']
        self.batch_size = global_args.get('batch_size', batch_size)

        self.nets = networks.initialize_network(self.backbone, self.model_variant)
        self.nets = {name: spec['net'] for name, spec in self.nets.items()}

        self.print_debug(self.nets)

        for name, net in self.nets.items():
            net.load_state_dict(state_dict['nets'][name])
            net.train(False)

    def predict_reachability(self, start: PlaceCell, goal: PlaceCell) -> float:
        """ Predicts reachability value between two locations """
        if self.with_spikings:
            if isinstance(goal.gc_connections, list):
                goal.gc_connections = np.array(goal.gc_connections)
            return self.predict_reachability_batch([start.observations[0]], [goal.observations[-1]],
                                                   [spikings_reshape(start.gc_connections.flatten())],
                                                   [spikings_reshape(np.array(goal.gc_connections).flatten())])[0]
        return self.predict_reachability_batch([start.observations[0]], [goal.observations[-1]])[0]

    def predict_reachability_batch(self, starts: [numpy.ndarray | torch.Tensor], goals: [numpy.ndarray | torch.Tensor],
                                   src_spikings: [numpy.ndarray | torch.Tensor] = None,
                                   goal_spikings: [numpy.ndarray | torch.Tensor] = None) -> [float]:
        """ Predicts reachability for multiple location pairs

        arguments:
        starts: [numpy.ndarray | torch.Tensor]        -- images perceived by the agent on first locations of each pair
        starts: [numpy.ndarray | torch.Tensor]        -- images perceived by the agent on second locations of each pair
        src_spikings: [numpy.ndarray]                 -- grid cell firings corresponding to the first locations
                                                         of each pair, nullable
        goal_spikings: [numpy.ndarray]                -- grid cell firings corresponding to the second locations
                                                         of each pair, nullable
        batch_size: int                               -- length of each input list and of returned list

        returns:
        [float] -- reachability values
        """

        def get_prediction(src_batch: [numpy.ndarray | torch.Tensor], dst_batch: [numpy.ndarray | torch.Tensor],
                           src_spikings: [numpy.ndarray] = None, goal_spikings: [numpy.ndarray] = None) -> [float]:
            """ Helper function, main logic for predicting reachability for multiple location pairs """
            with torch.no_grad():
                if isinstance(src_batch[0], np.ndarray):
                    src_batch = np.array(src_batch)
                    if self.with_spikings:
                        src_spikings = np.array(src_spikings)
                elif isinstance(src_batch[0], torch.Tensor):
                    if not isinstance(src_batch, torch.Tensor):
                        src_batch = torch.stack(src_batch)
                else:
                    raise RuntimeError('Unsupported datatype: %s' % type(src_batch[0]))
                if isinstance(dst_batch[0][0], np.ndarray):
                    dst_batch = np.array(dst_batch)
                    if self.with_spikings:
                        goal_spikings = np.array(goal_spikings)
                elif isinstance(dst_batch[0][0], torch.Tensor):
                    if not isinstance(dst_batch, torch.Tensor):
                        dst_batch = torch.stack(dst_batch)
                else:
                    raise RuntimeError('Unsupported datatype: %s' % type(dst_batch[0]))
                if self.with_spikings:
                    return networks.get_prediction(self.nets, self.backbone, self.model_variant,
                                                   torch.from_numpy(src_batch).float(),
                                                   torch.from_numpy(dst_batch).float(),
                                                   batch_src_spikings=torch.from_numpy(src_spikings).float(),
                                                   batch_dst_spikings=torch.from_numpy(goal_spikings).float())

                return networks.get_prediction(self.nets, self.backbone, self.model_variant,
                                               torch.from_numpy(src_batch).float(),
                                               torch.from_numpy(dst_batch).float())

        assert len(starts) == len(goals)
        n = len(starts)

        results = []
        n_remaining = n
        batch_size = min(self.batch_size, len(starts))
        while n_remaining > 0:
            results.append(get_prediction(starts[n - n_remaining: n - n_remaining + batch_size],
                                          goals[n - n_remaining: n - n_remaining + batch_size],
                                          src_spikings[n - n_remaining: n - n_remaining + batch_size],
                                          goal_spikings[n - n_remaining: n - n_remaining + batch_size])[0])
            n_remaining -= batch_size
        return torch.cat(results, dim=0).data.cpu().numpy()

    def pass_threshold(self, reachability_factor, threshold) -> bool:
        """ Two nodes are reachable if the confidence value of the network is greater than the threshold """
        return reachability_factor > threshold

    def get_connectivity_probability(self, reachability_factor):
        """ Converts output of the network into connectivity factor """
        return min(1.0, max((self.threshold_reachable - reachability_factor * 0.3) / self.threshold_reachable, 0.1))


class SimulationReachabilityEstimator(ReachabilityEstimator):
    def __init__(self, device='cpu', debug=False, env_model=None):
        """ Creates a reachability estimator that judges reachability
            between two locations based success of navigation simulation

        arguments:
        threshold_same: float      -- threshold for determining when nodes are close enough to be considered same node
        threshold_reachable: float -- threshold for determining when nodes are close enough to be considered reachable
        device                     -- device used for calculations (default cpu)
        debug: bool                -- enables logging
        """
        super().__init__(threshold_same=1.0, threshold_reachable=1.0, device=device, debug=debug)
        self.env_model = env_model
        self.fov = 120 * np.pi / 180

    def predict_reachability(self, start: PlaceCell, goal: PlaceCell) -> float:
        """ Determines reachability factor between two locations """
        from system.controller.local_controller.local_navigation import setup_gc_network, vector_navigation

        """ Return reachability estimate from start to goal using the re_type """
        if not self.env_model:
            raise ValueError("missing env_model; needed for simulating reachability")
        """ Simulate movement between start and goal and return whether goal was reached """
        dt = 1e-2

        # initialize grid cell network and create target spiking
        gc_network = setup_gc_network(dt)
        gc_network.set_as_current_state(start.gc_connections)
        target_spiking = goal.gc_connections
        start_pos = start.env_coordinates
        goal_pos = goal.env_coordinates

        model = "combo"

        from system.controller.simulation.pybulletEnv import PybulletEnvironment
        env = PybulletEnvironment(False, dt, self.env_model, "analytical", start=list(start_pos))

        over, _ = vector_navigation(env, list(goal_pos), gc_network, gc_spiking=target_spiking, model=model,
                                    step_limit=750, plot_it=False)

        if over == 1:
            map_layout = MapLayout(self.env_model)

            overlap_ratios = map_layout.view_overlap(env.xy_coordinates[-1], env.orientation_angle[-1],
                                                     goal_pos, env.orientation_angle[-1], self.fov, mode='plane')

            env.end_simulation()
            if overlap_ratios[0] < 0.1 and overlap_ratios[1] < 0.1:
                # Agent is close to the goal, but seperated by a wall.
                return 0.0
            elif np.linalg.norm(goal_pos - env.xy_coordinates[-1]) > 0.7:
                # Agent actually didn't reach the goal and is too far away.
                return 0.0
            else:
                # Agent did actually reach the goal
                return 1.0
        else:
            env.end_simulation()
            return 0.0

    def pass_threshold(self, reachability_factor, threshold) -> bool:
        return reachability_factor >= threshold


class ViewOverlapReachabilityEstimator(ReachabilityEstimator):
    def __init__(self, device='cpu', debug=False):
        """ Creates a reachability estimator that judges reachability
            between two locations based the overlap of their fields of view

        arguments:
        threshold_same: float      -- threshold for determining when nodes are close enough to be considered same node
        threshold_reachable: float -- threshold for determining when nodes are close enough to be considered reachable
        device                     -- device used for calculations (default cpu)
        debug: bool                -- enables logging
        """
        super().__init__(threshold_same=0.4, threshold_reachable=0.3, device=device, debug=debug)
        self.env_model = "Savinov_val3"
        self.fov = 120 * np.pi / 180
        self.distance_threshold = 0.7
        self.map_layout = MapLayout(self.env_model)

    def predict_reachability(self, start: PlaceCell, goal: PlaceCell) -> float:
        """ Reachability Score based on the view overlap of start and goal in the environment """
        # untested and unfinished
        start_pos = start.env_coordinates
        goal_pos = goal.env_coordinates

        heading1 = np.degrees(np.arctan2(goal_pos[0] - start_pos[0], goal_pos[1] - start_pos[1]))

        overlap_ratios = self.map_layout.view_overlap(start_pos, heading1, goal_pos, heading1, self.fov, mode='plane')

        return (overlap_ratios[0] + overlap_ratios[1]) / 2

    def pass_threshold(self, reachability_factor, threshold) -> bool:
        return reachability_factor > threshold


def spikings_reshape(img_array):
    """ Helper function, image stored in array form to image in correct shape for nn """
    img = np.reshape(img_array, (6, 40, 40))
    return img
