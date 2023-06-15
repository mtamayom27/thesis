import numpy as np

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..",".."))

from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.bio_model.cognitivemap import CognitiveMap
from system.bio_model.placecellModel import PlaceCellNetwork
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network

# if True plot results
plotting = True

class TrajectoryFollower(object):
    
    def __init__(self, env_model,creation_type, connection_type, connection):
        """ Handles interactions between local controller and cognitive_map to navigate the environment.

        arguments:
        creation_type, connection_type, connection - see cognitvemap.py

        """

        # setup place cell network, cognitive map and grid cell network (from data)
        self.pc_network = PlaceCellNetwork(from_data = True, re_type = creation_type)
        self.cognitive_map = CognitiveMap(from_data = True,re_type = connection_type, mode = "navigation", connection = connection,env_model = env_model)
        self.gc_network = setup_gc_network(1e-2)
        self.env_model = env_model
        pass
    
    def navigation(self, start = None , goal = None):
        """ Agent navigates through the environment.

        arguments:
        env_model       - environment to navigate in
        start,goal      - index of start and goal node on the cognitve map
                        if None: random start and goal are chose
        
        """

        # Plan a topological path through the environment,
        # if no such path exists choose random start and goal until a path is found
        path = None 
        while not path:
            if not start:
                start = np.random.choice(list(self.cognitive_map.node_network))
                #print("start_index", list(self.cognitive_map.node_network).index(start))
            else:
                start = list(self.cognitive_map.node_network)[start]
        
            if not goal:
                goal = np.random.choice(list(self.cognitive_map.node_network))
                #print("goal_index", list(self.cognitive_map.node_network).index(goal))
            else:
                goal = list(self.cognitive_map.node_network)[goal]
        
            path = self.cognitive_map.find_path(start, goal)

            if not path:
                print("No path found.")
                start = None
                goal = None
        
        # print the topological path as a series of node indexes
        for i,p in enumerate(path):
            print("path_index", i, list(self.cognitive_map.node_network).index(p))

        # start
        src_pos = list(path[0].env_coordinates)
        
        # environment setup
        dt = 1e-2
        env = PybulletEnvironment(False,dt,self.env_model, "analytical",buildDataSet=True ,start = src_pos)

        # draw path on the cognitive map
        if plotting: self.plot_cognitive_map_path(path,env)
        
        # set current grid cell spikings of the agent
        self.gc_network.set_as_current_state(path[0].gc_connections)
        
        # the local controller navigates from subgoal to subgoal
        # if two consecutive subgoals are missed the navigation is aborted
        flag = False
        for i,p in enumerate(path[:-1]):
            goal_pos = list(path[i+1].env_coordinates)
            goal_spiking = path[i+1].gc_connections
            stop,_ = vector_navigation(env, goal_pos, self.gc_network, goal_spiking, model ="combo", exploration_phase = (self.pc_network,self.cognitive_map),plot_it=False,step_limit=1000)
            if stop == -1:
                if flag:
                    break
                flag = True
        
        # plot the agent's trajectory in the environment
        if plotting:
            import plotting.plotResults as plot
            plot.plotTrajectoryInEnvironment(env,cognitive_map = self.cognitive_map,path=path)

    def plot_cognitive_map_path(self,path,env):
        """ plot the path on the cognitive map """
        import matplotlib.pyplot as plt
        import networkx as nx
        import system.plotting.plotHelper as pH #import add_environment

        plt.figure()
        ax = plt.gca()
        pH.add_environment(ax,env)
        G = self.cognitive_map.node_network
        pos=nx.get_node_attributes(G,'pos')
        nx.draw_networkx_nodes(G,pos,node_color='#0065BD80',node_size=600)
        nx.draw_networkx_edges(G,pos,edge_color='#CCCCC6')

        #draw_path
        path_edges = list(zip(path,path[1:]))
        nx.draw_networkx_nodes(G,pos,nodelist=path,node_color='#E37222',node_size=600)
        G = G.to_undirected()
        nx.draw_networkx_edges(G,pos,edgelist=path_edges,edge_color='#E37222',width=3)
        plt.axis("equal")
        plt.show()
    
if __name__ == "__main__":
    """ Test navigation through the maze """

    # see cognitivemap.py
    creation_re_type = "firing"
    connection_re_type = "simulation"
    connection = ("all", "delayed")
    
    # setup
    tj = TrajectoryFollower("Savinov_val3",creation_re_type, connection_re_type, connection)
    
    # example navigation trials
    #tj.navigation(start=110,goal=108)   # Figure 6.13 (a): success, bad path
    #tj.navigation(start=120,goal=110)   # Figure 6.13 (b): success, not on explore path
    #tj.navigation(start=112,goal=13)    # Figure 6.13 (c): short success

    #tj.navigation(start=23,goal=30)      # Figure 6.14 (a): too imprecise
    #tj.navigation(start=103,goal=30)     # Figure 6.14 (b): too imprecise
    #tj.navigation(start=20,goal=27)      # Figure 6.14 (c): failure, agent too imprecise    

    #tj.navigation(start=122,goal=8)     # Figure 6.16: circles 

    #tj.navigation(start=22,goal=106)    #failure, too imprecise
    #tj.navigation(start=115,goal=30)    #failure, too imprecise 
    #tj.navigation(start=123,goal=127)   #success, very basic example of a shortcut?
    #tj.navigation(start=127,goal=26)    #failure, circle
    #tj.navigation(start=88,goal=73)     #too imprecise
    #tj.navigation(start = 73, goal = 65) #corridor path
    
    tj.navigation()

