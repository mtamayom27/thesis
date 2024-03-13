""" This code has been adapted from:
***************************************************************************************
*    Title: "Neurobiologically Inspired Navigation for Artificial Agents"
*    Author: "Johanna Latzel"
*    Date: 12.03.2024
*    Availability: https://nextcloud.in.tum.de/index.php/s/6wHp327bLZcmXmR
*
***************************************************************************************
"""
import networkx as nx

from plotThesis import *
import matplotlib.pyplot as plt
import tensorflow as tf

from system.bio_model.cognitive_map import LifelongCognitiveMap
from system.bio_model.place_cell_model import PlaceCellNetwork
from system.controller.local_controller.decoder.phase_offset_detector import PhaseOffsetDetectorNetwork
from system.controller.local_controller.local_navigation import setup_gc_network
from system.controller.reachability_estimator.reachability_estimation import reachability_estimator_factory
from system.controller.simulation.environment.map_occupancy import MapLayout
from system.controller.simulation.pybullet_environment import PybulletEnvironment
from system.controller.topological.topological_navigation import TopologicalNavigation
from system.controller.simulation.environment.map_occupancy_helpers.map_visualizer import OccupancyMapVisualizer


def plt_grid_cell_decoder():
    model = "combo/"# combo_return/"#"combo_radius_2/"#"combo/" # "pod/" # "linear_lookahead/"  # "spike_detection/", "linear_lookahead/", "phase_offset_detector/"

    errors = np.load("experiments/" + model + "error_array" + ".npy")
    times = np.load("experiments/" + model + "time_array" + ".npy")

    errors_evaluate = errors
    actual_errors_evaluate = np.load("experiments/" + model + "actual_error_array" + ".npy")
    actual_errors_goal_evaluate = np.load("experiments/" + model + "actual_error_goal_array" + ".npy")

    filter_threshold = 20#0.5
    delete = np.where(errors_evaluate < filter_threshold, False, True)
    errors_evaluate = np.delete(errors_evaluate, delete)

    plot_vector_navigation_error(errors_evaluate)
    plot_vector_navigation_error(actual_errors_evaluate)
    plot_vector_navigation_error(actual_errors_goal_evaluate)

    print(times.mean())


def merge_tfrecord_files(file1, file2, output_file):
    with tf.io.TFRecordWriter(output_file) as writer:
        # Read and write data from the first file
        for record in tf.data.TFRecordDataset(file1):
            writer.write(record.numpy())

        # Read and write data from the second file
        for record in tf.data.TFRecordDataset(file2):
            writer.write(record.numpy())


def truncate_tfrecord_file(input_file, output_file, max_epoch=30):
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with tf.io.TFRecordWriter(output_file) as writer:
        for raw_record in tf.data.TFRecordDataset(input_file):
            event = tf.compat.v1.Event.FromString(raw_record.numpy())

            # Filter based on step
            if hasattr(event, 'step') and event.step <= 30:
                writer.write(raw_record.numpy())

# for file in files:
#     truncate_tfrecord_file(dir_path + file, dir_path + 'new_' + file)

# merge_tfrecord_files('Resnet1_copy/events.out.tfevents.1693242628.ip-192-168-178-39.eu-west-1.compute.internal.26772.0', '/Users/anna/Documents/TUM/Thesis/bio-inspired-navigation/system/controller/reachability_estimator/training/runs/runs/resnet2_copy/events.out.tfevents.1693256548.ip-192-168-178-39.eu-west-1.compute.internal.51778.0', '/Users/anna/Documents/TUM/Thesis/bio-inspired-navigation/system/controller/reachability_estimator/training/runs/runs/resnet3/events.out.tfevents.1693256548.ip-192-168-178-39.eu-west-1.compute.internal.51778.0')

