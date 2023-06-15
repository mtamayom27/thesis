''' This code has been adapted from:
***************************************************************************************
*    Title: "Scaling Local Control to Large Scale Topological Navigation"
*    Author: "Xiangyun Meng, Nathan Ratliff, Yu Xiang and Dieter Fox"
*    Date: 2020
*    Availability: https://github.com/xymeng/rmp_nav/tree/77a07393ccee77b0c94603642ed019268ce06640/rmp_nav/data_generation
*
***************************************************************************************
'''
import numpy as np
import time
import h5py

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))



from system.controller.simulation.pybulletEnv import PybulletEnvironment
from system.controller.local_controller.local_navigation import setup_gc_network, vector_navigation
from system.controller.simulation.environment.map_occupancy import MapLayout

import system.plotting.plotResults as plot

def get_path():
    """ returns path to data storage folder """
    dirname = os.path.join(os.path.dirname(__file__), "..")
    return dirname

#Print debug statements
debug = True#False
def print_debug(*params):
    if debug:
        print(*params)
        
plotting = False

def display_trajectories(filename,env_model):
    """ display all trajectories on one map, as well as a heatmap to check coverage """
    filename = filename+".hd5"
    
    import matplotlib.pyplot as plt
    dirname = get_path()
    dirname = os.path.join(dirname, "data/trajectories")
    dirname = os.path.join(dirname, filename)
    filepath = os.path.realpath(dirname)
    hf = h5py.File(filepath, 'r')
    print("number of datasets: ",len(hf.keys()))
    
        
    #plot all trajectories in one map
    xy_coordinates = []
    for key in list(hf.keys()):
        ds_array = hf[key][()]
        coord = [i[0] for i in ds_array]
        xy_coordinates+=coord
        print(key)
        
    #     # plot individual trajectories:
    #     # plot.plotTrajectoryInEnvironment(None,None,None,"title",xy_coordinates=coord,env_model="SMTP")
    # plot.plotTrajectoryInEnvironment(None,filename,xy_coordinates=xy_coordinates,env_model=env_model)
    
    #heatmap
    x = [i[0] for i in xy_coordinates]
    y = [i[1] for i in xy_coordinates]

    #get dimensions
    env = PybulletEnvironment(False,1e-2,env_model,mode = "analytical")
    fig, ax = plt.subplots()
    hh = ax.hist2d(x,y, bins=[np.arange(env.dimensions[0],env.dimensions[1],0.1)
                          ,np.arange(env.dimensions[2],env.dimensions[3],0.1)],norm = "symlog")
    fig.colorbar(hh[3], ax=ax)
    plt.show()

def sample_location(env_model):
    ''' Sample location within environment boundaries'''
    if env_model == "Savinov_val3":
        dimensions = [-9, 6, -5, 4]
    elif env_model == "Savinov_val2":
        dimensions = [-5, 5, -5, 5]
    elif env_model == "Savinov_test7":
        dimensions = [-9, 6, -4, 4]
    elif env_model == "plane":
        dimensions = [-9, 6, -4, 4]
    else: raise ValueError("env_model does not exist")

    x = np.around(np.random.uniform(dimensions[0],dimensions[1]),1)
    y = np.around(np.random.uniform(dimensions[2],dimensions[3]),1)
    return (x,y)

def valid_location(env_model):
    """ Sample valid location for agent in the environment """
    while True:
        x,y = sample_location(env_model)
        env = PybulletEnvironment(False,1e-2,env_model,mode = "pod",start = [x,y])
        if not env.detect_maze_agent_contact():
            env.end_simulation()
            return [x,y]
        env.end_simulation()

def gen_samples(course):
    ''' Generate start and goal '''
    start = valid_location(course)
    
    #The goal location does not have to be entirely reachable, only within range
    goal = sample_location(course)
    return [start,goal]


def gen_multiple_goals(env_name, nr_of_goals):
    ''' Generate start and multiple subgoals'''
    
    points = []
    for i in range(nr_of_goals):
        points.append(sample_location(env_name))
        
    start = valid_location(env_name)
    points.insert(0, start)
    return points

