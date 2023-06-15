from plotThesis import *


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

plt_grid_cell_decoder()

