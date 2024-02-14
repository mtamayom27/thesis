import numpy as np

import sys
import os
import csv
import json
import networkx as nx

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
    def __init__(self, env_model, creation_type, connection_type, weights_file=None, with_spikings=False, map_file="tmp_graph_building.gpickle"):
        """ Handles interactions between local controller and cognitive_map to navigate the environment.

        arguments:
        creation_type, connection_type, connection - see cognitvemap.py

        """

        # setup place cell network, cognitive map and grid cell network (from data)
        self.pc_network = PlaceCellNetwork(from_data=True, re_type=creation_type, weights_file=weights_file)

        # self.cognitive_map = CognitiveMap(from_data=True, re_type=connection_type, mode="navigation", connection=connection, env_model=env_model)
        self.cognitive_map = LifelongCognitiveMap(from_data=True, re_type=connection_type, env_model=env_model, weights_file=weights_file, with_spikings=with_spikings, map_filename=map_file)
        self.gc_network = setup_gc_network(1e-2)
        self.env_model = env_model
        self.pod = PhaseOffsetDetectorNetwork(16, 9, 40)

    
    def navigation(self, method="combo", start=None, goal=None):
        """ Agent navigates through the environment.

        arguments:
        env_model       - environment to navigate in
        start,goal      - index of start and goal node on the cognitve map
                        if None: random start and goal are chose
        
        """
        # [list(self.cognitive_map.node_network.nodes).index(x) for x in
        #  self.cognitive_map.node_network[list(self.cognitive_map.node_network.nodes)[start]]]
        #
        # [[list(self.cognitive_map.node_network.nodes).index(y) for y in x] for x in
        #  nx.shortest_path(self.cognitive_map.node_network, list(self.cognitive_map.node_network.nodes)[0]).values()]


        # Plan a topological path through the environment,
        # if no such path exists choose random start and goal until a path is found
        start_ind = start
        if start is None:
            start = np.random.choice(list(self.cognitive_map.node_network.nodes))
            start_ind = list(self.cognitive_map.node_network).index(start)
            # print("start_index", list(self.cognitive_map.node_network).index(start))
        else:
            start = list(self.cognitive_map.node_network.nodes)[start]

        goal_ind = goal
        if goal is None:
            while not goal or goal == start:
                goal = np.random.choice(list(self.cognitive_map.node_network.nodes))
            goal_ind = list(self.cognitive_map.node_network).index(goal)
            # print("goal_index", list(self.cognitive_map.node_network).index(goal))
        else:
            goal = list(self.cognitive_map.node_network.nodes)[goal]

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

        # print the topological path as a series of node indexes
        for i, p in enumerate(path):
            print("path_index", i, list(self.cognitive_map.node_network.nodes).index(p))

        # start
        src_pos = list(path[0].env_coordinates)

        # environment setup
        dt = 1e-2
        env = PybulletEnvironment(False, dt, self.env_model, "analytical", build_data_set=True, start=src_pos)

        # draw path on the cognitive map
        if plotting:
            plot.plotTrajectoryInEnvironment(env, cognitive_map=self.cognitive_map, path=path)
        # set current grid cell spikings of the agent
        self.gc_network.set_as_current_state(path[0].gc_connections)
        original_path = list(path)
        last_pc = path[0]
        i = 0
        self.cognitive_map.prior_idx_pc_firing = None
        path_length = 0
        path_length_limit = 30
        while i + 1 < len(path) and path_length < path_length_limit:
            goal_pos = list(path[i + 1].env_coordinates)
            goal_spiking = path[i + 1].gc_connections
            stop, pc = vector_navigation(env, goal_pos, self.gc_network, goal_spiking, model=method,
                                         obstacles=True, exploration_phase=False, pc_network=self.pc_network,
                                         pod=self.pod, cognitive_map=self.cognitive_map, plot_it=False, step_limit=500)
            # stop, pc = vector_navigation(env, goal_pos, self.gc_network, goal_spiking, model="analytical",
            #                              obstacles=True, exploration_phase=False, pc_network=self.pc_network,
            #                              pod=self.pod, cognitive_map=self.cognitive_map, plot_it=False, step_limit=100)

            self.cognitive_map.update_map(node_p=path[i], node_q=path[i + 1], observation_p=last_pc, observation_q=pc, success=stop == 1, env=env)

            path_length += 1
            if stop != 1:
                last_pc, new_path = self.locate_node(env, pc, goal, self.gc_network, self.pod)
                if not last_pc:
                    last_pc = path[i]

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
                # plot_cognitive_map_path(self.cognitive_map.node_network, path, env)
            else:
                last_pc = pc
                i += 1
            if i == len(path) - 1:
                break
            if path_length % 200 == 0 and plotting:
                plot.plotTrajectoryInEnvironment(env)

        self.cognitive_map.postprocess()
        if path_length >= path_length_limit:
            print("LIMIT WAS REACHED STOPPING HERE")

        # plot the agent's trajectory in the environment
        if plotting:
            plot.plotTrajectoryInEnvironment(env, goal=False, start=start.env_coordinates, end=goal.env_coordinates)
            plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=self.cognitive_map, start=path[0].env_coordinates, end=path[-1].env_coordinates)

            # fig, ax = plt.subplots()

            # def update(frame):
            #     ax.clear()
            #     pos = nx.get_node_attributes(graph_states[frame], 'pos')
            #     nx.draw(graph_states[frame], pos, with_labels=True, node_color='lightblue', edge_color='gray',
            #             labels={i: str(list(graph_states[frame].nodes).index(i)) for i in
            #                     list(graph_states[frame].nodes)}, node_size=60)

            # Create the animation
            # ani = animation.FuncAnimation(fig, update, frames=len(graph_states), interval=1000)

            # Show the animation
            # plt.show()
            # save_graphs_to_csv(graph_states)
            # write_kwargs_to_file(path=[waypoint.env_coordinates for waypoint in path], positions=positions)
        return path_length < path_length_limit, start_ind, goal_ind

    def locate_node(self, env, pc, goal, gc_network=None, pod_network=None):
        new_node = True
        close_node = None
        for node in self.cognitive_map.node_network.nodes:
            goal_vector = env.get_goal_vector(gc_network, pod_network, goal=node.env_coordinates)  # recalculate goal_vector
            if env.reached(goal_vector):
                close_node = node
                new_node = False
                new_path = self.cognitive_map.find_path(node, goal)
                if new_path:
                    return node, new_path
        # if not new_node:
        #     return pc, None
        #
        # self.cognitive_map.add_node_to_network(pc)
        # new_path = self.cognitive_map.find_path(pc, goal)
        # return pc, new_path
        return close_node or pc, None


