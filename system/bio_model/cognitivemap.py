''' This code has been adapted from:
***************************************************************************************
*    Title: "Biologically inspired spatial navigation using vector-based and topology-based path planning"
*    Author: "Tim Engelmann"
*    Date: 28.09.2021
*    Code version: 1.0
*    Availability: https://drive.google.com/file/d/1g7I-n9KVVulybh1YeElSC-fvm9_XDoez/view
*
***************************************************************************************
'''
import networkx as nx
import numpy as np

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from system.controller.reachability_estimator.reachabilityEstimation import init_reachability_estimator


def get_path_re():
    """ returns path to RE model folder """
    dirname = os.path.join(os.path.dirname(__file__), "../controller/reachability_estimator/data/models")
    return dirname


def get_path_top():
    """ returns path to topological data folder """
    dirname = os.path.join(os.path.dirname(__file__))
    return dirname


debug = True  # if True: print debug output


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


class CognitiveMap:
    def __init__(self, from_data=False, re_type="distance", mode="exploration", connection=("all", "delayed"),
                 env_model=None):
        """ Cognitive map representation of the environment. 
        
        arguments:
        from_data   -- if True: load existing cognitive map (default False)
        re_type     -- type of reachability estimator determining whether two nodes are connected
                    see ReachabilityEstimator class for explanation of different types (default distance)
        mode        -- distinguishes between navigation and exploration mode for differences in
                    node connection process (default exploration)
        connection  -- (which nodes, when) Decides when the connection between which nodes is calculated.
                        all / radius: all possible connections are calculated 
                                    or just the connections between two nodes within each others radius are calculated
                        delayed / instant: the connection calculation is dealyed until after the agent has explored the maze
                                        or every node is connected to other nodes as soon as it is created
        env_model   -- only needed when the reachability estimation is handled by simulation
        """

        filename = "trained_model_pair_conv.30"
        filepath = os.path.join(get_path_re(), filename)

        self.reach_estimator = init_reachability_estimator(re_type, weights_file=filepath, env_model=env_model)

        # thresholds for different RE types
        if re_type == "distance":
            self.connection_threshold = 0.75
        elif re_type == "neural_network":
            self.connection_threshold = 0.5
        elif re_type == "simulation":
            self.connection_threshold = 1.0
        if re_type == "view_overlap":
            self.connection_threshold = 0.3

        self.active_threshold = 0.85

        self.connection = connection

        self.node_network = nx.DiGraph()  # if reachability under threshold no edge

        self.prior_idx_pc_firing = None
        self.mode = mode

        self.radius = 5  # radius in which node connection is calculated

        if from_data:
            self.load_cognitive_map()

    def compute_reachability(self, reachability):
        """Determine most reachable place cell"""
        idx_pc_reachable = np.argmax(np.array(reachability))
        reach = np.max(reachability)
        return [reach, idx_pc_reachable]  # Return highest reachability and idx of pc

    def find_path(self, start, goal):
        """ Return path along nodes from start to goal"""
        # Future Work: Other path-finding options for weighted connections
        g = self.node_network

        try:
            # return shortest path
            path = nx.shortest_path(g, source=start, target=goal)
        except nx.NetworkXNoPath:
            print("no path")
            return None

        return path

    def update_reachabilities(self):
        """ Update reachability between the nodes. """
        nr_nodes = len(list(self.node_network.nodes))
        for i, p in enumerate(list(self.node_network.nodes)):
            print_debug("currently updating node " + str(i))
            progress_str = "Progress: " + str(int((i + 1) * 100 / nr_nodes)) + "%"
            print(progress_str)

            for q in list(self.node_network.nodes):

                if q == p:
                    continue

                if self.connection[0] == "radius" and np.linalg.norm(
                        q.env_coordinates - p.env_coordinates) > self.radius:
                    # No connection above radius
                    continue

                rp = self.reach_estimator.predict_reachability(p, q)  # reachability from p to q

                if self.reach_estimator.reachable(rp, self.connection_threshold):
                    self.node_network.add_weighted_edges_from([(p, q, rp)])
                else:
                    self.node_network.remove_edges_from([(p, q, rp)])

    def _connect_single_node(self, p):
        """ Calculate reachability of node p with other nodes """
        for q in list(self.node_network.nodes):

            if q == p:
                continue

            if self.connection[0] == "radius" and np.linalg.norm(q.env_coordinates - p.env_coordinates) > self.radius:
                # No connection above radius
                continue

            rp = self.reach_estimator.predict_reachability(p, q)  # reachability from p to q
            rq = self.reach_estimator.predict_reachability(q, p)  # reachability from q to p

            if self.reach_estimator.reachable(rp, self.connection_threshold):
                self.node_network.add_weighted_edges_from([(p, q, rp)])
            if self.reach_estimator.reachable(rq, self.connection_threshold):
                self.node_network.add_weighted_edges_from([(q, p, rq)])

    def add_node_to_map(self, p):
        """ Add a new node to the cognitive map """
        # add into digraph
        self.node_network.add_node(p, pos=tuple(p.env_coordinates))

        if self.connection[1] == "instant":
            # Connect the new node to all other nodes in the graph
            print_debug("connecting new node")
            self._connect_single_node(p)
            print_debug("connecting finished")

    def track_movement(self, pc_firing, created_new_pc, p):
        """Keeps track of current place cell firing and creation of new place cells"""

        # get the currently active place cell
        idx_pc_active = np.argmax(pc_firing)
        pc_active = np.max(pc_firing)

        # Check if we have entered a new place cell
        if created_new_pc:
            entered_different_pc = True
            self.add_node_to_map(p)

        elif pc_active > self.active_threshold and self.prior_idx_pc_firing != idx_pc_active:
            entered_different_pc = True
        else:
            entered_different_pc = False

        if entered_different_pc:
            if self.mode == "navigation" and self.prior_idx_pc_firing:
                # If we have entered place cell p after being in place cell q during
                # navigation, q is definitely reachable and the edge gets updated accordingly.
                q = list(self.node_network.nodes)[self.prior_idx_pc_firing]
                p = list(self.node_network.nodes)[idx_pc_active]
                self.node_network.add_weighted_edges_from([(q, p, 1)])

            self.prior_idx_pc_firing = idx_pc_active

    def save_cognitive_map(self):
        """ Store the current state of the node_network """

        directory = os.path.join(get_path_top(), "data/cognitive_map")
        if not os.path.exists(directory):
            os.makedirs(directory)

        nx.write_gpickle(self.node_network, os.path.join(directory, "cognitive_map.gpickle"))

        if self.connection[1] == "delayed":
            self.update_reachabilities()
            nx.write_gpickle(self.node_network, os.path.join(directory, "cognitive_map.gpickle"))

    def load_cognitive_map(self):
        """ Load existing cognitive map """
        directory = os.path.join(get_path_top(), "data/cognitive_map")
        if not os.path.exists(directory):
            raise ValueError("cognitive map not found")

        self.node_network = nx.read_gpickle(os.path.join(directory, "cognitive_map.gpickle"))

    def draw_cognitive_map(self):
        """ Plot the cognitive map """
        import matplotlib.pyplot as plt
        G = self.node_network
        pos = nx.get_node_attributes(G, 'pos')

        # Plots the nodes with index labels
        nx.draw(G, pos, labels={i: str(list(G.nodes).index(i)) for i in list(G.nodes)})

        # Plots the graph without labels
        # nx.draw(G,pos,node_color='#0065BD',node_size = 50, edge_color = '#CCCCC6')
        plt.show()

    def test_place_cell_network(self, env, gc_network, from_data=False):
        """ Test the drift error of place cells stored in the cognitive map """
        from system.controller.local_controller.local_navigation import find_new_goal_vector

        G = self.node_network
        delta_avg = 0
        pred_gvs = []  # goal vectors decoded using linear lookahead
        true_gvs = []  # analytically calculated goal vectors
        error = []

        if from_data:
            dirname = os.path.join(os.path.dirname(__file__), "../../experiments/drift_error")

            pred_gvs = np.load(os.path.join(dirname, "pred_gvs.npy"))
            true_gvs = np.load(os.path.join(dirname, "true_gvs.npy"))
            error = true_gvs - pred_gvs
            delta = [np.linalg.norm(i) for i in error]
            delta_avg = np.mean(delta)

        else:
            env.mode = "linear_lookahead"
            # decode goal vectors from current position to every place cell on the cognitive map 
            for i, p in enumerate(list(G.nodes)):
                print("Decoding goal vector to place Cell", i, "out of", len(list(G.nodes)))
                target_spiking = p.gc_connections
                gc_network.set_as_target_state(target_spiking)
                env.goal_pos = p.env_coordinates

                find_new_goal_vector(gc_network, env, env.mode)

                pred_gv = env.goal_vector
                true_gv = env.calculate_goal_vector_analytically()

                error_gv = true_gv - pred_gv
                delta = np.linalg.norm(error_gv)

                delta_avg += delta
                pred_gvs.append(pred_gv)
                true_gvs.append(true_gv)
                error.append(error_gv)

            delta_avg /= len(list(G.nodes))

        print("Average error:", delta_avg)

        # Plot the drift error on the cognitive map
        import matplotlib.pyplot as plt
        import system.plotting.plotHelper as pH

        plt.figure()
        ax = plt.gca()
        pH.add_environment(ax, env)
        pH.add_robot(ax, env)
        pos = nx.get_node_attributes(G, 'pos')
        nx.draw_networkx_nodes(G, pos, node_color='#0065BD80', node_size=3000)

        directory = "experiments/"
        if not os.path.exists(directory):
            os.makedirs(directory)

        directory = "experiments/drift_error"
        if not os.path.exists(directory):
            os.makedirs(directory)

        np.save("experiments/drift_error/pred_gvs", pred_gvs)
        np.save("experiments/drift_error/true_gvs", true_gvs)

        for i, gv in enumerate(pred_gvs):
            # control the amount of goal vectors displayed in the plot
            if i % 2 == 0 or i % 3 == 0 or i % 5 == 0:
                continue
            plt.quiver(env.xy_coordinates[-1][0], env.xy_coordinates[-1][1], gv[0], gv[1], color='grey', angles='xy',
                       scale_units='xy', scale=1, width=0.005)
            plt.quiver(env.xy_coordinates[-1][0] + gv[0], env.xy_coordinates[-1][1] + gv[1], error[i][0], error[i][1],
                       color='red', angles='xy', scale_units='xy', scale=1, width=0.005)

        plt.show()


