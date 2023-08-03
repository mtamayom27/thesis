import numpy as np
import torch

from system.bio_model.placecellModel import PlaceCell
from system.controller.reachability_estimator import networks
from system.controller.reachability_estimator.reachabilityEstimation import OldNetworkReachabilityEstimator


def make_nets(specs, device):
    ret = {}
    for net_name, spec in specs.items():
        net_class = getattr(networks, spec['class'])
        net_args = spec.get('net_kwargs', {})
        net = net_class(no_weight_init=True, **net_args).to(device)
        ret[net_name] = net
    return ret


class RGBDNetworkReachabilityEstimator(OldNetworkReachabilityEstimator):
    def __init__(self, device='cpu', debug=False, weights_file=None):
        """ Creates a reachability estimator that judges reachability
            between two locations based on its type

        arguments:
        weights_file    -- neural network
        device          -- device used for calculations (default cpu)
        """
        super().__init__(device=device, debug=debug, weights_file=weights_file)

    def predict_reachability(self, start: PlaceCell, goal: PlaceCell) -> float:
        """ Return reachability estimate from start to goal using the re_type """
        return self.predict_reachability_batch([start.observations[0]], [goal.observations], batch_size=1)[0]

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

                    # Extract features
                    pair_features = nets['img_encoder'](
                        src_batch2.view(batch_size * win_size, c, h, w),
                        goal_batch.view(batch_size * win_size, c, h, w)).view(batch_size, win_size, -1)

                    # Convolutional Layer
                    conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

                    # Get prediction
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

    def pass_threshold(self, reachability_factor, threshold) -> bool:
        return reachability_factor > threshold
