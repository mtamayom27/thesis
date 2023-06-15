''' This code has been adapted from:
***************************************************************************************
*    Title: "Scaling Local Control to Large Scale Topological Navigation"
*    Author: "Xiangyun Meng, Nathan Ratliff, Yu Xiang and Dieter Fox"
*    Date: 2020
*    Availability: https://github.com/xymeng/rmp_nav
*
***************************************************************************************
'''
import torch
import numpy as np
import tabulate
import yaml

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..",".."))

import system.controller.reachability_estimator.networks as networks
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.local_controller.local_navigation import setup_gc_network, vector_navigation

debug = True # if True: print debug output
def print_debug(*params):
    """ output only when in debug mode """
    if debug:
        print(*params)

def get_path():
    """ returns path to data storage folder """
    dirname = os.path.dirname(__file__)
    return dirname

def make_nets(specs, device):
    ret = {}
    for net_name, spec in specs.items():
        net_class = getattr(networks, spec['class'])
        net_args = spec.get('net_kwargs', {})
        net = net_class(no_weight_init=True, **net_args).to(device)
        ret[net_name] = net
    return ret

class ReachabilityEstimator:
    def __init__(self, weights_file = None, device='cpu', type = "distance"):
        """ Creates a reachability estimator that judges reachability 
            between two locations based on its type
            
        arguments:
        weights_file    -- neural network
        device          -- device used for calculations (default cpu)
        type            -- type of reachability estimation
                        distance: returns distance between two coordinates
                        neural_network: returns neural network prediction using images
                        simulation: simulates navigation attempt and returns result
                        view_overlap: judges reachability based on view overlap of start and goal position within the environment
        """
        
        if type == "neural_network":
            state_dict = torch.load(weights_file, map_location='cpu')
            print_debug('loaded %s' % weights_file)
            g = state_dict.get('global_args', {})
            print_debug('global args:')
            print_debug(tabulate.tabulate(g.items()))
            
            model_spec = {'img_encoder': {'class': 'ImagePairEncoderV2', 'net_kwargs': {'init_scale': 1.0}, 'opt': 'Adam', 'opt_kwargs': {'lr': 0.0003, 'eps': 1e-05}}, 'reachability_regressor': {'class': 'ReachabilityRegressor', 'net_kwargs': {'input_dim': 5120, 'init_scale': 1.0}, 'opt': 'Adam', 'opt_kwargs': {'lr': 0.0003, 'eps': 1e-05}},"conv_encoder": {'class': 'ConvEncoder', 'net_kwargs': {'input_dim': 512, 'init_scale': 1.0}, 'opt': 'Adam', 'opt_kwargs': {'lr': 0.0003, 'eps': 1e-05}}}


            if isinstance(model_spec, dict):
                nets = make_nets(model_spec, device)
            else:
                nets = make_nets(yaml.load(open(model_spec).read()), device)
                
            print_debug(nets)

            for name, net in nets.items():
                net.load_state_dict(state_dict['nets'][name])
                net.train(False)

            self.device = device
            self.g = g
            self.nets = nets
        
        self.type = type
        self.env_model = None
    
    def predict_reachability(self,start,goal,env_model = None):
        """ Return reachability estimate from start to goal using the re_type """
        if self.type == "distance":
            return self.predict_reachability_distance(start.env_coordinates, goal.env_coordinates)
        elif self.type == "neural_network":
            return self.predict_reachability_multiframe(start.observations[0],goal.observations)
        elif self.type == "simulation":
            if not self.env_model:
                raise ValueError("missing env_model; needed for simulating reachability")
            return self.predict_reachability_simulation(start, goal,self.env_model)
        elif self.type == "view_overlap":
            #TODO: untested and unfinished
            self.env_model = "Savinov_val3"
            return self.predict_reachability_view_overlap(start,goal,self.env_model)
    
    def predict_reachability_distance(self,start_pos,goal_pos):
        """ Return distance between start and goal as an estimation of reachability"""
        return np.linalg.norm(start_pos-goal_pos)
    
    def predict_reachability_simulation(self,start,goal,env_model):
        """ Simulate movement between start and goal and return whether goal was reached """
        dt = 1e-2

        #initialize grid cell network and create target spiking
        gc_network = setup_gc_network(dt)
        gc_network.set_as_current_state(start.gc_connections)
        target_spiking = goal.gc_connections
        start_pos = start.env_coordinates
        goal_pos = goal.env_coordinates
        
        model = "combo"

        from system.controller.simulation.pybulletEnv import PybulletEnvironment
        env = PybulletEnvironment(False,dt,env_model, "analytical",start = list(start_pos))
        
        over,_ = vector_navigation(env, list(goal_pos), gc_network, gc_spiking = target_spiking, model = model, step_limit = 750, plot_it = False)
        
        if over == 1:
            self.fov = 120*np.pi/180
        
            map_layout = MapLayout(env_model)
        
            overlap_ratios = map_layout.view_overlap(env.xy_coordinates[-1], env.orientation_angle[-1], self.fov,
                                          goal_pos, env.orientation_angle[-1], self.fov,mode='plane')
            
            env.end_simulation()
            if overlap_ratios[0] < 0.1 and overlap_ratios[1] < 0.1:
                #Agent is close to the goal, but seperated by a wall.
                return 0.0
            elif np.linalg.norm(goal_pos - env.xy_coordinates[-1]) > 0.7:
                #Agent actually didn't reach the goal and is too far away.
                return 0.0
            else:
                #Agent did actually reach the goal
                return 1.0
        else:
            env.end_simulation()
            return 0.0
        
    def predict_reachability_view_overlap(self,start,goal,env_model):
        """ Reachability Score based on the view overlap of start and goal in the environment """
        start_pos = start.env_coordinates
        goal_pos = goal.env_coordinates

        self.fov = 120*np.pi/180
        
        map_layout = MapLayout(env_model)

        heading1 = np.degrees(np.arctan2(goal_pos[0]-start_pos[0],goal_pos[1]-start_pos[1]))

        overlap_ratios = map_layout.view_overlap(start_pos, heading1, self.fov,
                                        goal_pos, heading1, self.fov,mode='plane')

        return (overlap_ratios[0]+overlap_ratios[1])/2
        
    def predict_reachability_multiframe(self, ob, goal_seq):
        """ Return the trained models estimation of reachability """
        ret = self.predict_reachability_batch([ob], [goal_seq],batch_size=1)[0]
        return ret
    
    def predict_reachability_batch(self, obs, goals, batch_size=64):
        nets = self.nets
        with torch.no_grad():
            model_variant = self.g.get('model_variant', 'default')
    
            def helper(ob_batch, goal_batch):
                # as_tensor() is very slow when passing in a list of np arrays, but is 30X faster
                # when wrapping the list with np.array().
                if isinstance(ob_batch[0], np.ndarray):
                    ob_batch = np.array(ob_batch)
                elif isinstance(ob_batch[0], torch.Tensor):
                    if not isinstance(ob_batch, torch.Tensor):
                        ob_batch = torch.stack(ob_batch)
                else:
                    raise RuntimeError('Unsupported datatype: %s' % type(ob_batch[0]))
                if isinstance(goal_batch[0][0], np.ndarray):
                    goal_batch = np.array(goal_batch)
                elif isinstance(goal_batch[0][0], torch.Tensor):
                    if not isinstance(goal_batch, torch.Tensor):
                        goal_batch = torch.stack(goal_batch)
                else:
                    raise RuntimeError('Unsupported datatype: %s' % type(goal_batch[0]))
    
                ob_batch = torch.as_tensor(ob_batch).to(non_blocking=True).float()
                goal_batch = torch.as_tensor(goal_batch).to(non_blocking=True).float()

                batch_size, win_size, c, h, w = goal_batch.size()
                
    
                if model_variant == 'the_only_variant':
                    assert goal_batch.size(1) == self.g["n_frame"]
                    ob_batch2 = ob_batch.unsqueeze(1).expand_as(goal_batch).contiguous()
                    pair_features = nets['img_encoder'](
                        ob_batch2.view(-1, c, h, w),
                        goal_batch.view(-1, c, h, w)).view(1, -1)
                    
                    pred_reachability = torch.sigmoid(
                        nets['reachability_regressor'](pair_features)).squeeze(1)
                    return pred_reachability
                
                elif model_variant == "pair_conv":
                    assert goal_batch.size(1) == self.g["n_frame"]
                    src_batch2 = ob_batch.unsqueeze(1).expand_as(goal_batch).contiguous()
                    
                    #Extract features
                    pair_features = nets['img_encoder'](
                        src_batch2.view(batch_size*win_size, c, h, w),
                        goal_batch.view(batch_size*win_size, c, h, w)).view(batch_size,win_size, -1)
                    
                    #Convolutional Layer
                    conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))
                    
                    #Get prediction
                    pred_reach_logits = nets['reachability_regressor'](conv_feature)

                    pred_reach = torch.sigmoid(pred_reach_logits).squeeze(1)

                    return pred_reach

                else:
                    raise RuntimeError('Unsupported model variant %s' % model_variant)

        assert len(obs) == len(goals)
        n = len(obs)

        results = []
        n_remaining = n
        while n_remaining > 0:
            results.append(helper(obs[n - n_remaining: n - n_remaining + batch_size],
                                  goals[n - n_remaining: n - n_remaining + batch_size]))
            n_remaining -= batch_size
        return torch.cat(results, dim=0).data.cpu().numpy()