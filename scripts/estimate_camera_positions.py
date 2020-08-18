from scripts.project_manager import read_config_file
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import numpy as np
import math


def create_input_arrays(config_file):
    config_XYZ = config_file["scanner_settings"]
    x_input = np.arange(start=config_XYZ["x_min"], stop=config_XYZ["x_max"] + config_XYZ["x_step"],
                        step=config_XYZ["x_step"])
    y_input = np.arange(start=config_XYZ["y_min"], stop=config_XYZ["y_max"], step=config_XYZ["y_step"])
    z_input = np.arange(start=config_XYZ["z_min"], stop=config_XYZ["z_max"], step=config_XYZ["z_step"])

    return x_input, y_input, z_input


def convert_to_angles(input_arr, inc_per_rot):
    # convert arrays to angle values (in radian)
    output_arr = (input_arr / inc_per_rot) * 2 * math.pi

    return output_arr


if __name__ == '__main__':
    config = read_config_file(path=Path.cwd().parent.joinpath("example_config.yaml"))
    print(config["scanner_settings"])
    X, Y, Z = create_input_arrays(config)

    X_ang = convert_to_angles(X, inc_per_rot=800)  # as the initial angle is view from below
    Y_ang = convert_to_angles(Y, inc_per_rot=1600)

    scanner_positions = []

    fig = plt.figure(figsize=(5, 5))
    ax = Axes3D(fig)

    for x in X_ang:
        for y in Y_ang:
            P_x = 0.2 * math.sin(math.pi / 2 - x + (190 / 800 * 2 * math.pi)) * math.cos(y)
            P_y = 0.2 * math.sin(math.pi / 2 - x + (190 / 800 * 2 * math.pi)) * math.sin(y)
            P_z = 0.2 * math.cos(math.pi / 2 - x + (190 / 800 * 2 * math.pi))
            scanner_positions.append([P_x, P_y, P_z])

            ax.scatter(P_x, P_y, P_z)

    plt.show()
