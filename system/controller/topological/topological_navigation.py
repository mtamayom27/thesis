""" This code has been adapted from:
***************************************************************************************
*    Title: "Neurobiologically Inspired Navigation for Artificial Agents"
*    Author: "Johanna Latzel"
*    Date: 12.03.2024
*    Availability: https://nextcloud.in.tum.de/index.php/s/6wHp327bLZcmXmR
*
***************************************************************************************
"""
import numpy as np

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from system.bio_model.grid_cell_model import GridCellNetwork
from system.controller.local_controller.decoder.phase_offset_detector import PhaseOffsetDetectorNetwork
from system.controller.simulation.pybullet_environment import PybulletEnvironment
from system.bio_model.cognitive_map import LifelongCognitiveMap, CognitiveMapInterface
from system.bio_model.place_cell_model import PlaceCellNetwork, PlaceCell
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network
import system.plotting.plotResults as plot

# if True plot results
plotting = True


class TopologicalNavigation(object):
    def __init__(self, env_model: str, method: str,
                 pc_network: PlaceCellNetwork, cognitive_map: CognitiveMapInterface,
                 gc_network: GridCellNetwork, pod: PhaseOffsetDetectorNetwork):
        """
        Handles interactions between local controller and cognitive_map to navigate the environment.
        Performs topological navigation

        arguments:
        env_model: str -- name of the environment model
        model: str -- type of goal vector calculation, possible values: ['pod', 'linear_lookahead', 'combo']
        pc_network: PlaceCellNetwork -- place cell network
        cognitive_map: CognitiveMapInterface -- cognitive map object
        gc_network: GridCellNetwork -- grid cell network
        pod: PhaseOffsetDetectorNetwork -- phase offset detector object
        """
        self.pc_network = pc_network
        self.cognitive_map = cognitive_map
        self.gc_network = gc_network
        self.env_model = env_model
        self.pod = pod
        self.method = method
        self.path_length_limit = 30  # max number of topological navigation steps
        self.step_limit = 500  # max number of vector navigation steps

    def navigate(self, start_ind: int = None, goal_ind: int = None, cognitive_map_filename: str = None):
        """ Navigates the agent through the environment with topological navigation.

        arguments:
        start_ind: int              -- index of start node in the cognitive map, if None: random is chosen
        goal_ind: int               -- index of goal node in the cognitive map, if None: random is chosen
        cognitive_map_filename: str -- name of file to save the cognitive map to

        returns:
        bool -- whether the goal was reached
        int  -- index of start node
        int  -- index of goal node
        """

        if start_ind is None:
            start = np.random.choice(list(self.cognitive_map.node_network.nodes))
            start_ind = list(self.cognitive_map.node_network).index(start)
        else:
            start = list(self.cognitive_map.node_network.nodes)[start_ind]

        if goal_ind is None:
            goal = None
            while goal is None or goal == start:
                goal = np.random.choice(list(self.cognitive_map.node_network.nodes))
            goal_ind = list(self.cognitive_map.node_network).index(goal)
        else:
            goal = list(self.cognitive_map.node_network.nodes)[goal_ind]

        # Plan a topological path through the environment,
        # if no such path exists choose random start and goal until a path is found
        path = self.cognitive_map.find_path(start, goal)
        if not path:
            j = 0
            while path is None and j < 10:
                node = np.random.choice(list(self.cognitive_map.node_network.nodes))
                path = self.cognitive_map.find_path(node, goal)
                j += 1
            if path is None:
                path = [goal]
            path = [start] + path

        for i, p in enumerate(path):
            print("path_index", i, list(self.cognitive_map.node_network.nodes).index(p))

        src_pos = list(path[0].env_coordinates)

        dt = 1e-2
        env = PybulletEnvironment(False, dt, self.env_model, self.method, build_data_set=True, start=src_pos)

        if plotting:
            plot.plotTrajectoryInEnvironment(env, cognitive_map=self.cognitive_map, path=path)

        self.gc_network.set_as_current_state(path[0].gc_connections)
        last_pc = path[0]
        i = 0
        curr_path_length = 0
        while i + 1 < len(path) and curr_path_length < self.path_length_limit:
            goal_pos = list(path[i + 1].env_coordinates)
            goal_spiking = path[i + 1].gc_connections
            stop, pc = vector_navigation(env, goal_pos, self.gc_network, goal_spiking, model=self.method,
                                         obstacles=True, exploration_phase=False, pc_network=self.pc_network,
                                         pod=self.pod, cognitive_map=self.cognitive_map, plot_it=False,
                                         step_limit=self.step_limit)
            self.cognitive_map.postprocess_vector_navigation(node_p=path[i], node_q=path[i + 1],
                                                             observation_p=last_pc, observation_q=pc, success=stop == 1)

            curr_path_length += 1
            if stop != 1:
                last_pc, new_path = self.locate_node(env, pc, goal)
                if not last_pc:
                    last_pc = path[i]

                # if no path to the goal exists, try to find a random node that has valid path to the goal
                # if none is found, go straight to the goal
                if new_path is None:
                    j = 0
                    while new_path is None and j < 10:
                        node = np.random.choice(list(self.cognitive_map.node_network.nodes))
                        new_path = self.cognitive_map.find_path(node, goal)
                        j += 1
                    if new_path is None:
                        new_path = [path[i]] + [goal]
                    new_path = [path[i]] + new_path

                path[i:] = new_path
            else:
                last_pc = pc
                i += 1
            if i == len(path) - 1:
                break

        if curr_path_length >= self.path_length_limit:
            print("LIMIT WAS REACHED STOPPING HERE")

        if plotting:
            plot.plotTrajectoryInEnvironment(env, goal=False, start=start.env_coordinates, end=goal.env_coordinates)
            plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=self.cognitive_map,
                                             start=path[0].env_coordinates, end=path[-1].env_coordinates)

        self.cognitive_map.postprocess_topological_navigation()
        if cognitive_map_filename is not None:
            self.cognitive_map.save(filename=cognitive_map_filename)
        return curr_path_length < self.path_length_limit, start_ind, goal_ind

    def locate_node(self, env: PybulletEnvironment, pc: PlaceCell, goal: PlaceCell):
        """
        Maps a location of the given place cell to the node in the graph.
        Among multiple close nodes prioritize the one that has a valid path to the goal.

        arguments:
        env: PybulletEnvironment -- current environment of the agent
        pc: PlaceCell            -- a place cell to be located
        goal: PlaceCell          -- goal node

        returns:
        PlaceCell          -- mapped node in the graph or the given place cell if no node was found
        [PlaceCell] | None -- path to the goal if exists
        """
        closest_node = None
        for node in self.cognitive_map.node_network.nodes:
            goal_vector = env.get_goal_vector(self.gc_network, self.pod,
                                              goal=node.env_coordinates)  # recalculate goal_vector
            if env.reached(goal_vector):
                closest_node = node
                new_path = self.cognitive_map.find_path(node, goal)
                if new_path:
                    return node, new_path
        return closest_node or pc, None


