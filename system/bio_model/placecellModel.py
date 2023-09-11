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
import numpy as np
import types

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def get_path_re():
    """ returns path to RE model folder """
    dirname = os.path.join(os.path.dirname(__file__), "../controller/reachability_estimator/data/models")
    return dirname


def get_path_top():
    """ returns path to topological data folder """
    dirname = os.path.join(os.path.dirname(__file__))
    return dirname


class PlaceCell:
    """Class to keep track of an individual Place Cell"""

    def __init__(self, gc_connections, observations, coordinates):
        self.gc_connections = gc_connections  # Connection matrix to grid cells of all modules; has form (n^2 x M)
        self.env_coordinates = coordinates  # Save x and y coordinate at moment of creation

        self.plotted_found = [False, False]  # Was used for debug plotting, of linear lookahead

        self.observations = observations

    def compute_firing(self, s_vectors):
        """Computes firing value based on current grid cell spiking"""
        gc_connections = np.where(self.gc_connections > 0.1, 1, 0)  # determine where connection exist to grid cells
        filtered = np.multiply(gc_connections, s_vectors)  # filter current grid cell spiking, by connections
        modules_firing = np.sum(filtered, axis=1) / np.sum(s_vectors, axis=1)  # for each module determine pc firing
        firing = np.average(modules_firing)  # compute overall pc firing by summing averaging over modules
        return firing

    def compute_firing_2x(self, s_vectors, axis, plot=False):
        """Computes firing projected on one axis, based on current grid cell spiking"""
        new_dim = int(np.sqrt(len(s_vectors[0])))  # n

        s_vectors = np.where(s_vectors > 0.1, 1, 0)  # mute weak grid cell spiking, transform to binary vector
        gc_connections = np.where(self.gc_connections > 0.1, 1, 0)  # mute weak connections, transform to binary vector

        proj_s_vectors = np.empty((len(s_vectors[:, 0]), new_dim))
        for i, s in enumerate(s_vectors):
            s = np.reshape(s, (new_dim, new_dim))  # reshape (n^2 x 1) vector to n x n vector
            proj_s_vectors[i] = np.sum(s, axis=axis)  # sum over column/row

        proj_gc_connections = np.empty_like(proj_s_vectors)
        for i, gc_vector in enumerate(gc_connections):
            gc_vector = np.reshape(gc_vector, (new_dim, new_dim))  # reshape (n^2 x 1) vector to n x n vector
            proj_gc_connections[i] = np.sum(gc_vector, axis=axis)  # sum over column/row

        filtered = np.multiply(proj_gc_connections, proj_s_vectors)  # filter projected firing, by projected connections

        norm = np.sum(np.multiply(proj_s_vectors, proj_s_vectors), axis=1)  # compute unnormed firing at optimal case

        firing = 0
        modules_firing = 0
        for idx, filtered_vector in enumerate(filtered):
            # We have to distinguish between modules tuned for x direction and modules tuned for y direction
            if np.amin(filtered_vector) == 0:
                # If tuned for right direction there will be clearly distinguishable spikes
                firing = firing + np.sum(filtered_vector) / norm[idx]  # normalize firing and add to firing
                modules_firing = modules_firing + 1

        firing = firing / modules_firing  # divide by modules that we considered to get overall firing

        # # Plotting options, used for linear lookahead debugging
        # if plot:
        #     for idx, s_vector in enumerate(s_vectors):
        #         plot_vectors(s_vectors[idx], gc_connections[idx], axis=axis, i=idx)
        #     plot_linear_lookahead_function(proj_gc_connections, proj_s_vectors, filtered, axis=axis)

        # if firing > 0.97 and not self.plotted_found[axis]:
        #     for idx, s_vector in enumerate(s_vectors):
        #         plot_vectors(s_vectors[idx], gc_connections[idx], axis=axis, i=idx, found=True)
        #     plot_linear_lookahead_function(proj_gc_connections, proj_s_vectors, filtered, axis=axis, found=True)
        #     self.plotted_found[axis] = True

        return firing


def compute_weights(s_vectors):
    # weights = np.where(s_vectors > 0.1, 1, 0)
    weights = np.array(s_vectors)  # decided to not change anything here, but do it when computing firing

    return weights


