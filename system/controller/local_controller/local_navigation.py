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

import os
import sys

from system.bio_model.cognitivemap import CognitiveMapInterface
from system.bio_model.placecellModel import PlaceCellNetwork, PlaceCell

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from system.controller.local_controller.decoder.linearLookaheadNoRewards import *
from system.controller.local_controller.decoder.phaseOffsetDetector import PhaseOffsetDetectorNetwork
from system.bio_model.gridcellModel import GridCellNetwork

import system.plotting.plotResults as plot
import numpy as np

plotting = True  # if True: plot everything
debug = True  # if True: print debug output


def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)


update_fraction = 0.5  # how often the goal vector is recalculated


def compute_navigation_goal_vector(gc_network, nr_steps, env, model="pod", pod=None):
    """Computes the goal vector for the agent to travel to"""
    distance_to_goal = np.linalg.norm(env.goal_vector)  # current length of goal vector
    distance_to_goal_original = np.linalg.norm(env.goal_vector_original)  # length of goal vector at calculation

    if (
            distance_to_goal_original > 0.3 and distance_to_goal / distance_to_goal_original < update_fraction) or nr_steps == 0:
        # Vector-based navigation and agent has traversed a large portion of the goal vector, it is recalculated
        # or it is the first calculation
        find_new_goal_vector(gc_network, env, model, pod=pod)

        # future work: adding a turn here could make the local controller more robust
        # env.turn_to_goal()
    else:
        env.goal_vector = env.goal_vector - np.array(env.xy_speeds[-1]) * env.dt

    return env.goal_vector


def find_new_goal_vector(gc_network, env, model, pod=None):
    """For Vector-based navigation, computes goal vector with one grid cell decoder"""

    if model == "pod":
        env.goal_vector = pod.compute_goal_vector(gc_network.gc_modules)
    elif model == "linear_lookahead":
        env.goal_vector = perform_look_ahead_2xnr(gc_network, env)
    env.goal_vector_original = env.goal_vector


def create_gc_spiking(start, goal):
    """ 
    Agent navigates from start to goal accross a plane without any obstacles, using the analyticallly 
    calculated goal vector to genereate the grid cell spikings necessary for the decoders. During actual
    navigation this would have happened in the exploration phase.
    """

    dt = 1e-2
    from system.controller.simulation.pybulletEnv import PybulletEnvironment
    env = PybulletEnvironment(False, dt, "plane", mode="analytical", start=list(start))
    env.goal_pos = goal

    # Grid-Cell Initialization
    gc_network = setup_gc_network(env.dt)

    env.turn_to_goal()

    i = 0
    while i < 5000:
        i += 1
        if i == 5000:
            raise ValueError("Agent should not get caught in a loop in an empty plane.")
        env.navigation_step(gc_network, obstacles=False)
        status = env.get_status()
        if status == -1:
            raise ValueError("Agent should not get stuck in an empty plane.")
        elif status == 1:
            if plotting: plot.plotTrajectoryInEnvironment(env)
            env.end_simulation()
            return gc_network.consolidate_gc_spiking()


def setup_gc_network(dt):
    """ Initialize the grid cell newtork """
    # Grid-Cell Initialization
    M = 6  # 6 for default, number of modules
    n = 40  # 40 for default, size of sheet -> nr of neurons is squared
    gmin = 0.2  # 0.2 for default, maximum arena size, 0.5 -> ~10m | 0.05 -> ~105m
    gmax = 2.4  # 2.4 for default, determines resolution, dont pick to high (>2.4 at speed = 0.5m/s)

    # note that if gc modules are created from data n and M are overwritten
    gc_network = GridCellNetwork(n, M, dt, gmin, gmax=gmax, from_data=True)

    return gc_network


def get_observations(env):
    # TODO Johanna: parameterize context length and delta T
    # observations with context length k=10 and delta T = 3
    observations = env.images[::3][-10:]
    # reformat observation images
    # TODO Johanna: Future work: This assumes context length k=10, delta T = 3, outsource into helper function
    if len(observations) < 10:
        observations += [observations[-1]] * (10 - len(observations))
    return [np.transpose(observation[2], (2, 0, 1))[:3] for observation in observations]


