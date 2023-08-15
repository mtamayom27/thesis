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
from torch import nn
import torch.nn.functional as F


class ReachabilityRegressor(nn.Module):
    def __init__(self, input_dim=512, init_scale=1.0, bias=True, no_weight_init=False):
        super(ReachabilityRegressor, self).__init__()

        self.fc1 = nn.Linear(input_dim, input_dim // 2, bias=bias)
        self.fc2 = nn.Linear(input_dim // 2, input_dim // 2, bias=bias)
        self.fc3 = nn.Linear(input_dim // 2, 1, bias=bias)

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
        # Output are logits. Need to apply sigmoid to get values in (0, 1)
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