import random
import numpy as np


def shuffled(T):
    """Shuffle the given array T."""
    random.shuffle(T)
    return T


def sample_bernoulli(p):
    # Sampling from a Bernoulli distribution with probability p
    return np.random.binomial(1, p)


def sample_normal(m, s):
    return np.random.normal(m, s)