if __name__ == "__main__":
    """ Load, draw and update the cognitive map """

    # Adjust what sort of RE you want to use for connecting nodes
    connection_re_type = "view_overlap"  # "neural_network" #"simulation" #"view_overlap"
    connection = ("radius", "delayed")
    cm = CognitiveMap(from_data=True, re_type=connection_re_type, connection=connection, env_model="Savinov_val3")

    # Update and Save the cognitive map
    # cm.update_reachabilities()
    # cm.save_cognitive_map()

    # Draw the cognitive map
    cm.draw_cognitive_map()

    testing = True
    if testing:
        """ test the place cell drift of the cognitive map """
        from system.controller.simulation.pybulletEnv import PybulletEnvironment
        from system.bio_model.placecellModel import PlaceCellNetwork
        from system.controller.local_controller.local_navigation import setup_gc_network

        pc_network = PlaceCellNetwork(from_data=True)
        cognitive_map = CognitiveMap(from_data=True)
        gc_network = setup_gc_network(1e-2)

        # environment setup
        dt = 1e-2
        env = PybulletEnvironment(False, dt, "Savinov_val3", "analytical", buildDataSet=True,
                                  start=list(list(cm.node_network)[1].env_coordinates))

        # set current grid cell spikings of the agent
        gc_network.set_as_current_state(list(cognitive_map.node_network)[1].gc_connections)

        cognitive_map.test_place_cell_network(env, gc_network, from_data=True)
