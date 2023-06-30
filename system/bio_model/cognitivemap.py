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

from system.utils import shuffled, sample_normal
from placecellModel import PlaceCell
from system.controller.reachability_estimator.reachabilityEstimation import init_reachability_estimator

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))


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


class CognitiveMapInterface:
    def __init__(self, from_data=False, re_type="distance", env_model=None):
        """ Cognitive map representation of the environment.

        arguments:
        from_data   -- if True: load existing cognitive map (default False)
        re_type     -- type of reachability estimator determining whether two nodes are connected
                    see ReachabilityEstimator class for explanation of different types (default distance)
        env_model   -- only needed when the reachability estimation is handled by simulation
        """

        weights_filename = "trained_model_pair_conv.30"
        weights_filepath = os.path.join(get_path_re(), weights_filename)
        self.reach_estimator = init_reachability_estimator(re_type, weights_file=weights_filepath, env_model=env_model,
                                                           debug=debug)
        self.node_network = nx.DiGraph()  # if reachability under threshold no edge
        if from_data:
            self.load_cognitive_map()

    def track_movement(self, pc_firing, created_new_pc, pc):
        pass

    def find_path(self, start, goal):
        """ Return path along nodes from start to goal"""
        # TODO Johanna Future Work: Other path-finding options for weighted connections
        g = self.node_network

        try:
            # return shortest path
            path = nx.shortest_path(g, source=start, target=goal)
        except nx.NetworkXNoPath:
            print("no path")
            return None

        return path

    def add_node_to_map(self, p: PlaceCell):
        """ Add a new node to the cognitive map """
        self.node_network.add_node(p, pos=tuple(p.env_coordinates))

    def add_edge_to_map(self, p, q, w=1, **kwargs):
        """ Add a new weighted edge to the cognitive map """
        self.node_network.add_edge(p, q, weight=w, **kwargs)

    def add_bidirectional_edge_to_map(self, p, q, w=1, **kwargs):
        """ Add 2 new weighted edges to the cognitive map """
        self.node_network.add_edge(p, q, weight=w, **kwargs)
        self.node_network.add_edge(q, p, weight=w, **kwargs)

    def save_cognitive_map(self):
        """ Store the current state of the node_network """

        directory = os.path.join(get_path_top(), "data/cognitive_map")
        if not os.path.exists(directory):
            os.makedirs(directory)

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