if __name__ == "__main__":
    """ 
    Test navigation through the maze.
    The exploration should be completed before running this script. 
    """
    from system.controller.reachability_estimator.reachability_estimation import reachability_estimator_factory

    re_type = "neural_network"
    re_weights_file = "re_mse_weights.50"
    map_file = "after_exploration.gpickle"
    map_file_after_lifelong_learning = "after_lifelong_learning.gpickle"
    with_spikings = True
    env_model = "Savinov_val3"
    model = "combo"

    re = reachability_estimator_factory(re_type, weights_file=re_weights_file, env_model=env_model,
                                        with_spikings=with_spikings)
    pc_network = PlaceCellNetwork(from_data=False, reach_estimator=re)
    cognitive_map = LifelongCognitiveMap(reachability_estimator=re, load_data_from=map_file, debug=True)
    gc_network = setup_gc_network(1e-2)
    pod = PhaseOffsetDetectorNetwork(16, 9, 40)

    tj = TopologicalNavigation(env_model, model, pc_network, cognitive_map, gc_network, pod)

    dt = 1e-2
    env = PybulletEnvironment(False, dt, env_model, "analytical", build_data_set=True)
    plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=tj.cognitive_map, trajectory=False)

    successful = 0
    for navigation_i in range(100):
        success, start, end = tj.navigate(cognitive_map_filename=map_file_after_lifelong_learning)
        if success:
            successful += 1
        tj.cognitive_map.draw()
        print(f"Navigation {navigation_i} finished")
        plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=tj.cognitive_map, trajectory=False)

    print(f"{successful} successful navigations")
    print("Navigation finished")
