import sys
import os

from system.controller.reachability_estimator.reachabilityEstimation import init_reachability_estimator

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from system.bio_model.gridcellModel import GridCellNetwork
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network
from system.bio_model.placecellModel import PlaceCellNetwork
from system.bio_model.cognitivemap import LifelongCognitiveMap, CognitiveMapInterface
import system.plotting.plotResults as plot

plotting = True  # if True: plot paths
debug = True  # if True: print debug output
dt = 1e-2


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


def waypoint_movement(path, env_model: str, gc_network: GridCellNetwork, pc_network: PlaceCellNetwork, cognitive_map: CognitiveMapInterface, mode="combo"):
    """ Agent navigates on path, 
        exploring the environment and building the cognitive map
    
    arguments:
    path        -- initial start position and subgoals on the path
    env_model   -- environment model
    re_type     -- type of reachability used to connect the place cells on the cognitive map    
    """

    # get the path through the environment
    mapLayout = MapLayout(env_model)
    goals = []
    for i in range(len(path) - 1):
        new_wp = mapLayout.find_path(path[i], path[i + 1])
        if new_wp is None:
            raise ValueError("No path found!")
        goals += new_wp
        if plotting:
            mapLayout.draw_map_path(path[i], path[i + 1], i)

    # draw the path
    if plotting:
        mapLayout.draw_path(goals)

    env = PybulletEnvironment(False, dt, env_model, mode, build_data_set=True, start=path[0])

    # The local controller navigates the path analytically and updates the pc_netowrk and the cognitive_map
    for i, goal in enumerate(goals):
        print_debug(f"new waypoint with coordinates {goal}.", f'{i / len(goals) * 100} % completed.')
        vector_navigation(env, goal, gc_network, model=mode, step_limit=5000, obstacles=False,
                          plot_it=plotting, exploration_phase=True, pc_network=pc_network, cognitive_map=cognitive_map)
        if plotting and (i + 1) % 100 == 0:
            cognitive_map.draw()
            plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=False)

    env.end_simulation()
    return pc_network, cognitive_map


def exploration_path(env_model, creation_type, connection_type, re_weights_file, cognitive_map_filename, mode):
    """ Agent follows a hard-coded path to explore
        the environment and build the cognitive map.

        arguments:
        - env_model: environment to be explored
        - creation_type, connection_type, connection: see cognitive map

    """

    if env_model == "Savinov_val3":
        goals = [
            [-2, 0], [-6, -2.5], [-4, 0.5], [-6.5, 0.5], [-7.5, -2.5], [-2, -1.5], [1, -1.5],
            [0.5, 1.5], [2.5, -1.5], [1.5, 0], [5, -1.5], [4.5, -0.5], [-0.5, 0], [-8.5, 3],
            [-8.5, -4], [-7.5, -3.5], [1.5, -3.5], [-6, -2.5]
        ]
    else:
        raise NotImplementedError()

    # explore and generate
    # Setup grid cells, place cells and the cognitive map
    gc_network = setup_gc_network(dt)
    re = init_reachability_estimator(connection_type, weights_file=re_weights_file, env_model=env_model,
                                     debug=debug, with_spikings=True)
    pc_network = PlaceCellNetwork(re_type=creation_type, reach_estimator=re)
    cognitive_map = LifelongCognitiveMap(reachability_estimator=re)

    pc_network, cognitive_map = waypoint_movement(goals, env_model, gc_network, pc_network, cognitive_map, mode=mode)
    # save place cell network and cognitive map
    cognitive_map.postprocess()
    pc_network.save_pc_network()
    cognitive_map.save(filename=cognitive_map_filename)

    # draw the cognitive map
    if plotting:
        cognitive_map.draw()
        env = PybulletEnvironment(False, dt, env_model, build_data_set=True)
        plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=cognitive_map, trajectory=False)


if __name__ == "__main__":
    """ 
    Create a cognitive map by exploring the environment
    Choose creation and connection as is suitable

    See cognitivemap.py for description:
    - creation_re_type: "firing", "neural_network", "distance", "simulation", "view_overlap"
    - connection_re_type: "firing", "neural_network", "distance", "simulation", "view_overlap"
    """

    creation_re_type = "firing"
    connection_re_type = "neural_network"
    re_weights_file = "mse_weights.50"
    cognitive_map_filename = "after_exploration.gpickle"
    mode = "combo"

    exploration_path(env_model="Savinov_val3",
                     creation_type=creation_re_type,
                     connection_type=connection_re_type,
                     re_weights_file=re_weights_file,
                     cognitive_map_filename=cognitive_map_filename,
                     mode=mode)