class PlaceCellNetwork:
    """A PlaceCellNetwork holds information about all Place Cells"""

    def __init__(self, from_data=False, re_type="distance", weights_file=None):
        """ Place Cell Network  of the environment. 
        
        arguments:
        from_data   -- if True: load existing place cells (default False)
        re_type     -- type of reachability estimator determining whether a new node gets created
                    see ReachabilityEstimator class for explanation of different types (default distance)
                    plus additional type "firing" that uses place cell spikings
        """
        from system.controller.reachability_estimator.reachabilityEstimation import init_reachability_estimator

        self.re_type = re_type
        filepath = os.path.join(get_path_re(), weights_file)

        if not self.re_type == "firing":
            self.reach_estimator = init_reachability_estimator(re_type, weights_file=filepath)

        # thresholds for place cell creation
        if self.re_type == "distance":
            self.creation_threshold = 0.5
        elif self.re_type == "neural_network":
            self.creation_threshold = 0.6
        elif self.re_type == "simulation":
            self.creation_threshold = 1.0
        elif self.re_type == "firing":
            self.creation_threshold = 0.93
        elif self.re_type == "view_overlap":
            self.creation_threshold = 0.4

        self.place_cells = []  # array of place cells

        if from_data:
            # Load place cells if wanted
            directory = os.path.join(get_path_top(), "data/pc_model")

            gc_connections = np.load(directory + "/gc_connections.npy")
            env_coordinates = np.load(directory + "/env_coordinates.npy")
            observations = np.load(directory + "/observations.npy", allow_pickle=True)

            for idx, gc_connection in enumerate(gc_connections):
                pc = PlaceCell(gc_connection, observations[idx], env_coordinates[idx])
                self.place_cells.append(pc)

    def create_new_pc(self, gc_modules, obs, coordinates):
        # Consolidate grid cell spiking vectors to matrix of size n^2 x M
        s_vectors = np.empty((len(gc_modules), len(gc_modules[0].s)))
        for m, gc in enumerate(gc_modules):
            s_vectors[m] = gc.s
        weights = compute_weights(s_vectors)
        pc = PlaceCell(weights, obs, coordinates)
        self.place_cells.append(pc)

    def in_range(self, reach):
        """ Determine whether one value meets the threshold """
        if self.re_type == "distance":
            r = np.min(reach)
            return r < self.creation_threshold
        elif self.re_type == "neural_network":
            r = np.max(reach)
            return r > self.creation_threshold
        elif self.re_type == "simulation":
            r = np.max(reach)
            return r >= self.creation_threshold
        elif self.re_type == "firing":
            r = np.max(reach)
            return r > self.creation_threshold
        elif self.re_type == "view_overlap":
            r = np.max(reach)
            return r > self.creation_threshold

    def track_movement(self, gc_modules, observations, coordinates):
        """Keeps track of current grid cell firing"""

        firing_values = self.compute_firing_values(gc_modules)

        if self.re_type == "firing":
            firing = firing_values
        else:
            firing = self.compute_reachability_values(coordinates, observations)

        created_new_pc = False
        if len(firing_values) == 0 or not self.in_range(firing):
            self.create_new_pc(gc_modules, observations, coordinates)
            firing_values.append(1)
            created_new_pc = True

        return [firing_values, created_new_pc]

    def compute_firing_values(self, gc_modules, virtual=False, axis=None, plot=False):

        s_vectors = np.empty((len(gc_modules), len(gc_modules[0].s)))
        # Consolidate grid cell spiking vectors that we want to consider
        for m, gc in enumerate(gc_modules):
            if virtual:
                s_vectors[m] = gc.s_virtual
            else:
                s_vectors[m] = gc.s

        firing_values = []
        for i, pc in enumerate(self.place_cells):
            if axis is not None:
                plot = plot if i == 0 else False  # linear lookahead debugging plotting
                firing = pc.compute_firing_2x(s_vectors, axis, plot=plot)  # firing along axis
            else:
                firing = pc.compute_firing(s_vectors)  # overall firing
            firing_values.append(firing)
        return firing_values

    def compute_reachability_values(self, coordinates, observations):
        """ Compute reachability values from all cells to current state, breaks when reachable """
        firing_values = []
        goal = types.SimpleNamespace()
        goal.env_coordinates = coordinates
        goal.observations = observations
        for pc in self.place_cells:
            # compute reachability value from all place cells to the goal
            firing = self.reach_estimator.predict_reachability(pc, goal)
            firing_values.append(firing)

            # if one place cell is still in range we do not need to compute the rest
            if self.in_range([firing]):
                break

        return firing_values

    def save_pc_network(self, filename=""):
        """ Save current place cell network """
        gc_connections = []
        env_coordinates = []
        observations = []
        for pc in self.place_cells:
            gc_connections.append(pc.gc_connections)
            env_coordinates.append(pc.env_coordinates)
            observations.append(pc.observations)

        directory = os.path.join(get_path_top(), "data/pc_model")
        if not os.path.exists(directory):
            os.makedirs(directory)

        np.save(os.path.join(directory, "gc_connections" + filename + ".npy"), gc_connections)
        np.save(os.path.join(directory, "env_coordinates" + filename + ".npy"), env_coordinates)
        np.save(os.path.join(directory, "observations" + filename + ".npy"), observations)
