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
import time
import tabulate
import numpy as np
from torchmetrics.functional import precision_recall
from torchmetrics import Accuracy, F1Score
from torchmetrics.classification import BinaryPrecision, BinaryRecall, BinaryAccuracy, BinaryF1Score
from torch.utils.data import DataLoader, RandomSampler
from torch.utils.tensorboard import SummaryWriter

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from system.controller.reachability_estimator import networks
from system.controller.reachability_estimator.training.H5Dataset import H5Dataset
from system.controller.reachability_estimator.training.utils import save_model, load_model, module_grad_stats


def get_path():
    """ returns path to data storage folder """
    dirname = os.path.join(os.path.dirname(__file__), "..")
    return dirname


def _load_weights(model_file, nets, net_opts):
    state = load_model(os.path.dirname(model_file),
                       os.path.basename(model_file), load_to_cpu=True)
    epoch = int(state['epoch'])

    for name, net in nets.items():
        net.load_state_dict(state['nets'][name])

    for name, opt in net_opts.items():
        opt.load_state_dict(state['optims'][name])
        # Move the parameters stored in the optimizer into gpu
        for opt_state in opt.state.values():
            for k, v in opt_state.items():
                if torch.is_tensor(v):
                    opt_state[k] = v.to(device='cuda')
    return epoch


def _save_model(nets, net_opts, epoch, global_args, model_file):
    """ save current state of the model """
    state = {
        'epoch': epoch,
        'global_args': global_args,
        'optims': {
            name: opt.state_dict() for name, opt in net_opts.items()
        },
        'nets': {
            name: net.state_dict() for name, net in nets.items()
        }
    }
    save_model(state, epoch, '', model_file)


def test_dst(dataset):
    """ Test model on dataset. Logs accuracy, precision, recall and f1score. """

    from system.controller.reachability_estimator.reachabilityEstimation import OldNetworkReachabilityEstimator
    filename = "trained_model_pair_conv.30"
    filepath = os.path.join(os.path.join(os.path.dirname(__file__), "../data/models"), filename)
    reach_estimator = OldNetworkReachabilityEstimator(weights_file=filepath)

    sampler = RandomSampler(dataset, True, len(dataset))

    loader = DataLoader(dataset,
                        batch_size=64,
                        sampler=sampler,
                        num_workers=24,
                        pin_memory=True,
                        drop_last=True)

    test_accuracy = 0
    test_precision = 0
    test_recall = 0
    test_f1 = 0

    accuracy = BinaryAccuracy()
    precision = BinaryPrecision()
    recall = BinaryRecall()
    f1 = BinaryF1Score()
    for idx, (batch_src_imgs, batch_dst_imgs, batch_reachability, batch_vector, _, _) in enumerate(loader):
        src_img = batch_src_imgs.to(device="cpu", non_blocking=True)
        dst_imgs = batch_dst_imgs.to(device="cpu", non_blocking=True)
        r = batch_reachability.to(device="cpu", non_blocking=True)

        src_batch = src_img.float()
        dst_batch = dst_imgs.float()

        pred_r = reach_estimator.predict_reachability_batch(src_batch, dst_batch, batch_size=64)
        pred_r = torch.from_numpy(pred_r)

        test_accuracy += accuracy(pred_r, r.int())

        test_precision += precision(pred_r, r.int())
        test_recall += recall(pred_r, r.int())

        test_f1 += f1(pred_r, r.int())

    writer = SummaryWriter()
    test_accuracy /= len(loader)
    test_precision /= len(loader)
    test_recall /= len(loader)
    test_f1 /= len(loader)

    writer.add_scalar("Accuracy/Testing", test_accuracy, 1)
    writer.add_scalar("Precision/Testing", test_precision, 1)
    writer.add_scalar("Recall/Testing", test_recall, 1)
    writer.add_scalar("fscore/Testing", test_f1, 1)


