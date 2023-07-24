import numpy as np

import sys
import os
import csv
import json
import networkx as nx

from matplotlib import pyplot as plt, animation

from system.controller.local_controller.decoder.phaseOffsetDetector import PhaseOffsetDetectorNetwork

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.bio_model.cognitivemap import LifelongCognitiveMap
from system.bio_model.placecellModel import PlaceCellNetwork
from system.controller.local_controller.local_navigation import vector_navigation, setup_gc_network, \
    find_new_goal_vector
import system.plotting.plotResults as plot

# if True plot results
plotting = True


def save_graphs_to_csv(graphs, file_path='data/history.csv', edge_attributes=None):
    if edge_attributes is None:
        edge_attributes = ['connectivity_probability', 'weight', 'mu', 'sigma']
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        # Write header row with node indices as column names
        header_row = []
        lens = [len(graph.nodes) for graph in graphs]
        for i in range(max(lens)):
            header_row.append(str(i))
        writer.writerow(header_row)

        # Write data rows for each graph
        for graph in graphs:
            data_row = []
            for node in graph.nodes:
                adjacency_list = []
                for neighbor in graph.neighbors(node):
                    edge_attributes_dict = {}
                    for attr in edge_attributes:
                        edge_attributes_dict['to'] = list(graph.nodes).index(neighbor)
                        if attr in graph.edges[node, neighbor]:
                            edge_attributes_dict[attr] = graph.edges[node, neighbor][attr]
                    adjacency_list.append(edge_attributes_dict)
                data_row.append(json.dumps(adjacency_list))
            writer.writerow(data_row)


def load_graphs_from_csv(file_path='data/history.csv'):
    graphs = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        header_row = next(reader)[1:]  # Exclude the first empty cell

        for row in reader:
            graph = nx.Graph()
            for i, node in enumerate(header_row):
                adjacency_list = json.loads(row[i])
                for neighbor, edge_attributes_dict in zip(header_row, adjacency_list):
                    edge = (node, neighbor)
                    graph.add_edge(*edge, **edge_attributes_dict)
            graphs.append(graph)

    return graphs


def write_kwargs_to_file(file_path='data/history.txt', **kwargs):
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)

    serializable_kwargs = {}
    for key, value in kwargs.items():
        try:
            json.dumps(value)  # Check if value is serializable
            serializable_kwargs[key] = value
        except TypeError:
            serializable_kwargs[key] = str(value)

    with open(file_path, 'w') as file:
        json.dump(serializable_kwargs, file)


