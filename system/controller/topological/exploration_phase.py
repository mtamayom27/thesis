""" This code has been adapted from:
***************************************************************************************
*    Title: "Neurobiologically Inspired Navigation for Artificial Agents"
*    Author: "Johanna Latzel"
*    Date: 12.03.2024
*    Availability: https://nextcloud.in.tum.de/index.php/s/6wHp327bLZcmXmR
*
***************************************************************************************
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from system.bio_model.grid_cell_model import GridCellNetwork
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.pybullet_environment import PybulletEnvironment
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network
from system.bio_model.place_cell_model import PlaceCellNetwork, PlaceCell
from system.bio_model.cognitive_map import LifelongCognitiveMap, CognitiveMapInterface
import system.plotting.plotResults as plot

plotting = True  # if True: plot paths
debug = True  # if True: print debug output
dt = 1e-2


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


def waypoint_movement(path: [PlaceCell], env_model: str, gc_network: GridCellNetwork, pc_network: PlaceCellNetwork,
                      cognitive_map: CognitiveMapInterface):
    """ Navigates the agent on the given path and builds the cognitive map.
        The local controller navigates the path analytically and updates the pc_network and the cognitive_map.
    
    arguments:
    path: [PlaceCell]                    -- path to follow
    env_model: str                       -- environment model
    gc_network: GridCellNetwork          -- grid cell network
    pc_network: PlaceCellNetwork         -- place cell network
    cognitive_map: CognitiveMapInterface -- cognitive map object
    mode: str                            -- mode goal vector detection, possible values:
                                            ['pod', 'linear_lookahead', 'combo']
    """

    map_layout = MapLayout(env_model)
    goals = []
    for i in range(len(path) - 1):
        new_wp = map_layout.find_path(path[i], path[i + 1])
        if new_wp is None:
            raise ValueError("No path found!")
        goals += new_wp
        if plotting:
            map_layout.draw_map_path(path[i], path[i + 1], i)

    if plotting:
        map_layout.draw_path(goals)

    env = PybulletEnvironment(False, dt, env_model, "analytical", build_data_set=True, start=path[0])

    for i, goal in enumerate(goals):
        print_debug(f"new waypoint with coordinates {goal}.", f'{i / len(goals) * 100} % completed.')
        vector_navigation(env, goal, gc_network, model="analytical", step_limit=5000, obstacles=False,
                          plot_it=plotting, exploration_phase=True, pc_network=pc_network, cognitive_map=cognitive_map)
        if plotting and (i + 1) % 100 == 0:
            cognitive_map.draw()
            plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=False)

    env.end_simulation()
    if plotting:
        cognitive_map.draw()
        plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=True)
    return pc_network, cognitive_map


if __name__ == "__main__":
    """ 
    Create a cognitive map by exploring the environment. 
    Agent follows a hard-coded path to explore the environment and build the cognitive map. 
    """
    from system.controller.reachability_estimator.reachability_estimation import reachability_estimator_factory    

    re_type = "simulation"
    re_weights_file = "re_mse_weights.50"
    cognitive_map_filename = "after_exploration1.gpickle"
    env_model = "Savinov_val3"  # only one currently supported

    goals = [
        [-2, 0], [-6, -2.5], [-4, 0.5], [-6.5, 0.5], [-7.5, -2.5], [-2, -1.5], [1, -1.5],
        [0.5, 1.5], [2.5, -1.5], [1.5, 0], [5, -1.5], [4.5, -0.5], [-0.5, 0], [-8.5, 3],
        [-8.5, -4], [-7.5, -3.5], [1.5, -3.5], [-6, -2.5]
    ]

    gc_network = setup_gc_network(dt)
    re = reachability_estimator_factory(re_type, weights_file=re_weights_file, env_model=env_model,
                                        debug=debug, with_spikings=True)
    pc_network = PlaceCellNetwork(reach_estimator=re)
    cognitive_map = LifelongCognitiveMap(reachability_estimator=re)

    pc_network, cognitive_map = waypoint_movement(goals, env_model, gc_network, pc_network, cognitive_map)
    cognitive_map.postprocess_topological_navigation()

    pc_network.save_pc_network()
    cognitive_map.save(filename=cognitive_map_filename)

    plotting = False
    if plotting:
        cognitive_map.draw()
        env = PybulletEnvironment(False, dt, env_model, build_data_set=True)
        plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=False)