if __name__ == "__main__":
    """ Test navigation through the maze """

    # see cognitivemap.py
    creation_re_type = "firing"
    connection_re_type = "neural_network"
    weights_file = "no_siamese_mse.50"
    # map_file="cognitive_map_partial_0.gpickle"
    # map_file="best_graph_ever.gpickle"
    map_file="final_sparse_explo_combo_0.gpickle"
    # map_file="bio_inspired_new_3.gpickle"
    # map_file = "new_area_explo_4.gpickle"
    # map_file="new_area_bio_inspired_0.gpickle"
    # map_file = "best_old_area_bio_1.gpickle"
    # setup

    tj = TrajectoryFollower("Savinov_val3", creation_re_type, connection_re_type, weights_file, with_spikings=True, map_file=map_file)

    dt = 1e-2
    env = PybulletEnvironment(False, dt, "Savinov_val3", "analytical", build_data_set=True)
    # plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=tj.cognitive_map, trajectory=False)
    #
    # G = tj.cognitive_map.node_network.copy()
    successful = 0
    for navigation_i in range(100):
        success, start, end = tj.navigation(method="combo")
        if success:
            successful += 1
        tj.cognitive_map.draw()
        tj.cognitive_map.save(filename="best_old_area_bio_new.gpickle")
        print(f"Navigation {navigation_i} finished")
        plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=tj.cognitive_map, trajectory=False)

    print(f"{successful} successful navigations")
    # plot.plotTrajectoryInEnvironment(env, goal=False, cognitive_map=tj.cognitive_map, trajectory=False)

    print("Navigation finished")