def waypoint_movement(env_model,cam_freq,traj_length):
    ''' Calculates environment-specific waypoints from start to goal and creates
    trajectory by making agent follow them.
    
    arguments:
    env_model      -- environment name
    cam_freq        -- at what frequency is the state of the agent saved
    traj_length     -- how many timesteps should the agent run
    '''
    
    #generate start and final goal
    start, goal = gen_samples(env_model)
    
    # calculate waypoints, if no path can be found return
    savinov = MapLayout(env_model)
    waypoints = savinov.find_path(start, goal)
    if waypoints is None:
        print_debug("No path found!")
        return []
    
    # initialize environment
    goals = waypoints
    visualize=False
    dt = 1e-2
    env = PybulletEnvironment(visualize,dt,env_model,"analytical",buildDataSet=True,start=start)
    gc_network = setup_gc_network(dt)
    
    samples = []
    goal_reached = True
    for g in goals:
        print_debug("new waypoint",g)
        
        # if trajectory_length has been reached the trajectory can be saved
        if len(samples)>traj_length/cam_freq:
            break
        
        over,data = vector_navigation(env, g, gc_network, model = "analytical", step_limit = 5000, plot_it = False, collect_data_traj=cam_freq)
        if over == -1 or over == 0:
            goal_reached = False
        else:
            goal_reached = True
        samples += data

    #reaching the last subgoal is an indicator of a valid trajectory (the agent actually moved along the path)
    if goal_reached: 
        print_debug("successfull trajectory")
        if plotting: plot.plotTrajectoryInEnvironment(env)
        env.end_simulation()
        return samples
    else:
        print_debug("unsuccessfull trajectory")
        if plotting: plot.plotTrajectoryInEnvironment(env)
        env.end_simulation()
        return []

def generate_multiple_trajectories(out_hd5_obj,num_traj,trajectory_length,cam_freq,mapname):
    ''' Generate multiple trajectories
    
    arguments:
    out_hd5_obj         -- output file
    num_traj            -- number of trajectories that should be generated for the file
    trajectory_length   -- number of timesteps in generated trajectory
    cam_freq            -- frequency with which the agent state is saved
    mapname             -- name of environment
    '''
    dtype = np.dtype([
        ('xy_coordinates', (np.float32, 2)),
        ('orientation', np.float32),
        ('grid_cell_spiking',(np.float32,9600))
    ])
    
    seed = 123456 
    rng_trajid = np.random.RandomState(seed)

    i = 0
    while i < num_traj:
        traj_id = rng_trajid.randint(0xfffffff)
        dset_name = '/%08x' % traj_id

        print('processing trajectory %d id: %08x' % (i, traj_id))
        
        start_time = time.time()

        if dset_name in out_hd5_obj:
            print('dataset %s exists. skipped' % dset_name)
            i += 1
            continue
        
        samples = []
        while len(samples)<60:
            #try again if unsuccesfull or trajectory too short
            samples = waypoint_movement(mapname,cam_freq,trajectory_length)


        dset = out_hd5_obj.create_dataset(
            dset_name,
            data=np.array(samples, dtype=dtype),
            maxshape=(None,), dtype=dtype)

        out_hd5_obj.flush()

        i += 1
        
        print("--- %s seconds for one trajectory ---" % (time.time() - start_time))
        
def save_trajectories(filename, mapname,num_traj,traj_length,cam_freq):
    ''' Generate and save trajectories.
    
    arguments:
    
    filename    -- filename for storing trajectories
    mapname     -- environment name
    num_traj    -- number of trajectories to be generated
    traj_length -- how many timesteps should the agent run
    cam_freq    -- at what frequency is the state of the agent saved
    '''
    dirname = get_path()
    directory = os.path.join(dirname, "data/trajectories")
    directory = os.path.realpath(directory)
    
    f = h5py.File(directory+"/"+filename+".hd5", 'a')
    f.attrs.create('agent', "waypoint")
    f.attrs.create('map_type', mapname)
    
    generate_multiple_trajectories(f, num_traj,traj_length,cam_freq,mapname)

if __name__ == "__main__":
    """ 
    Testing:
    Generate/ load a few trajectories per map and display.
    
    Default:
    Generate 1000 trajectories of length 3000 with a saving frequency of 10 
    in the environment "Savinov_val3"
    
    Parameterized:
    Adjust filename, env_model, num_traj, traj_length and cam_freq 
    """
    test = True
    if test:
        print("Testing trajectory generation in available mazes.")
        print("Testing Savinov_val3")
        save_trajectories("test_1","Savinov_val3",1,3000,10)
        display_trajectories("test_1","Savinov_val3")
        print("Testing Savinov_val2")
        save_trajectories("test_2","Savinov_val2",1,3000,10)
        display_trajectories("test_2","Savinov_val2")
        print("Testing Savinov_test7")
        save_trajectories("test_3","Savinov_test7",1,3000,10)
        display_trajectories("test_3","Savinov_test7")
    elif len(sys.argv) == 6:
        _, filename, env_model, num_traj, trajectory_length,cam_freq = sys.argv
        print_debug(sys.argv)
        save_trajectories(filename,str(env_model),int(num_traj),int(trajectory_length),int(cam_freq))
    else:
        num_traj = 1000
        trajectory_length = 3000
        cam_freq = 10
        env_model = "Savinov_val3"#"Savinov_val2","Savinov_test7"
        
        #save_trajectories("trajectories",env_model,num_traj,trajectory_length,cam_freq)
        display_trajectories("trajectories",env_model)
