import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..","..",".."))

import networkx as nx

from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network
from system.bio_model.placecellModel import PlaceCellNetwork
from system.bio_model.cognitivemap import CognitiveMap
import system.plotting.plotResults as plot

plotting = False # if True: plot paths
debug = True # if True: print debug output
def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)

def waypoint_movement(path,env_model,creation_type, connection_type, connection):
    """ Agent navigates on path, 
        exploring the environment and building the cognitive map
    
    arguments:
    path        -- initial start position and subgoals on the path
    env_model   -- environment model
    re_type     -- type of reachability used to connect the place cells on the cognitive map    
    """
    
    #get the path through the environment
    savinov = MapLayout(env_model)
    waypoints = []
    for i in range(len(path)-1):
        new_wp = savinov.find_path(path[i],path[i+1])
        if new_wp is None:
            raise ValueError("No path found!")
        waypoints+=new_wp
        if plotting: savinov.draw_map_path(path[i],path[i+1])

    # draw the path
    if plotting: savinov.draw_path(path)
        
    goals = waypoints
    
    env = PybulletEnvironment(False,1e-2,env_model,"analytical",buildDataSet=True,start=path[0])
    
    # Setup grid cells, place cells and the cognitive map
    gc_network = setup_gc_network(1e-2)
    pc_network = PlaceCellNetwork(re_type=creation_type)
    cognitive_map = CognitiveMap(re_type=connection_type,connection=connection,env_model = env_model)
    
    # The local controller navigates the path analytically and updates the pc_netowrk and the cognitive_map
    i=0
    for i,g in enumerate(goals):
        print_debug("new waypoint",g,i/len(goals)*100)
        vector_navigation(env,g,gc_network, model = "analytical", step_limit = 5000,
                                                    plot_it = False,exploration_phase=(pc_network,cognitive_map))
    
    # plot the trajectory
    if plotting: plot.plotTrajectoryInEnvironment(env,pc_network=pc_network)
    env.end_simulation()
    return pc_network,cognitive_map

def exploration_path(env_model,creation_type, connection_type, connection):
    ''' Agent follows a hard-coded path to explore
        the environment and build the cognitive map. 

        arguments:
        - env_model: environment to be explored
        - creation_type, connection_type, connection: see cognitive map
        
    '''
       
    # TODO: Future Work: add exploration patterns for all mazes
    if env_model == "Savinov_val3":
        goals = [
            [-2,0],[-6,-2.5],[-4,0.5],[-6.5,0.5],[-7.5,-2.5],[-2,-1.5],
            [1,-1.5],[0.5,1.5],[2.5,-1.5],[1.5,0],
            [5,-1.5],[4.5,-0.5],[-0.5,0],[-8.5,3],[-8.5,-4],[-7.5,-3.5],[1.5,-3.5]
        ]
        #goals = [[-2,0],[-4,-2.5],[-2,0]]
    elif env_model == "Savinov_val2":
        pass
    elif env_model == "Savinov_test7":
        pass
    
    # explore and generate
    pc_network,cognitive_map = waypoint_movement(goals,env_model,creation_type, connection_type, connection)
    
    # save place cell network and cognitive map
    pc_network.save_pc_network()
    cognitive_map.save_cognitive_map()

    # draw the cognitive map
    if plotting: cognitive_map.draw_cognitive_map()

if __name__ == "__main__":
    """ 
    Create a cognitive map by exploring the environment
    Choose creation and connection as is suitable

    See cognitivemap.py for description:
    - creation_re_type: "firing", "neural_network", "distance", "simulation"
    - connection_re_type: "firing", "neural_network", "distance", "simulation"
    - connection: ("all","instant"), ("radius", "delayed")
    """
    
    creation_re_type = "firing"
    connection_re_type = "simulation"
    connection = ("radius", "delayed")
    
    exploration_path("Savinov_val3",creation_re_type, connection_re_type, connection)