def tensor_log(title, loader, train_device, model_variant, n_frame, writer, epoch, nets):
    """ Log accuracy, precision, recall and f1score for dataset in loader."""
    with torch.no_grad():
        log_loss = 0
        log_precision = 0
        log_recall = 0
        log_accuracy = 0
        log_f1 = 0
        accuracy = BinaryAccuracy()
        precision = BinaryPrecision()
        recall = BinaryRecall()
        f1 = BinaryF1Score()
        for idx, (batch_src_imgs, batch_dst_imgs, batch_reachability, batch_vector, _, _) in enumerate(loader):
            # Get predictions
            src_img = batch_src_imgs.to(device=train_device, non_blocking=True)
            dst_imgs = batch_dst_imgs.to(device=train_device, non_blocking=True)
            r = batch_reachability.to(device=train_device, non_blocking=True)

            src_batch = src_img.float()
            dst_batch = dst_imgs.float()
            batch_size, win_size, c, h, w = dst_batch.size()

            if model_variant == "the_only_variant":
                assert dst_batch.size(1) == n_frame
                src_batch2 = src_batch.unsqueeze(1).expand_as(dst_batch).contiguous()

                # Extract features
                pair_features = nets['img_encoder'](
                    src_batch2.view(batch_size * win_size, c, h, w),
                    dst_batch.view(batch_size * win_size, c, h, w).view(batch_size, -1))

                # Get prediction
                pred_reach_logits = nets['reachability_regressor'](pair_features)

                # Log accuracy
                pred_reach = torch.sigmoid(pred_reach_logits).squeeze(1)
            elif model_variant == "pair_conv":
                assert dst_batch.size(1) == n_frame
                src_batch2 = src_batch.unsqueeze(1).expand_as(dst_batch).contiguous()

                # Extract features
                pair_features = nets['img_encoder'](
                    src_batch2.view(batch_size * win_size, c, h, w),
                    dst_batch.view(batch_size * win_size, c, h, w)).view(batch_size, win_size, -1)

                # Convolutional Layer
                conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

                # Get prediction
                pred_reach_logits = nets['reachability_regressor'](conv_feature)

                # Log accuracy
                pred_reach = torch.sigmoid(pred_reach_logits).squeeze(1)
            elif model_variant == "with_dist":
                assert dst_batch.size(1) == n_frame
                src_batch2 = src_batch.unsqueeze(1).expand_as(dst_batch).contiguous()

                # Extract features
                pair_features = nets['img_encoder'](
                    src_batch2.view(batch_size * win_size, c, h, w),
                    dst_batch.view(batch_size * win_size, c, h, w)).view(batch_size, win_size, -1)

                # Convolutional Layer
                conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

                # Get prediction
                # add the decoded goal vector
                pred_reach_logits = nets['reachability_regressor'](torch.cat((batch_vector, conv_feature), 1))
                # Log accuracy
                pred_reach = torch.sigmoid(pred_reach_logits).squeeze(1)

            new_loss = torch.nn.functional.binary_cross_entropy_with_logits(pred_reach_logits.squeeze(1), r)
            log_loss += new_loss.item()
            log_precision += precision(pred_reach_logits, r.int())
            log_recall += recall(pred_reach_logits, r.int())
            accuracy = Accuracy(task="binary")
            log_accuracy += accuracy(pred_reach, r.int())
            f1 = F1Score(task="binary")
            log_f1 += f1(pred_reach, r.int())

        log_loss /= len(loader)
        log_precision /= len(loader)
        log_recall /= len(loader)
        log_accuracy /= len(loader)
        log_f1 /= len(loader)

        writer.add_scalar("Accuracy/" + title, log_accuracy, epoch)
        writer.add_scalar("Precision/" + title, log_precision, epoch)
        writer.add_scalar("Recall/" + title, log_recall, epoch)
        writer.add_scalar("Loss/" + title, log_loss, epoch)
        writer.add_scalar("Fscore/" + title, log_f1, epoch)