class TrajectoryFollower(object):
    def __init__(self, env_model, creation_type, connection_type, connection):
        """ Handles interactions between local controller and cognitive_map to navigate the environment.

        arguments:
        creation_type, connection_type, connection - see cognitvemap.py

        """

        # setup place cell network, cognitive map and grid cell network (from data)
        self.pc_network = PlaceCellNetwork(from_data=True, re_type=creation_type)
        # self.cognitive_map = CognitiveMap(from_data=True, re_type=connection_type, mode="navigation", connection=connection, env_model=env_model)
        self.cognitive_map = LifelongCognitiveMap(from_data=True, re_type=connection_type, env_model=env_model)
        self.gc_network = setup_gc_network(1e-2)
        self.env_model = env_model
        self.pod = PhaseOffsetDetectorNetwork(16, 9, 40)

    def navigation(self, start=None, goal=None):
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
                # print("start_index", list(self.cognitive_map.node_network).index(start))
            else:
                start = list(self.cognitive_map.node_network)[start]

            if not goal:
                goal = np.random.choice(list(self.cognitive_map.node_network))
                # print("goal_index", list(self.cognitive_map.node_network).index(goal))
            else:
                goal = list(self.cognitive_map.node_network)[goal]

            path = self.cognitive_map.find_path(start, goal)

            if not path:
                print("No path found.")
                start = None
                goal = None

        # print the topological path as a series of node indexes
        for i, p in enumerate(path):
            print("path_index", i, list(self.cognitive_map.node_network).index(p))

        # start
        src_pos = list(path[0].env_coordinates)

        # environment setup
        dt = 1e-2
        env = PybulletEnvironment(False, dt, self.env_model, "analytical", build_data_set=True, start=src_pos)

        # draw path on the cognitive map
        if plotting:
            self.plot_cognitive_map_path(path, env)
            graph_states = [nx.DiGraph(self.cognitive_map.node_network)]
            positions = [path[0]]

        # set current grid cell spikings of the agent
        self.gc_network.set_as_current_state(path[0].gc_connections)

        last_pc = path[0]
        i = 0
        while True:
            goal_pos = list(path[i + 1].env_coordinates)
            goal_spiking = path[i + 1].gc_connections
            stop, pc = vector_navigation(env, goal_pos, self.gc_network, goal_spiking, model="combo",
                                         obstacles=True, exploration_phase=False, pc_network=self.pc_network,
                                         pod=self.pod, cognitive_map=self.cognitive_map, plot_it=True, step_limit=1000)
            self.cognitive_map.update_map(node_p=path[i], node_q=path[i + 1], observation_p=last_pc, observation_q=pc, success=stop != -1)
            if plotting:
                graph_states.append(nx.DiGraph(self.cognitive_map.node_network))
                positions.append(pc)

            if stop == -1:
                _, last_pc = self.cognitive_map.locate_node(pc)

                new_path = self.cognitive_map.find_path(last_pc, goal)
                if new_path is None or len(new_path) < 1:
                    print("NO PATH FOUND")
                    break

                path[i:] = new_path
                self.plot_cognitive_map_path(path, env)
            else:
                failed_attempts = 0
                i += 1
                if i == len(path) - 1:
                    break

        # plot the agent's trajectory in the environment
        if plotting:
            plot.plotTrajectoryInEnvironment(env, cognitive_map=self.cognitive_map, path=path)
            fig, ax = plt.subplots()

            def update(frame):
                ax.clear()
                pos = nx.get_node_attributes(graph_states[frame], 'pos')
                nx.draw(graph_states[frame], pos, with_labels=True, node_color='lightblue', edge_color='gray',
                        labels={i: str(list(graph_states[frame].nodes).index(i)) for i in
                                list(graph_states[frame].nodes)}, node_size=60)

            # Create the animation
            ani = animation.FuncAnimation(fig, update, frames=len(graph_states), interval=1000)

            # Show the animation
            plt.show()
            save_graphs_to_csv(graph_states)
            write_kwargs_to_file(path=[waypoint.env_coordinates for waypoint in path], positions=positions)

    def plot_cognitive_map_path(self, path, env):
        """ plot the path on the cognitive map """
        import system.plotting.plotHelper as pH  # import add_environment

        plt.figure()
        ax = plt.gca()
        pH.add_environment(ax, env)
        G = self.cognitive_map.node_network
        pos = nx.get_node_attributes(G, 'pos')
        nx.draw_networkx_nodes(G, pos, node_color='#0065BD80', node_size=60)
        nx.draw_networkx_edges(G, pos, edge_color='#CCCCC6')

        # draw_path
        path_edges = list(zip(path, path[1:]))
        nx.draw_networkx_nodes(G, pos, nodelist=path, node_color='#E3722280', node_size=60)
        G = G.to_undirected()
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='#E3722280', width=3)
        plt.axis("equal")
        plt.show()


if __name__ == "__main__":
    """ Test navigation through the maze """

    # see cognitivemap.py
    creation_re_type = "distance"
    connection_re_type = "distance"
    connection = ("all", "delayed")

    # setup
    tj = TrajectoryFollower("Savinov_val3", creation_re_type, connection_re_type, connection)
    tj.navigation(start=176, goal=180)
    # tj.navigation(start=111, goal=119)
    # tj.navigation(start=67, goal=84)
    # example navigation trials
    # tj.navigation(start=110,goal=108)   # Figure 6.13 (a): success, bad path
    # tj.navigation(start=120,goal=110)   # Figure 6.13 (b): success, not on explore path
    # tj.navigation(start=112,goal=13)    # Figure 6.13 (c): short success

    # tj.navigation(start=23,goal=30)      # Figure 6.14 (a): too imprecise
    # tj.navigation(start=103,goal=30)     # Figure 6.14 (b): too imprecise
    # tj.navigation(start=20,goal=27)      # Figure 6.14 (c): failure, agent too imprecise

    # tj.navigation(start=122,goal=8)     # Figure 6.16: circles

    # tj.navigation(start=22,goal=106)    #failure, too imprecise
    # tj.navigation(start=115,goal=30)    #failure, too imprecise
    # tj.navigation(start=123,goal=127)   #success, very basic example of a shortcut?
    # tj.navigation(start=127,goal=26)    #failure, circle
    # tj.navigation(start=88,goal=73)     #too imprecise
    # tj.navigation(start = 73, goal = 65) #corridor path

    # tj.navigation()