class CognitiveMap(CognitiveMapInterface):
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
                        delayed / instant: the connection calculation is delayed until after the agent has explored the maze
                                        or every node is connected to other nodes as soon as it is created
        env_model   -- only needed when the reachability estimation is handled by simulation
        """
        super().__init__(from_data, re_type, env_model)

        self.active_threshold = 0.85

        self.connection = connection

        self.prior_idx_pc_firing = None
        self.mode = mode

        self.radius = 5  # radius in which node connection is calculated

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

                reachable, reachability_factor = self.reach_estimator.get_reachability(p, q)
                if reachable:
                    self.node_network.add_weighted_edges_from([(p, q, reachability_factor)])
                else:
                    self.node_network.remove_edges_from([(p, q, reachability_factor)])

    def _connect_single_node(self, p):
        """ Calculate reachability of node p with other nodes """
        for q in list(self.node_network.nodes):

            if q == p:
                continue

            if self.connection[0] == "radius" and np.linalg.norm(q.env_coordinates - p.env_coordinates) > self.radius:
                # No connection above radius
                continue

            reachable_pq, reachability_factor_pq = self.reach_estimator.get_reachability(p, q)
            reachable_qp, reachability_factor_qp = self.reach_estimator.get_reachability(q, p)

            if reachable_pq:
                self.node_network.add_weighted_edges_from([(p, q, reachability_factor_pq)])
            if reachable_qp:
                self.node_network.add_weighted_edges_from([(q, p, reachability_factor_qp)])

    def add_node_to_map(self, p: PlaceCell):
        super().add_node_to_map(p)

        if self.connection[1] == "instant":
            # Connect the new node to all other nodes in the graph
            print_debug("connecting new node")
            self._connect_single_node(p)
            print_debug("connecting finished")

    def track_movement(self, pc_firing, created_new_pc, pc: PlaceCell):
        """Keeps track of curren/t place cell firing and creation of new place cells"""

        # get the currently active place cell
        idx_pc_active = np.argmax(pc_firing)
        pc_active = np.max(pc_firing)

        # Check if we have entered a new place cell
        if created_new_pc:
            entered_different_pc = True
            self.add_node_to_map(pc)

        elif pc_active > self.active_threshold and self.prior_idx_pc_firing != idx_pc_active:
            entered_different_pc = True
        else:
            entered_different_pc = False

        if entered_different_pc:
            if self.mode == "navigation" and self.prior_idx_pc_firing:
                # If we have entered place cell p after being in place cell q during
                # navigation, q is definitely reachable and the edge gets updated accordingly.
                q = list(self.node_network.nodes)[self.prior_idx_pc_firing]
                pc = list(self.node_network.nodes)[idx_pc_active]
                self.node_network.add_weighted_edges_from([(q, pc, 1)])

            self.prior_idx_pc_firing = idx_pc_active

    def save_cognitive_map(self):
        CognitiveMapInterface.save_cognitive_map(self)
        directory = os.path.join(get_path_top(), "data/cognitive_map")

        if self.connection[1] == "delayed":
            self.update_reachabilities()
            nx.write_gpickle(self.node_network, os.path.join(directory, "cognitive_map.gpickle"))

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

    def postprocess(self):
        self.update_reachabilities()


class LifelongCognitiveMap(CognitiveMapInterface):
    def __init__(self, from_data=False, re_type="distance", env_model=None):
        super().__init__(from_data, re_type, env_model)
        self.trajectory_nodes: [PlaceCell] = []
        self.sigma = 0.015
        self.sigma_squared = self.sigma ** 2
        self.threshold_edge_removal = 0.5
        self.p_s_given_r = 0.55
        self.p_s_given_not_r = 0.15

    def track_movement(self, pc_firing, created_new_pc, pc: PlaceCell):
        """Collects nodes"""

        # Check if we have entered a new place cell
        if created_new_pc:
            self.trajectory_nodes.append(pc)

    def is_connectable(self, p: PlaceCell, q: PlaceCell) -> (bool, float):
        """Check if two waypoints p and q are connectable."""
        return self.reach_estimator.get_reachability(p, q)

    def is_mergeable(self, p: PlaceCell) -> bool:
        """Check if the waypoint p is mergeable with the existing graph"""
        return any(self.reach_estimator.is_same(p, q) for q in self.node_network.nodes)

    def construct_graph(self):
        # TODO: more clever node choosing here
        self.add_node_to_map(self.trajectory_nodes.pop(0))  # Initialize graph with the first element from trajectories

        updated = True
        while updated:
            updated = False
            for candidate in shuffled(self.trajectory_nodes):
                if self.is_mergeable(candidate):
                    self.trajectory_nodes.remove(candidate)
                else:
                    for existing_node in self.node_network.nodes:
                        connectable, weight = self.is_connectable(candidate, existing_node)
                        if connectable:
                            if candidate not in self.node_network.nodes:
                                self.add_node_to_map(candidate)
                                self.trajectory_nodes.remove(candidate)
                            # TODO: in paper here relative form transformation
                            self.add_bidirectional_edge_to_map(candidate, existing_node,
                                                               sample_normal(weight, self.sigma),
                                                               connectivity_probability=1.0, mu=weight,
                                                               sigma=self.sigma)
                            updated = True

    def postprocess(self):
        self.construct_graph()

    def update_edge(self, node_p, node_q, observation_q, observation_p):
        success = self.reach_estimator.get_reachability(observation_q, node_q)[0]
        edge = self.node_network[node_p][node_q]

        # Update connectivity
        p_s_r = self.p_s_given_r
        t = p_s_r * edge['connectivity_probability']
        p_r_s = t / (t + self.p_s_given_not_r * (1 - edge['connectivity_probability']))

        if not success and p_r_s < self.threshold_edge_removal:
            # Prune the edge when p(r_ij^{t+1}|s) < Rp
            self.node_network.remove_edge(node_p, node_q)
            self.node_network.remove_edge(node_q, node_p)
        else:
            edge['connectivity_probability'] = p_r_s

        # Update distance weight
        if success:
            weight = self.reach_estimator.get_reachability(observation_p, node_q)[1]
            sigma_ij_t_squared = edge['sigma'] ** 2
            mu_ij_t = edge['mu']
            edge['mu'] = (self.sigma_squared * mu_ij_t + sigma_ij_t_squared * weight) / (sigma_ij_t_squared + self.sigma_squared)
            edge['sigma'] = np.sqrt(1 / (1 / sigma_ij_t_squared + 1 / self.sigma_squared))
            edge['weight'] = sample_normal(edge['mu'], edge['sigma'])



if __name__ == "__main__":
    """ Load, draw and update the cognitive map """

    # Adjust what sort of RE you want to use for connecting nodes
    connection_re_type = "neural_network"  # "neural_network" #"simulation" #"view_overlap"
    connection = ("radius", "delayed")
    cm = CognitiveMap(from_data=True, re_type=connection_re_type, connection=connection, env_model="Savinov_val3")

    # Update and Save the cognitive map
    cm.postprocess()
    cm.save_cognitive_map()

    # Draw the cognitive map
    cm.draw_cognitive_map()

    testing = True
    if testing:
        """ test the place cell drift of the cognitive map """
        from system.controller.simulation.pybulletEnv import PybulletEnvironment
        from system.bio_model.placecellModel import PlaceCellNetwork, PlaceCell
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