def create_re_plots():

    labels = {
        'MSE': 'CNN backbone(RGBD) + MSE(Grid cell spikings)',
        'Resnet': 'ResNet backbone(RGBD)',
        'RGBD': 'CNN backbone(RGBD)',
        'Sieamese': 'CNN backbone(RGBD) + Siamese CNN(Grid cell spikings)',
        'Simple': 'CNN backbone(RGB)',
        'SSIM': 'CNN backbone(RGBD) + SSIM(Grid cell spikings)'
    }

    def plot_tensorboard_data(log_files, tag):
        if tag == 'Fscore/Validation':
            plt.figure(figsize=(10, 7))
        else:
            plt.figure(figsize=(10, 6))
        fontdict = {'size': 22}
        for log_file in log_files:
            steps = []
            values = []

            # Read the TensorBoard log file
            for record in tf.data.TFRecordDataset(log_file):
                event = tf.compat.v1.Event.FromString(record.numpy())

                # Check for scalar events with the specified tag
                for value in event.summary.value:
                    if value.tag == tag:
                        steps.append(event.step)
                        values.append(value.simple_value)

            # Plotting for each file
            plt.plot(steps, values, label=labels[log_file.split('/')[-2][4:]])  # Using file name as label

        # Adding grid
        plt.grid(True)

        # Final plot adjustments
        plt.xlabel('Epochs', fontdict=fontdict)
        plt.ylabel('Value', fontdict=fontdict)
        plt.tick_params(axis='both', which='major', labelsize=18)  # You can adjust the size as needed

        title = tag.split('/')[0]
        if title == 'Fscore':
            title = 'F-score'
        plt.title(title, fontdict={'size': 26 if tag == 'Fscore/Validation' else 30})
        # Adding legend
        # plt.legend(fontsize=16)  # Increase legend font size
        if tag == 'Fscore/Validation':
            plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=16)

        # Adjust layout to make space for the legend
        plt.tight_layout(rect=[0, 0.1, 1, 1])
        plt.savefig(tag.split('/')[0] + '.png', format="png")
        plt.show()


    dir_path = '/Users/anna/Documents/TUM/Thesis/bio-inspired-navigation/system/controller/reachability_estimator/training/runs/runs/'
    files = [
        'Simple/events.out.tfevents.1692343246.ip-192-168-178-39.eu-west-1.compute.internal.37247.0',
        'RGBD/events.out.tfevents.1692965749.ip-192-168-178-39.eu-west-1.compute.internal.27676.0',
        'Resnet/events.out.tfevents.1693256548.ip-192-168-178-39.eu-west-1.compute.internal.51778.0',
        'Sieamese/events.out.tfevents.1694116961.tp2-MS-7D15.106935.0',
        'SSIM/events.out.tfevents.1695815067.tp2-MS-7D15.89325.0',
        'MSE/events.out.tfevents.1696836371.tp2-MS-7D15.3149.0'
    ]
    tags = ['Accuracy/Validation', 'Fscore/Validation', 'Loss/Validation', 'Precision/Validation', 'Recall/Validation']
    # for tag in tags:
    [plot_tensorboard_data([dir_path + 'new_' + file for file in files], tag) for tag in tags]


def create_exploration():

    # get the path through the environment
    env_model = "Savinov_val3"
    mapLayout = MapLayout(env_model)
    path = [
            [-2, 0], [-6, -2.5], [-4, 0.5], [-6.5, 0.5], [-7.5, -2.5], [-2, -1.5], [1, -1.5],
            [0.5, 1.5], [2.5, -1.5], [1.5, 0], [5, -1.5],
            [4.5, -0.5], [-0.5, 0], [-8.5, 3], [-8.5, -4],
            [-7.5, -3.5], [1.5, -3.5], [-6, -2.5]
        ]
    goals = []
    for i in range(len(path) - 1):
        new_wp = mapLayout.find_path(path[i], path[i + 1])
        if new_wp is None:
            raise ValueError("No path found!")
        goals += new_wp

    # see cognitive_map.py
    creation_re_type = "firing"
    connection_re_type = "neural_network"
    weights_file = "re_mse_weights.50"
    cognitive_map_filename = "after_exploration.gpickle"

    re = reachability_estimator_factory(connection_re_type, weights_file=weights_file, env_model=env_model,
                                        with_spikings=True)
    pc_network = PlaceCellNetwork(from_data=True, reach_estimator=re)
    cognitive_map = LifelongCognitiveMap(reachability_estimator=re, load_data_from=cognitive_map_filename)
    gc_network = setup_gc_network(1e-2)
    pod = PhaseOffsetDetectorNetwork(16, 9, 40)

    tj = TopologicalNavigation(env_model, "combo", pc_network, cognitive_map, gc_network, pod)

    G = tj.cognitive_map.node_network.to_undirected()
    S = [G] + [G.subgraph(c).copy() for c in sorted(nx.connected_components(G), key=len, reverse=True)]
    for s in S:
        tj.cognitive_map.node_network = s

        # draw the path
        fig, ax = plt.subplots(1, 1)
        im = plt.imshow([[1, 2], [3, 4]])
        fig.canvas.draw()
        ax.draw_artist(im)
        vis = OccupancyMapVisualizer(mapLayout, ax)
        vis.draw_map()
        for i in range(len(path) - 1):
            waypoints = mapLayout.find_path(path[i], path[i + 1])
            if waypoints:
                x, y = np.array(waypoints).T
                plt.scatter(x, y, c='#FFD58040')

        dt = 1e-2
        env = PybulletEnvironment(False, dt, env_model, "analytical", build_data_set=True)

        G = tj.cognitive_map.node_network
        pos = nx.get_node_attributes(G, 'pos')
        # nx.draw(G,pos,node_color='#0065BD',node_size=10)
        G = G.to_undirected()
        nx.draw_networkx_nodes(G, pos, node_color='#0065BD70', node_size=40)
        nx.draw_networkx_edges(G, pos, edge_color='#99999980')

        # add_environment(ax, env)
        plt.axis("off")
        plt.show()

create_exploration()