def vector_navigation(env, goal, gc_network, gc_spiking=None, model="combo",
                      step_limit=float('inf'), plot_it=False, obstacles=True, pod=PhaseOffsetDetectorNetwork(16, 9, 40),
                      collect_data_traj=False, exploration_phase=False,
                      pc_network: PlaceCellNetwork = None, cognitive_map: CognitiveMapInterface = None):
    """ 
    Agent navigates towards goal.
    
    arguments:
    env         --  running PybulletEnvironment
    goal        --  coordinates of the goal
    gc_network  --  grid cell network used for navigation (pod, linear_lookahead, combo)
                    or grid cell spiking generation (analytical)
    gc_spiking  --  grid cell spikings at the goal (pod, linear_lookahead, combo)
    model       --  pod: agent uses the phase-offset decoder for goal vector calculation
                    linear_lookahead: agent uses linear lookahead decoder for goal vector calculation
                    combo: agent uses pod until arrival, than switches to linear lookahead
                    analytical: agent calculates precise goal vector using coordinates, collects spikings
                    (default combo)
    step_limit  --  navigation stops after step_limit amount of steps (default infinity)
    plot_it     --  if true: plot the navigation (default false)
    obstacles   --  if true: movement vector is a combination of goal and obstacle vector (default true)
    
    collect_data_traj -- return necessary data for trajectory generation
    collect_data_reachable  -- return necessary data for reachability dataset generation
    exploration_phase   -- track movement for cognitive map and place cell model (this is a misnomer and also used in the navigation phase)
    """

    if collect_data_traj:
        freq = collect_data_traj
        data = []

    if model == "combo":
        env.mode = "pod"
    else:
        env.mode = model

    env.goal_pos = goal

    if model != "analytical":
        gc_network.set_as_target_state(gc_spiking)

    env.nr_ofsteps = 0
    env.turn_to_goal(gc_network, pod)

    n = 0  # time steps
    stop = False  # stop signal received
    end_state = ""  # for plotting
    status = 0
    while n < step_limit and not stop:
        env.navigation_step(gc_network, pod, obstacles=obstacles)

        if pc_network is not None and cognitive_map is not None:
            observations = get_observations(env)
            [firing_values, created_new_pc] = pc_network.track_movement(gc_network.gc_modules, observations,
                                                                        env.xy_coordinates[-1])

            cognitive_map.track_movement(firing_values, created_new_pc, pc_network.place_cells[-1], exploration_phase=exploration_phase)

        status = env.get_status()
        if status == -1:
            # Agent got stuck
            end_state = "Agent got stuck"
            stop = True
        elif status == 1:
            if model == "combo" and env.mode == "pod":
                # In combined mode, switch from pod to linear lookahead
                env.mode = "linear_lookahead"
                env.nr_ofsteps = 0
                env.turn_to_goal(gc_network, pod)
            else:
                # Agent reached the goal
                end_state = "Agent reached the goal. Actual distance: " + str(
                    np.linalg.norm(env.goal_pos - env.xy_coordinates[-1])) + "."
                stop = True

        # over == 0 -> agent is still moving

        if collect_data_traj and n % freq == 0:
            # collect grid cell spikings for trajectory generation
            spiking = gc_network.consolidate_gc_spiking().flatten()
            data.append((env.xy_coordinates[-1], env.orientation_angle[-1], spiking))

        n += 1

    if plot_it:
        plot.plotTrajectoryInEnvironment(env, title=end_state)

    pc = PlaceCell(gc_connections=gc_network.gc_modules, observations=get_observations(env), coordinates=env.xy_coordinates[-1])
    if collect_data_traj:
        return status, data
    return status, pc


