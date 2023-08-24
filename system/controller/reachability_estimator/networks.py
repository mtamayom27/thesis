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


def initializeCNN(model_variant='pair_conv'):

    # Defining the NN and optimizers
    nets = {}
    if model_variant == "pair_conv":
        input_dim = 512
    elif model_variant == "with_dist":
        input_dim = 512 + 3
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
    return nets


def initializeResNet(model_variant='pair_conv'):
    # Defining the NN and optimizers
    nets = {}
    if model_variant == "pair_conv":
        input_dim = 512
    elif model_variant == "with_dist":
        input_dim = 512 + 3
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

    net = FcWithDropout(init_scale=1.0, input_dim=input_dim, no_weight_init=False)
    nets["fully_connected"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }

    net = torchvision.models.resnext101_64x4d(pretrained=True)
    nets["res_net"] = {
        'net': net,
        'opt': torch.optim.Adam(net.parameters(), lr=3.0e-4, eps=1.0e-5)
    }
    return nets


def initialize_network(backbone='convolutional', model_variant='pair_conv'):
    if backbone == 'convolutional':
        return initializeCNN(model_variant)
    elif backbone == 'res_net':
        return initializeResNet(model_variant)
    else:
        raise ValueError("Backbone not implemented")


def get_prediction_convolutional(nets, model_variant, src_batch, dst_batch, batch_transformation=None):
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
        sys.exit(0)
    return reachability_prediction, position_prediction, angle_prediction


def get_prediction_resnet(nets, model_variant, src_batch, dst_batch):
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
        print("This variant does not exist")
        sys.exit(0)
    return reachability_prediction, position_prediction, angle_prediction


def get_prediction(nets, backbone, model_variant, src_batch, dst_batch, batch_transformation=None):
    if backbone == 'convolutional':
        return get_prediction_convolutional(nets, model_variant, src_batch, dst_batch, batch_transformation)
    elif backbone == 'res_net':
        return get_prediction_resnet(nets, model_variant, src_batch, dst_batch)


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
    def __init__(self, input_dim=512, init_scale=1.0, bias=True, no_weight_init=False):
        super(FcWithDropout, self).__init__()

        self.fc1 = nn.Linear(input_dim, input_dim, bias=bias)
        self.dropout1 = nn.Dropout(inplace=True)
        self.fc2 = nn.Linear(input_dim, input_dim // 4, bias=bias)
        self.dropout2 = nn.Dropout(inplace=True)
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