def train_multiframedst(nets, net_opts, dataset, global_args):
    """ Train the model on a multiframe dataset. """
    (
        model_file,
        resume,
        batch_size,
        samples_per_epoch,
        max_epochs,
        lr_decay_epoch,
        lr_decay_rate,
        n_dataset_worker,
        train_device,
        log_interval,
        save_interval,
        n_frame,
        model_variant
    ) = [global_args[_] for _ in ['model_file',
                                  'resume',
                                  'batch_size',
                                  'samples_per_epoch',
                                  'max_epochs',
                                  'lr_decay_epoch',
                                  'lr_decay_rate',
                                  'n_dataset_worker',
                                  'train_device',
                                  'log_interval',
                                  'save_interval',
                                  'n_frame',
                                  'model_variant']]

    # For Tensorboard: log the runs
    writer = SummaryWriter()

    epoch = 0

    # Resume: load weights and continue training
    if resume:
        epoch = _load_weights(model_file, nets, net_opts)
        torch.manual_seed(231239 + epoch)
        print('loaded saved state. epoch: %d' % epoch)

    # This is a direct copy of rmp_nav
    # FIXME: hack to mitigate the bug in torch 1.1.0's schedulers
    if epoch <= 1:
        last_epoch = epoch - 1
    else:
        last_epoch = epoch - 2

    # Scheduler: takes care of learning rate decay
    net_scheds = {
        name: torch.optim.lr_scheduler.StepLR(
            opt,
            step_size=lr_decay_epoch,
            gamma=lr_decay_rate,
            last_epoch=last_epoch)
        for name, opt in net_opts.items()
    }

    n_samples = samples_per_epoch

    # Splitting the Dataset into Train/Validation:
    train_size = int(0.8 * len(dataset))
    valid_size = len(dataset) - train_size
    train_dataset, valid_dataset = torch.utils.data.random_split(dataset, [train_size, valid_size])

    while True:
        print('===== epoch %d =====' % epoch)

        sampler = RandomSampler(train_dataset, True, n_samples)

        loader = DataLoader(train_dataset,
                            batch_size=batch_size,
                            sampler=sampler,
                            num_workers=n_dataset_worker,
                            pin_memory=True,
                            drop_last=True)

        last_log_time = time.time()

        for idx, (batch_src_imgs, batch_dst_imgs, batch_reachability, batch_vector, _, _) in enumerate(loader):

            # Zeros optimizer gradient
            for _, opt in net_opts.items():
                opt.zero_grad()

            # Get predictions
            src_img = batch_src_imgs.to(device=train_device, non_blocking=True)
            dst_imgs = batch_dst_imgs.to(device=train_device, non_blocking=True)
            r = batch_reachability.to(device=train_device, non_blocking=True)

            src_batch = src_img.float()
            dst_batch = dst_imgs.float()
            batch_size, win_size, c, h, w = dst_batch.size()

            if model_variant == "the_only_variant":
                assert dst_batch.size(1) == n_frame
                src_batch2 = src_batch.unsqueeze(1).expand_as(dst_batch).contiguous()

                # Extract features
                pair_features = nets['img_encoder'](
                    src_batch2.view(batch_size * win_size, c, h, w),
                    dst_batch.view(batch_size * win_size, c, h, w).view(batch_size, -1))

                # Get prediction
                pred_reach_logits = nets['reachability_regressor'](pair_features)

            elif model_variant == "pair_conv":
                assert dst_batch.size(1) == n_frame
                src_batch2 = src_batch.unsqueeze(1).expand_as(dst_batch).contiguous()

                # Extract features
                pair_features = nets['img_encoder'](
                    src_batch2.view(batch_size * win_size, c, h, w),
                    dst_batch.view(batch_size * win_size, c, h, w)).view(batch_size, win_size, -1)

                # Convolutional Layer
                conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

                # Get prediction
                pred_reach_logits = nets['reachability_regressor'](conv_feature)

            elif model_variant == "with_dist":
                assert dst_batch.size(1) == n_frame
                src_batch2 = src_batch.unsqueeze(1).expand_as(dst_batch).contiguous()

                # Extract features
                pair_features = nets['img_encoder'](
                    src_batch2.view(batch_size * win_size, c, h, w),
                    dst_batch.view(batch_size * win_size, c, h, w)).view(batch_size, win_size, -1)

                # Convolutional Layer
                conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

                # Get prediction
                pred_reach_logits = nets['reachability_regressor'](torch.cat((batch_vector, conv_feature), 1))



            else:
                print("This variant does not exist")
                sys.exit(0)

            # Loss
            loss = torch.nn.functional.binary_cross_entropy_with_logits(pred_reach_logits.squeeze(1), r)
            # print("bce",loss.item())

            # backwards gradient
            loss.backward()

            # optimizer step
            for _, opt in net_opts.items():
                opt.step()

            # Logging the run
            if idx % log_interval == 0:
                print('epoch %d batch time %.2f sec loss: %6.2f' % (
                    epoch, (time.time() - last_log_time) / log_interval, loss.item()))
                print('learning rate:\n%s' % tabulate.tabulate([
                    (name, opt.param_groups[0]['lr']) for name, opt in net_opts.items()]))
                for name, net in nets.items():
                    print('%s grad:\n%s' % (name, module_grad_stats(net)))

                # writer.add_scalar("Loss/train",loss, epoch*n_samples+idx*batch_size)
                last_log_time = time.time()

        # learning rate decay
        for _, sched in net_scheds.items():
            sched.step()

        # Validation
        valid_loader = DataLoader(valid_dataset,
                                  batch_size=batch_size,
                                  num_workers=n_dataset_worker)

        # log performance on the validation set
        tensor_log("Validation", valid_loader, train_device, model_variant, n_frame, writer, epoch, nets)

        training_loader = DataLoader(train_dataset,
                                     batch_size=batch_size,
                                     num_workers=n_dataset_worker)

        # log performance on the training set
        tensor_log("Training", training_loader, train_device, model_variant, n_frame, writer, epoch, nets, net_opts)

        epoch += 1
        if epoch > max_epochs:
            writer.flush()
            break

        if epoch % save_interval == 0:
            print('saving model...')
            writer.flush()
            _save_model(nets, net_opts, epoch, global_args, model_file)


