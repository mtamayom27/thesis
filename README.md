# BA - Bio-Inspired Navigation

Welcome to the Git Repo for the Bachelor Thesis on

> Neurobiologically Inspired Navigation for
Artificial Agents

In this file we explain the installation process and describe the use of some of the different files.
For a detailed description and the reasoning behind this code, please refer to the thesis.


## Install packages
The code is based on Python3. It has only been tested on Python3.9 and might not work on other versions.

Install the following packages to run the code:

Install the required packages with

        pip install -r requirements.txt

A gcc,g++ and latex installation are required and can be added with the following commands if not installed already. 

        sudo apt install gcc
        sudo apt install g++

        sudo apt install texlive texlive-latex-extra texlive-fonts-recommended dvipng cm-super
        pip install latex

You also need to setup the modified version of range-libc, that can be found in this repository. The original version can be found at https://github.com/kctess5/range_libc.
It had to be modified to work with Python3. Follow these instructions (https://github.com/kctess5/range_libc#python-wrappers) to install. Additionally it requires ros nav_msgs.
        
        conda install -c conda-forge ros-nav-msgs
        cd range_libc/pywrapper
        python setup.py install
        python test.py


## More Setup

To use the data described in the thesis go to:
https://syncandshare.lrz.de/getlink/fiRDKFDsyVqEDj5wFHcwau/data_submit.zip

This folder contains:
- experiments: the experiment results from the thesis
- bio_data: model of grid cells, place cells and the cognitive map
- RE: trajectory and reachability dataset for training as well as the final model

## Code
This code implements the methodology as well as performs the experiments described in the thesis.

### Simulation
system/controller/simulation/pybulletEnv.py

Test different environment and the camera by moving an agent with your keyboard and plotting its trajectory. Change between four different environments.

Available environments:
- plane
- Savinov_test7
- Savinov_val2
- Savinov_val3

----

### Local Controller
system/controller/local_controller/local_navigation.py

Test navigating with the local controller using different movement vector and goal vector calculation methods in different environments.

Available decoders:
- pod: phase-offset decoder
- linear_lookahead: linear lookahead decoder
- analytical: precise calculation of goal vector with information that is not biologically available to the agent
- combo: uses pod until < 0.5 m from the goal, then switches to linear_lookahead for higher precision 
        The navigation uses the faster pod decoder until the agent thinks it has reached its goal, 
        then switches to slower linear lookahead for increased accuracy.

Calculation of movement vector:
- obstacles = True: combine the obstacle and goal vector to create the movement vector
- obstacles = False: the movement vector is the goal vector

#### Decoder Test
system/controller/local_controller/local_navigation.py

Perform the experiments described in subsection 6.2.2 Goal Vector Computation.
Set ***experiment = "vector_navigation"***

Choose between the:
- Available decoders: ***model = "pod" or "linear_lookahead" or "combo"***
- different distances to the goal location: ***distance = 15 or 2 or x***
- experiment types: 
    - A) return to start: ***simple = True*** 
    - B) navigate to goal, then return to start: ***simple = False*** 

Plot your results using createPlots.py
#### Obstacle Avoidance Test
system/controller/local_controller/local_navigation.py

Perform the experiments described in subsection 6.2.1 Obstacle Avoidance.
Set ***experiment = "obstacle_avoidance"***

- Choose between decoders: ***model = "analytical" or "combo"***
- Adjust which parameters to test
    - ***all = True*** : test entire range of parameter combinations
    - ***all = False*** : manually choose which combinations to test

To plot any of the attempts set ***plot_it = True***.

----

### Reachability Estimator
system/controller/reachability_estimator/reachabilityEstimation.py

There are several methods of judging reachability available:
- ***type = "distance"***: return distance between nodes
- ***type = "neural_network"***: use the neural model
- ***type = "simulation"***: simulate the navigation and return success or failure (only works as a connection RE)
- ***type = "view_overlap"***: return the view overlap between the nodes (only works as a connection RE)

To adjust what values are considered as reachable adjust the creation and connection thresholds in pc_network.py and cognitivemap.py.

#### Trajectory Generation
system/controller/reachability_estimator/data_generation/gen_trajectories.py

Generate trajectories through the environment storing grid cell spikings and coordinates.

Testing:
Generate/ load a few trajectories per map and display.

