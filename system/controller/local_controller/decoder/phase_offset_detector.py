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

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))


# Phase Offset Detectors based on Edvardsen 2015. For details on the implementation refer to the thesis or paper.
# Used for comparison of different decoders
# Code elements here follow a similar logic like the grid cell model.


def in_d(d):
    eta = 0.25
    lam = 15
    beta = 3 / (lam ** 2)
    # beta = 5 / (lam ** 2)

    weight = eta * (np.exp(-beta * (d ** 2)) - 1)
    return weight


def ex_d(d):
    lam = 15
    beta = 3 / (lam ** 2)
    # beta = 5 / (lam ** 2)

    weight = np.exp(-beta * (d ** 2))
    return weight


def compute_ds(x_pod, x_grid):
    n = int(np.sqrt(len(x_grid)))

    x1 = np.transpose(np.tile(x_pod, (n ** 2, 1)))
    x2 = np.tile(x_grid, (len(x_pod), 1))

    dx1 = np.abs(x2 - x1)
    dx2 = n - dx1
    dx = np.min([dx1, dx2], axis=0)
    return dx


class PhaseOffsetDetectorNetwork:
    def __init__(self, n_theta, n_xy, n):
        self.n_theta = n_theta
        self.n_xy = n_xy
        self.n = n

        self.w_ex_dict = {}

        delta = 7

        angles = np.linspace(0, 2 * np.pi, num=n_theta, endpoint=False)

        grid_pod = np.indices((n_xy, n_xy))
        x_pod = np.concatenate(grid_pod[1]) * int(n / n_xy)
        y_pod = np.concatenate(grid_pod[0]) * int(n / n_xy)

        grid = np.indices((n, n))
        x = np.concatenate(grid[1])
        y = np.concatenate(grid[0])

        dx = compute_ds(x_pod, x)
        dy = compute_ds(y_pod, y)
        d = np.linalg.norm([dx, dy], axis=0)

        self.w_in = in_d(d)

        self.factor = 0.2

        for idx, angle in enumerate(angles):
            grid_pod = np.indices((n_xy, n_xy))
            x_pod = np.concatenate(grid_pod[1]) * int(n / n_xy) + delta * np.cos(angle) * np.ones_like(x_pod)
            y_pod = np.concatenate(grid_pod[0]) * int(n / n_xy) + delta * np.sin(angle) * np.ones_like(y_pod)

            dx = compute_ds(x_pod, x)
            dy = compute_ds(y_pod, y)
            d = np.linalg.norm([dx, dy], axis=0)

            self.w_ex_dict[angle] = ex_d(d)

    def calculate_p(self, s, t):
        p_array = np.empty((self.n_theta, 1))
        for idx, angle in enumerate(self.w_ex_dict):
            p_in = np.multiply(np.tile(s, (int(self.n_xy ** 2), 1)), self.w_in)
            p_ex = np.multiply(np.tile(t, (int(self.n_xy ** 2), 1)), self.w_ex_dict[angle])

            p = np.maximum(0, np.sum(p_in, axis=1) + np.sum(p_ex, axis=1))
            p_m = np.sum(p)
            p_array[idx] = p_m
        return p_array

    def compute_goal_vector(self, gc_modules, virtual=False):
        p_array = np.zeros((self.n_theta, 1))
        for gc in gc_modules:
            t = gc.t if not virtual else gc.s_virtual
            p_array_temp = self.calculate_p(gc.s, t) / gc.gm
            p_array = p_array + p_array_temp

        angles = list(self.w_ex_dict.keys())
        x = np.dot(np.cos(angles), p_array)[0]
        y = np.dot(np.sin(angles), p_array)[0]
        goal_vector = np.array([x, y]) * self.factor

        return goal_vector