if __name__ == '__main__':

    """ Train or test models for the reachability estimator

        Model Variants:
        -  "pair_conv": model as described in the paper
        -  "the_only_variant": model without added convolutional layer
        -  "with_dist": like "pair_conv", but adds the decoded goal_vector

    """

    global_args = {
        'model_file': os.path.join(os.path.dirname(__file__), "../data/models/trained_model"),
        'resume': False,
        'batch_size': 64,
        'samples_per_epoch': 10000,
        'max_epochs': 30,
        'lr_decay_epoch': 1,
        'lr_decay_rate': 0.7,
        'n_dataset_worker': 24,
        'n_frame': 10,
        'log_interval': 20,
        'save_interval': 5,
        'model_variant': "pair_conv",  # "pair_conv",#"with_dist",#"the_only_variant",
        'train_device': "cpu"
    }

    # Defining the NN and optimizers
    nets = {}
    if global_args["model_variant"] == "pair_conv":
        input_dim = 512 * global_args["n_frame"]
    elif global_args["model_variant"] == "with_dist":
        input_dim = 512 * global_args["n_frame"] + 2
    else:
        input_dim = 5120
    net = networks.ReachabilityRegressor(init_scale=1.0, input_dim=input_dim, no_weight_init=False)
    nets["reachability_regressor"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = networks.ConvEncoder(init_scale=1.0, input_dim=512, no_weight_init=False)
    nets["conv_encoder"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = networks.ImagePairEncoderV2(init_scale=1.0)
    nets["img_encoder"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    testing = True

    if testing:
        # Testing
        hd5file = "reachability_dataset_testset.hd5"
        directory = get_path()
        directory = os.path.join(directory, "data/reachability")
        filepath = os.path.join(directory, hd5file)
        filepath = os.path.realpath(filepath)

        dataset = H5Dataset(filepath)

        test_dst(dataset)

    else:
        # Training
        hd5file = "reachability_train.hd5"

        directory = get_path()
        directory = os.path.join(directory, "data/reachability")
        filepath = os.path.join(directory, hd5file)
        filepath = os.path.realpath(filepath)

        dataset = H5Dataset(filepath, external_link=True)

        train_multiframedst(
            nets={
                name: spec['net'] for name, spec in nets.items()
            },
            net_opts={
                name: spec['opt'] for name, spec in nets.items()
            },
            dataset=dataset,
            global_args=global_args)