Default:
Generate 1000 trajectories of length 3000 with a saving frequency of 10 
in the environment "Savinov_val3"

Parameterized:
Adjust filename, env_model, num_traj, traj_length and cam_freq 

#### Reachability Dataset Generation
system/controller/reachability_estimator/data_generation/dataset.py

Generate a dataset of reachability samples or load from an existing one.
    
Testing:
Generate or load and display a few samples.

Parameterized call:
- Save to/load from filename
- Generate until there are num_samples samples
- Use trahectories from traj_file
    
Default: Time the generation of 50 samples

#### Reachability Estimator Neural Network
system/controller/reachability_estimator/training/train_multiframe_dst.py

Perform the experiments described in subsection 6.3.1 Reachability Estimator

Test or train the Reachability Estimator.
Set ***testing = True*** to test the models performance on the test dataset.
Set ***testing = False*** to train a model on the training dataset.

----

### Topological Navigation

#### Exploration
system/controller/topological/explorationPhase.py

Perform the experiments described in subsection 6.3.2 Cognitive Map Creation

Create a cognitive map by exploring the environment.
Adjust ***connection_re_type*** and ***creation_re_type***:
-  types: "firing", "neural_network", "distance", "simulation", "view_overlap"
    - "firing": place cell firing value
    - others: see explanation for RE
- connection: 
    - ("all","instant"): all nodes are tested during creation
    - ("radius", "delayed"): only nodes within 5m of each other are considered for connection, connection is calculated after exploration is over

To adjust what values are considered as reachable adjust the creation and connection thresholds in pc_network.py and cognitivemap.py.

#### Cognitive Map
system/bio_model/cognitivemap.py

Perform the experiments described in subsection 6.3.2 Cognitive Map Creation

Update the connections on the cognitive map or draw it.
Set ***testing=True*** to test the place cell drift of the cognitive map. Set ***from_data=False*** to recalculate the drift.

To adjust what values are considered as reachable adjust the creation and connection thresholds in pc_network.py and cognitivemap.py.

#### Navigation
system/controller/topological/traj_following.py

Perform the experiments described in subsection 6.3.3 Navigation in a Cluttered Environment
Test navigation through the maze. 
Adjust start and goal node.

----

## Code Structure

        .
        ├── range_libc                                  # Modified version of range_libc
        ├── system                                      # Navigation system
        │   ├── bio_model                               # Scripts modeling grid cells, place cells and the cognitive map and required data
        │   ├── controller                              # Scripts controlling the agent and environment
        │   │   ├── local_controller                    # Scripts controlling local navigation
        │   │   │   ├── decoder                         # Scripts for different grid cell decoder mechanism
        │   │   │   └── local_navigation.py             # Handles vector navigation and obstacle avoidance
        │   │   ├── reachability_estimator              # Scripts and data for reachability estimation
        │   │   │   ├── data                            # Store generated trajectories and reachability dataset
        │   │   │   ├── data_generation                 # Scripts for trajectory and reachability dataset generation
        │   │   │   ├── training                        # Scripts for training the reachability estimator
        │   │   │   ├── networks.py                     # Neural network structurere
        │   │   │   └── reachabilityEstimation.py       # Handles different kinds of reachability estimation
        │   │   ├── simulation                          # Scripts and data for simulating the agent in the environment
        │   │   │   ├── environment                     # Scripts and data concerning the environment
        │   │   │   ├── p3dx                            # Data for the agent
        │   │   │   └── pybulletEnv.py                  # Handles simulating steps in the environment
        │   │   └── topological                         # Scripts for topological navigation
        │   │   │   ├── explorationPhase.py             # Explorting the environment
        │   │   │   └── traj_following.py               # Navigating the environment
        │   ├── plotting                                # Scripts to create plots
        ├── README.md                                   # You are here. Overview of project
        └── requirements.txt                            # Required packages to install
## Further Questions

To ask questions about the thesis or code please reach out to johanna.latzel@tum.de

## Acknowledgement

This code was largely inspired and adapted from Engelmann(2021)[^c1] and Meng(2022)[^c2]


[^c1]: Engelmann Tim, “Biologically inspired spatial navigation using vector-based
and topology-based path planning", Sept. 2021
[^c2]: Meng, X., N. Ratliff, Y. Xiang, and D. Fox , “Scaling Local Control to Large-
Scale Topological Navigation.” 2020