if __name__ == "__main__":
    print("""Test the local controller's ability of vector navigation with obstacle avoidance.""")

    experiment = None
    """
    Available decoders:
    - pod: phase-offset decoder
    - linear_lookahead: linear lookahead decoder
    - analytical: precise calculation of goal vector with information that is not biologically available to the agent
    - combo: uses pod until < 0.5 m from the goal, then switches to linear_lookahead for higher precision 
    The navigation uses the faster pod decoder until the agent thinks it has reached its goal, 
    then switches to slower linear lookahead for increased accuracy.

    Change the start and goal position and environment model, as needed.
    """

    experiment = "vector_navigation"
    """
    Test the local controller with different decoders

    Ctrl-F to see where to adjust the following parameters
    1) CHOOSE THE DECODER YOU WANT TO TEST
    2) CHOOSE THE DISTANCE TO THE GOAL
    3) CHOOSE WHETHER TO PERFORM
        3A) A SIMPLE RETURN TO START
        3B) GENERATING THE GOAL SPIKINGS, NAVIGATING TO THE GOAL, THEN RETURN TO START
    4) ADJUST THE NAME FOR SAVING YOUR RESULTS

    """

    experiment = "obstacle_avoidance"
    """ 
    Test the obstacle avoidance system

    Ctrl-F to see where to adjust the following parameters
    1) CHOOSE WHETHER TO TEST WITH ANALYTICAL OR BIO-INSPIRED GOAL VECTOR CALCULATION
    2) ADJUST TEST PARAMETER RANGES
        2A) test a range of parameter values in different combinations              
        2B) choose a few combinations to test
    """

    from system.controller.simulation.pybulletEnv import PybulletEnvironment

    if not experiment:
        # env_model = "plane"
        # env_model = "Savinov_test7"
        # env_model = "Savinov_val2"
        env_model = "Savinov_val3"

        # Adjust start and goal
        start = [-6, -0.5]
        goal = [-8, -0.5]

        dt = 1e-2

        # initialize grid cell network and create target spiking
        gc_network = setup_gc_network(dt)
        target_spiking = create_gc_spiking(start, goal)

        # model = "pod"
        # model = "linear_lookahead"
        # model = "analytical"
        model = "combo"

        from system.controller.simulation.pybulletEnv import PybulletEnvironment

        env = PybulletEnvironment(False, dt, env_model, "analytical", start=start)

        vector_navigation(env, goal, gc_network, gc_spiking=target_spiking, model=model, step_limit=float('inf'),
                          plot_it=True, exploration_phase=False)

    elif experiment == "vector_navigation":
        import time

        nr_trials = 1
        env_model = "plane"
        dt = 1e-2

        error_array = []
        actual_error_array = []
        actual_error_goal_array = []
        time_array = []

        from system.controller.simulation.pybulletEnv import PybulletEnvironment

        for i in range(0, nr_trials):
            # initialize grid cell network and create target spiking
            gc_network = setup_gc_network(dt)

            # 1) CHOOSE THE DECODER YOU WANT TO TEST
            model = "pod"
            # model = "linear_lookahead"
            # model = "combo"

            env = PybulletEnvironment(False, dt, env_model, model, start=[0, 0])

            # changes the update fraction and arrival threshold according to the chosen model
            if model == "pod":
                env.pod_arrival_threshold = 0.2
            elif model == "linear_lookahead":
                update_fraction = 0.2

            """Picks a location at circular edge of environment"""
            # 2) CHOOSE THE DISTANCE TO THE GOAL
            distance = 15  # goal distance
            angle = np.random.uniform(0, 2 * np.pi)
            goal = env.xy_coordinates[0] + np.array([np.cos(angle), np.sin(angle)]) * distance

            start = np.array([0, 0])

            # 3) CHOOSE WHETHER TO PERFORM

            # 3A) A SIMPLE RETURN TO START
            simple = True
            if simple:
                """ navigate ~ 15 m away from the start position """
                target_spiking = gc_network.consolidate_gc_spiking()
                vector_navigation(env, goal, gc_network, model="analytical")
                start_time = time.time()
                vector_navigation(env, list(start), gc_network, gc_spiking=target_spiking, model=model, step_limit=8000,
                                  plot_it=False)
                trial_time = time.time() - start_time
                """------------------------------------------------------------------------------------------"""
            else:
                # 3B) GENERATING THE GOAL SPIKINGS, NAVIGATING TO THE GOAL, THEN RETURN TO START
                """ alternatively: generate spiking at goal then navigate there before returning to the start """
                start_spiking = gc_network.consolidate_gc_spiking()
                target_spiking = create_gc_spiking(start, goal)
                env = PybulletEnvironment(False, dt, env_model, model, start=list(start))

                if model == "pod":
                    env.pod_arrival_threshold = 0.2
                elif model == "linear_lookahead":
                    update_fraction = 0.2

                start_time = time.time()
                vector_navigation(env, list(goal), gc_network, gc_spiking=target_spiking, model=model, step_limit=8000,
                                  plot_it=False)
                actual_error_goal = np.linalg.norm(env.xy_coordinates[-1] - env.goal_pos)
                actual_error_goal_array.append(actual_error_goal)
                env.nr_ofsteps = 0
                vector_navigation(env, list(start), gc_network, gc_spiking=start_spiking, model=model, step_limit=8000,
                                  plot_it=False)

                trial_time = time.time() - start_time
                """------------------------------------------------------------------------------------------"""

            # Decoding Error
            error = np.linalg.norm((env.xy_coordinates[-1] + env.goal_vector) - env.goal_pos)
            error_array.append(error)

            # Navigation Error
            actual_error = np.linalg.norm(env.xy_coordinates[-1] - env.goal_pos)
            actual_error_array.append(actual_error)

            time_array.append(trial_time)
            print(trial_time)

            env.end_simulation()

            progress_str = "Progress: " + str(int((i + 1) * 100 / nr_trials)) + "% | Latest error: " + str(error)
            print(progress_str)

        # Directly plot and print the errors (distance between goal and actual end position)
        # error_plot(error_array)
        # print(error_array)

        # 4) ADJUST THE NAME FOR SAVING YOUR RESULTS
        # Save the data of all trials in a dedicated folder
        name = "test"
        directory = "experiments/"
        if not os.path.exists(directory):
            os.makedirs(directory)
        directory = "experiments/" + name
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Decoding Error (Return to start)
        np.save("experiments/" + name + "/error_array", error_array)
        # Navigation Error (Return to start)
        np.save("experiments/" + name + "/actual_error_array", actual_error_array)
        # Navigation Error of navigating to the goal in case of 3B
        np.save("experiments/" + name + "/actual_error_goal_array", actual_error_goal_array)
        # Time Cost
        np.save("experiments/" + name + "/time_array", time_array)
        # np.save("experiments/"+name+"/gc_array", gc_array)
        # np.save("experiments/"+name+"/position_array", position_array)
        # np.save("experiments/"+name+"/vectors_array", vector_array)

    elif experiment == "obstacle_avoidance":

        def three_trials(model, working_combinations, num_ray_dir, cone, mapping, combine):
            """ TRIAL 1 -----------------------------------------------------------------------------------------------------------------------"""
            start = [-1, -2]
            goal = [0, 2]
            env_model = "obstacle_map_1"

            # initialize grid cell network and create target spiking
            if model == "combo":
                gc_network = setup_gc_network(1e-2)
                target_spiking = create_gc_spiking(start, goal)
            else:
                gc_network = None
                target_spiking = None

            env = PybulletEnvironment(False, 1e-2, env_model, "analytical", start=start)

            env.mapping = mapping
            env.combine = combine
            env.num_ray_dir = num_ray_dir
            env.tactile_cone = cone

            over, _ = vector_navigation(env, goal, gc_network=gc_network, gc_spiking=target_spiking, model=model,
                                        plot_it=False, step_limit=10000)
            if over != 1: return
            print("here", over, mapping, combine, num_ray_dir, cone)

            nr_steps = env.nr_ofsteps

            """ TRIAL 2 -----------------------------------------------------------------------------------------------------------------------"""
            start = [0, -2]
            goal = [-1.5, 2]
            env_model = "obstacle_map_2"

            if model == "combo":
                gc_network = setup_gc_network(1e-2)
                target_spiking = create_gc_spiking(start, goal)
            else:
                gc_network = None
                target_spiking = None

            env = PybulletEnvironment(False, 1e-2, env_model, "analytical", start=start)

            env.mapping = mapping
            env.combine = combine
            env.num_ray_dir = num_ray_dir
            env.tactile_cone = cone

            over, _ = vector_navigation(env, goal, gc_network=gc_network, gc_spiking=target_spiking, model=model,
                                        plot_it=False, step_limit=10000)
            if over != 1: return

            nr_steps += env.nr_ofsteps

            """ TRIAL 3 -----------------------------------------------------------------------------------------------------------------------"""
            start = [-2.5, -2]
            goal = [-1, -1]
            env_model = "obstacle_map_3"

            # initialize grid cell network and create target spiking
            if model == "combo":
                gc_network = setup_gc_network(1e-2)
                target_spiking = create_gc_spiking(start, goal)
            else:
                gc_network = None
                target_spiking = None

            env = PybulletEnvironment(False, 1e-2, env_model, "analytical", start=start)

            env.mapping = mapping
            env.combine = combine
            env.num_ray_dir = num_ray_dir
            env.tactile_cone = cone

            over, _ = vector_navigation(env, goal, gc_network=gc_network, gc_spiking=target_spiking, model=model,
                                        plot_it=False, step_limit=10000)
            if over != 1: return
            print(over, mapping, combine, num_ray_dir, cone)

            nr_steps += env.nr_ofsteps

            # save all combinations that passed all three tests and how many time steps the agent took in total
            working_combinations.append((nr_ofrays, cone, mapping, combine, nr_steps))

            print(working_combinations)
            nr_steps_list = [sub[4] for sub in working_combinations]
            min_val = min(nr_steps_list)
            index = nr_steps_list.index(min_val)
            print("combination with fewest steps: ", working_combinations[index])


        # 1) CHOOSE WHETHER TO TEST WITH ANALYTICAL OR BIO-INSPIRED GOAL VECTOR CALCULATION
        model = "analytical"  # "combo"

        working_combinations = []
        # 2) ADJUST TEST PARAMETER RANGES
        all = False
        if all:
            # 2A) test a range of parameter values in different combinations
            for nr_ofrays in [16, 32, 64]:
                for cone in [90, 120, 180, 360]:
                    num_ray_dir = int(nr_ofrays // (360 / cone))
                    for mapping in [0.5, 1, 1.5, 2]:
                        for combine in [0.5, 1, 1.5, 2]:
                            three_trials(model, working_combinations, num_ray_dir, cone, mapping, combine)
        else:
            # 2B) choose a few combinations to test
            combinations = [(64, 180, 2, 0.5), (64, 120, 1.5, 1.5)]
            for c in combinations:
                nr_ofrays, cone, mapping, combine = c
                num_ray_dir = int(nr_ofrays // (360 / cone))
                three_trials(model, working_combinations, num_ray_dir, cone, mapping, combine)

        directory = "experiments/"
        if not os.path.exists(directory):
            os.makedirs(directory)
        np.save("experiments/working_combinations", working_combinations)
