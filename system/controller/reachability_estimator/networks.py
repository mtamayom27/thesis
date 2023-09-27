''' This code has been adapted from:
***************************************************************************************
*    Title: "Scaling Local Control to Large Scale Topological Navigation"
*    Author: "Xiangyun Meng, Nathan Ratliff, Yu Xiang and Dieter Fox"
*    Date: 2020
*    Availability: https://github.com/xymeng/rmp_nav
*
***************************************************************************************
'''
import math

import torch
import torchvision
from torch import nn
import torch.nn.functional as F
from torch.autograd import Variable


def initialize_siamese(model='spikings'):
    nets = {}

    net = GridCellNetwork()
    nets["grid_cell_network"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-3, eps=1.0e-5)
    }

    return nets


def initialize_cnn(model_variant='pair_conv'):

    # Defining the NN and optimizers
    nets = {}
    if model_variant == "pair_conv":
        input_dim = 512
    elif model_variant == "with_dist":
        input_dim = 512 + 3
    elif model_variant == 'spikings':
        input_dim = 512 + 1
    else:
        input_dim = 5120

    net = AngleRegression(init_scale=1.0, no_weight_init=False)
    nets["angle_regression"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = PositionRegression(init_scale=1.0, no_weight_init=False)
    nets["position_regression"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = ReachabilityRegression(init_scale=1.0, no_weight_init=False)
    nets["reachability_regression"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = FCLayers(init_scale=1.0, input_dim=input_dim, no_weight_init=False)
    nets["fully_connected"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = ConvEncoder(init_scale=1.0, input_dim=512, no_weight_init=False)
    nets["conv_encoder"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = ImagePairEncoderV2(init_scale=1.0)
    nets["img_encoder"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    if model_variant == 'spikings':
        net = SiameseNetwork()
        nets["spikings_encoder"] = {
            'net': net,
            'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
        }

    return nets


def initialize_res_net(model_variant='pair_conv'):
    # Defining the NN and optimizers
    nets = {}
    input_dim = 64

    net = AngleRegression(init_scale=1.0, no_weight_init=False)
    nets["angle_regression"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = PositionRegression(init_scale=1.0, no_weight_init=False)
    nets["position_regression"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = ReachabilityRegression(init_scale=1.0, no_weight_init=False)
    nets["reachability_regression"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = FcWithDropout(init_scale=1.0, input_dim=input_dim * 2, no_weight_init=False)
    nets["fully_connected"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = torchvision.models.resnet18(pretrained=True, num_classes=input_dim)
    weight1 = net.conv1.weight.clone()
    new_first_layer = nn.Conv2d(4, 64, kernel_size=(7, 7), stride=(2, 2), padding=(3, 3), bias=False).requires_grad_()
    new_first_layer.weight[:, :3, :, :].data[...] = Variable(weight1, requires_grad=True)
    net.conv1 = new_first_layer

    nets["res_net"] = {
        'net': net,
        'opt': None
    }
    return nets


def initialize_network(backbone='convolutional', model_variant='pair_conv'):
    if backbone == 'convolutional':
        return initialize_cnn(model_variant)
    elif backbone == 'res_net':
        return initialize_res_net(model_variant)
    elif backbone == 'grid_cell':
        return initialize_siamese(model_variant)
    else:
        raise ValueError("Backbone not implemented")


from torchmetrics.image import StructuralSimilarityIndexMeasure

compare_ssim = StructuralSimilarityIndexMeasure(data_range=1.0, reduction='none')

module_weights = torch.FloatTensor([6, 5, 4, 3, 2, 1])


def get_grid_cell(batch_src_spikings, batch_dst_spikings):
    """
    Calculate the similarity between two arrays of grid cell modules using Structural Similarity Index (SSIM)
    with weighted aggregation.

    Args:
    array1 (list of numpy arrays): First array of grid cell modules.
    array2 (list of numpy arrays): Second array of grid cell modules.
    module_weights (list of float): List of weights for each module. Must have the same length as arrays.

    Returns:
    float: Weighted SSIM-based similarity score.
    """
    batch_similarity_scores = torch.zeros(6, 64)

    for ch in range(6):
        batch_similarity_scores[ch] = compare_ssim(batch_src_spikings[:, ch:ch + 1, :, :], batch_dst_spikings[:, ch:ch + 1, :, :])
    batch_similarity_scores = torch.FloatTensor(batch_similarity_scores)
    batch_similarity_scores = torch.transpose(batch_similarity_scores, 0, 1)
    batch_similarity_scores = (batch_similarity_scores * module_weights).sum(1) / module_weights.sum()
    batch_similarity_scores = (torch.max(batch_similarity_scores, torch.fill(torch.zeros((64,)), 0.99)) - 0.99) / 0.01
    return batch_similarity_scores


def get_prediction_convolutional(nets, model_variant, src_batch, dst_batch, batch_transformation, batch_src_spikings, batch_dst_spikings):
    batch_size, c, h, w = dst_batch.size()
    if model_variant == "the_only_variant":
        # Extract features
        pair_features = nets['img_encoder'](
            src_batch.view(batch_size, c, h, w),
            dst_batch.view(batch_size, c, h, w).view(batch_size, -1))

        # Get prediction
        linear_features = nets['fully_connected'](pair_features)
        reachability_prediction = nets["reachability_regression"](linear_features)
        position_prediction = nets["position_regression"](linear_features)
        angle_prediction = nets["angle_regression"](linear_features)
    elif model_variant == "pair_conv":
        # Extract features
        pair_features = nets['img_encoder'](
            src_batch.view(batch_size, c, h, w),
            dst_batch.view(batch_size, c, h, w)).view(batch_size, 1, -1)

        # Convolutional Layer
        conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

        # Get prediction
        linear_features = nets['fully_connected'](conv_feature)
        reachability_prediction = nets["reachability_regression"](linear_features)
        position_prediction = nets["position_regression"](linear_features)
        angle_prediction = nets["angle_regression"](linear_features)
    elif model_variant == 'spikings':
        # Extract features
        pair_features = nets['img_encoder'](
            src_batch.view(batch_size, c, h, w),
            dst_batch.view(batch_size, c, h, w)).view(batch_size, 1, -1)

        spikings_features = get_grid_cell(batch_src_spikings, batch_dst_spikings)

        # Convolutional Layer
        conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

        # Get prediction
        linear_features = nets['fully_connected'](torch.cat((conv_feature, spikings_features.unsqueeze(1)), 1))
        reachability_prediction = nets["reachability_regression"](linear_features)
        position_prediction = nets["position_regression"](linear_features)
        angle_prediction = nets["angle_regression"](linear_features)
    elif model_variant == "with_dist":
        # Extract features
        pair_features = nets['img_encoder'](
            src_batch.view(batch_size, c, h, w),
            dst_batch.view(batch_size, c, h, w)).view(batch_size, 1, -1)

        # Convolutional Layer
        conv_feature = nets['conv_encoder'](pair_features.transpose(1, 2))

        # Get prediction
        linear_features = nets['fully_connected'](torch.cat((batch_transformation, conv_feature), 1))
        reachability_prediction = nets["reachability_regression"](linear_features)
        position_prediction = nets["position_regression"](linear_features)
        angle_prediction = nets["angle_regression"](linear_features)
    else:
        print("This variant does not exist")
        return
    return reachability_prediction, position_prediction, angle_prediction


def get_prediction_resnet(nets, model_variant, src_batch, dst_batch, batch_src_spikings, batch_dst_spikings):
    batch_size, c, h, w = dst_batch.size()
    if model_variant == "the_only_variant":
        raise NotImplementedError
    elif model_variant == "pair_conv":
        # Extract features
        src_features = nets['res_net'](src_batch.view(batch_size, c, h, w))
        dst_features = nets['res_net'](dst_batch.view(batch_size, c, h, w))

        # Convolutional Layer
        pair_features = torch.cat([src_features, dst_features], dim=1)

        # Get prediction
        linear_features = nets['fully_connected'](pair_features)
        reachability_prediction = nets["reachability_regression"](linear_features)
        position_prediction = nets["position_regression"](linear_features)
        angle_prediction = nets["angle_regression"](linear_features)
    elif model_variant == "with_dist":
        raise NotImplementedError
    else:
        raise ValueError("This variant does not exist")
    return reachability_prediction, position_prediction, angle_prediction


def get_prediction(nets, backbone, model_variant, src_batch, dst_batch, batch_transformation=None, batch_src_spikings=None, batch_dst_spikings=None):
    if backbone == 'convolutional':
        return get_prediction_convolutional(nets, model_variant, src_batch, dst_batch, batch_transformation, batch_src_spikings, batch_dst_spikings)
    elif backbone == 'res_net':
        return get_prediction_resnet(nets, model_variant, src_batch, dst_batch, batch_src_spikings, batch_dst_spikings)
    elif backbone == 'grid_cell':
        return get_grid_cell(batch_src_spikings, batch_dst_spikings), None, None


class GridCellNetwork(nn.Module):
    def __init__(self, no_weight_init=False):
        super(GridCellNetwork, self).__init__()

        self.conv1 = nn.Conv2d(in_channels=6, out_channels=16, kernel_size=3, stride=1, padding=1)
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, stride=1, padding=1)
        self.relu2 = nn.ReLU()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Define fully connected layers
        self.fc1 = nn.Linear(64 * 10 * 10, 64)
        self.relu3 = nn.ReLU()
        self.fc2 = nn.Linear(64, 1)

        if not no_weight_init:
            for layer in (self.conv1, self.conv2, self.fc1, self.fc2):
                nn.init.orthogonal_(layer.weight, 1.0)
                if hasattr(layer, 'bias') and layer.bias is not None:
                    with torch.no_grad():
                        layer.bias.zero_()

    def forward(self, x1, x2):
        x1 = self.pool(self.relu1(self.conv1(x1)))
        x1 = self.pool(self.relu2(self.conv2(x1)))
        x1 = x1.view(-1, 32 * 10 * 10)

        # Forward pass for the second grid cell module
        x2 = self.pool(self.relu1(self.conv1(x2)))
        x2 = self.pool(self.relu2(self.conv2(x2)))
        x2 = x2.view(-1, 32 * 10 * 10)

        x = torch.cat((x1, x2), dim=1)
        x = self.relu3(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x.squeeze(1)


class AngleRegression(nn.Module):
    def __init__(self, init_scale=1.0, bias=True, no_weight_init=False):
        super(AngleRegression, self).__init__()

        self.fc = nn.Linear(4, 1, bias=bias)
        self.sigmoid = nn.Sigmoid()
        self.two_pi = nn.Parameter(torch.tensor(math.pi * 2).squeeze(0))
        self.pi = nn.Parameter(torch.tensor(math.pi).squeeze(0))

        if not no_weight_init:
            nn.init.orthogonal_(self.fc.weight, init_scale)
            if hasattr(self.fc, 'bias') and self.fc.bias is not None:
                with torch.no_grad():
                    self.fc.bias.zero_()

    def forward(self, x):
        x = self.fc(x)
        x = self.sigmoid(x)
        x = x * self.two_pi - self.pi
        return x.squeeze(1)


class PositionRegression(nn.Module):
    def __init__(self, init_scale=1.0, bias=True, no_weight_init=False):
        super(PositionRegression, self).__init__()

        self.fc = nn.Linear(4, 2, bias=bias)

        if not no_weight_init:
            nn.init.orthogonal_(self.fc.weight, init_scale)
            if hasattr(self.fc, 'bias') and self.fc.bias is not None:
                with torch.no_grad():
                    self.fc.bias.zero_()

    def forward(self, x):
        x = self.fc(x)
        return x


class ReachabilityRegression(nn.Module):
    def __init__(self, init_scale=1.0, bias=True, no_weight_init=False):
        super(ReachabilityRegression, self).__init__()

        self.fc = nn.Linear(4, 1, bias=bias)
        self.sigmoid = nn.Sigmoid()

        if not no_weight_init:
            nn.init.orthogonal_(self.fc.weight, init_scale)
            if hasattr(self.fc, 'bias') and self.fc.bias is not None:
                with torch.no_grad():
                    self.fc.bias.zero_()

    def forward(self, x):
        x = self.fc(x)
        x = self.sigmoid(x)
        return x.squeeze(1)


class FcWithDropout(nn.Module):
    def __init__(self, input_dim=2000, init_scale=1.0, bias=True, no_weight_init=False):
        super(FcWithDropout, self).__init__()

        self.fc1 = nn.Linear(input_dim, input_dim, bias=bias)
        self.dropout1 = nn.Dropout()
        self.fc2 = nn.Linear(input_dim, input_dim // 4, bias=bias)
        self.dropout2 = nn.Dropout()
        self.fc3 = nn.Linear(input_dim // 4, input_dim // 4, bias=bias)
        self.fc4 = nn.Linear(input_dim // 4, 4, bias=bias)

        if not no_weight_init:
            for layer in (self.fc1, self.fc2, self.fc3):
                nn.init.orthogonal_(layer.weight, init_scale)
                if hasattr(layer, 'bias') and layer.bias is not None:
                    with torch.no_grad():
                        layer.bias.zero_()

    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout1(x)
        x = self.fc2(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc3(x)
        x = self.fc4(x)
        return x


class FCLayers(nn.Module):
    def __init__(self, input_dim=512, init_scale=1.0, bias=True, no_weight_init=False):
        super(FCLayers, self).__init__()

        self.fc1 = nn.Linear(input_dim, input_dim // 2, bias=bias)
        self.fc2 = nn.Linear(input_dim // 2, input_dim // 2, bias=bias)
        self.fc3 = nn.Linear(input_dim // 2, 4, bias=bias)

        if not no_weight_init:
            for layer in (self.fc1, self.fc2, self.fc3):
                nn.init.orthogonal_(layer.weight, init_scale)
                if hasattr(layer, 'bias') and layer.bias is not None:
                    with torch.no_grad():
                        layer.bias.zero_()

    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = self.fc2(x)
        x = F.relu(x)
        x = self.fc3(x)
        return x


class ImagePairEncoderV2(nn.Module):
    def __init__(self, init_scale=1.0, bias=True, no_weight_init=False):
        super(ImagePairEncoderV2, self).__init__()

        # Input: 12 x 64 x 64
        # img1, img2, img1 - img2 total 12 channels
        self.conv1 = nn.Conv2d(12, 64, kernel_size=5, stride=2, bias=bias)
        # 64 x 30 x 30
        self.conv2 = nn.Conv2d(64, 128, kernel_size=5, stride=2, bias=bias)
        # 128 x 13 x 13
        self.conv3 = nn.Conv2d(128, 256, kernel_size=5, stride=2, bias=bias)
        # 256 x 5 x 5
        self.conv4 = nn.Conv2d(256, 512, kernel_size=5, stride=1, bias=bias)
        # 512 x 1 x 1

        if not no_weight_init:
            for layer in (self.conv1, self.conv2, self.conv3, self.conv4):
                nn.init.orthogonal_(layer.weight, init_scale)

    def forward(self, src_imgs, dst_imgs):
        imgs = torch.cat([src_imgs, dst_imgs, src_imgs - dst_imgs], dim=1)
        x = F.relu(self.conv1(imgs))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = F.relu(self.conv4(x))
        return x.view(x.size(0), -1)


class SiameseNetwork(nn.Module):
    def __init__(self, init_scale=1.0, bias=True, no_weight_init=False):
        super(SiameseNetwork, self).__init__()

        self.conv1 = nn.Conv2d(6, 16, kernel_size=3, padding=1, bias=bias)
        self.pool1 = nn.MaxPool2d(2)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1, bias=bias)
        self.pool2 = nn.MaxPool2d(2)
        self.fc1 = nn.Linear(32 * 10 * 10, 128, bias=bias)
        self.pool3 = nn.MaxPool2d(2)
        self.fc2 = nn.Linear(128, 8, bias=bias)

        if not no_weight_init:
            for layer in (self.conv1, self.conv2, self.fc1, self.fc2):
                nn.init.orthogonal_(layer.weight, init_scale)
                if hasattr(layer, 'bias') and layer.bias is not None:
                    with torch.no_grad():
                        layer.bias.zero_()

    def forward_one(self, x):
        x = F.relu(self.conv1(x))
        x = self.pool1(x)
        x = F.relu(self.conv2(x))
        x = self.pool2(x)
        x = x.view(x.size()[0], -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

    def forward(self, input1, input2):
        embed1 = self.forward_one(input1)
        embed2 = self.forward_one(input2)
        return torch.cat([embed1, embed2, embed1 - embed2], dim=1)


class ConvEncoder(nn.Module):
    def __init__(self, input_dim=512, output_dim=512, kernel_size=1, init_scale=1.0,
                 no_weight_init=False):
        super(ConvEncoder, self).__init__()
        self.conv = nn.Conv1d(input_dim, output_dim, kernel_size=kernel_size)
        if not no_weight_init:
            for layer in (self.conv,):
                nn.init.orthogonal_(layer.weight, init_scale)
                with torch.no_grad():
                    layer.bias.zero_()

    def forward(self, x):
        # Input size: batch_size x feature_dim x seq_len
        x = self.conv(x)
        x = F.relu(x)
        return x.flatten(1)


class ImageEncoderV3(nn.Module):
    def __init__(self, output_dim=512, init_scale=1.0, residual_link=False):
        super(ImageEncoderV3, self).__init__()
        self.residual_link = residual_link

        # Input: 3 x 64 x 64
        self.conv1 = nn.Conv2d(3, output_dim // 8, kernel_size=5, stride=2)
        if residual_link:
            self.res_fc1 = nn.Conv2d(output_dim // 8, output_dim // 4, kernel_size=1, stride=2)

        # 30 x 30
        self.conv2 = nn.Conv2d(output_dim // 8, output_dim // 4, kernel_size=5, stride=2)
        if residual_link:
            self.res_fc2 = nn.Conv2d(output_dim // 4, output_dim // 2, kernel_size=1, stride=2)

        # 13 x 13
        self.conv3 = nn.Conv2d(output_dim // 4, output_dim // 2, kernel_size=5, stride=2)
        if residual_link:
            self.res_fc3 = nn.Conv2d(output_dim // 2, output_dim, kernel_size=1, stride=1)

        # 5 x 5
        self.conv4 = nn.Conv2d(output_dim // 2, output_dim, kernel_size=5, stride=1)
        # 1 x 1

        for layer in (self.conv1, self.conv2, self.conv3, self.conv4):
            nn.init.orthogonal_(layer.weight, init_scale)

    def forward(self, imgs):
        if self.residual_link:
            x = F.relu(self.conv1(imgs))
            x = F.relu(self.res_fc1(x[:, :, 2:-2, 2:-2]) + self.conv2(x))
            x = F.relu(self.res_fc2(x[:, :, 2:-2, 2:-2]) + self.conv3(x))
            x = F.relu(self.res_fc3(x[:, :, 2:-2, 2:-2]) + self.conv4(x))
        else:
            x = F.relu(self.conv1(imgs))
            x = F.relu(self.conv2(x))
            x = F.relu(self.conv3(x))
            x = F.relu(self.conv4(x))

        return x.view(x.size(0), -1)