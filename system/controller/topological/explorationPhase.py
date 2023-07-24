import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from system.bio_model.gridcellModel import GridCellNetwork
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network
from system.bio_model.placecellModel import PlaceCellNetwork
from system.bio_model.cognitivemap import LifelongCognitiveMap, CognitiveMapInterface

plotting = True  # if True: plot paths
debug = True  # if True: print debug output


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


def waypoint_movement(path, env_model: str, gc_network: GridCellNetwork, pc_network: PlaceCellNetwork, cognitive_map: CognitiveMapInterface):
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
            mapLayout.draw_map_path(path[i], path[i + 1])

    # draw the path
    if plotting:
        mapLayout.draw_path(goals)

    env = PybulletEnvironment(False, 1e-2, env_model, "analytical", build_data_set=True, start=path[0])

    # The local controller navigates the path analytically and updates the pc_netowrk and the cognitive_map
    for i, goal in enumerate(goals):
        print_debug(f"new waypoint with coordinates {goal}.", f'{i / len(goals) * 100} % completed.')
        vector_navigation(env, goal, gc_network, model="analytical", step_limit=5000, obstacles=False,
                          plot_it=False, exploration_phase=True, pc_network=pc_network, cognitive_map=cognitive_map)

    # plot the trajectory
    # if plotting:
    #     plot.plotTrajectoryInEnvironment(env, pc_network=pc_network)
    env.end_simulation()
    cognitive_map.postprocess()
    return pc_network, cognitive_map


def exploration_path(env_model, creation_type, connection_type, connection):
    """ Agent follows a hard-coded path to explore
        the environment and build the cognitive map.

        arguments:
        - env_model: environment to be explored
        - creation_type, connection_type, connection: see cognitive map

    """

    # TODO Johanna: Future Work: add exploration patterns for all mazes
    if env_model == "Savinov_val3":
        goals = [
            [-2, 0], [-6, -2.5], [-4, 0.5], [-6.5, 0.5], [-7.5, -2.5], [-2, -1.5],
            [1, -1.5], [0.5, 1.5], [2.5, -1.5], [1.5, 0],
            [5, -1.5], [4.5, -0.5], [-0.5, 0], [-8.5, 3], [-8.5, -4], [-7.5, -3.5], [1.5, -3.5]
        ]
        # goals = [[2.5, 3.3], [1, -1.5]]

    elif env_model == "Savinov_val2":
        pass
    elif env_model == "Savinov_test7":
        pass

    # explore and generate
    # Setup grid cells, place cells and the cognitive map
    gc_network = setup_gc_network(1e-2)
    pc_network = PlaceCellNetwork(re_type=creation_type)
    # TODO: add setting
    # cognitive_map = CognitiveMap(re_type=connection_type, connection=connection, env_model=env_model)
    cognitive_map = LifelongCognitiveMap(re_type=connection_type, env_model=env_model)

    pc_network, cognitive_map = waypoint_movement(goals, env_model, gc_network, pc_network, cognitive_map)

    # save place cell network and cognitive map
    pc_network.save_pc_network()
    cognitive_map.save()

    # draw the cognitive map
    if plotting:
        cognitive_map.draw()


if __name__ == "__main__":
    """ 
    Create a cognitive map by exploring the environment
    Choose creation and connection as is suitable

    See cognitivemap.py for description:
    - creation_re_type: "firing", "neural_network", "distance", "simulation", "view_overlap"
    - connection_re_type: "firing", "neural_network", "distance", "simulation", "view_overlap"
    - connection: ("all","instant"), ("radius", "delayed")
    """

    creation_re_type = "distance"
    connection_re_type = "distance"
    connection = ("radius", "delayed")

    exploration_path("Savinov_val3", creation_re_type, connection_re_type, connection)
