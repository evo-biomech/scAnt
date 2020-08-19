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


def get_approx_cam_pos(X_ang, Y_ang, r):
    scanner_positions = [[], [], []]
    scanner_orientations = [[], [], []]

    for x in X_ang:
        for y in Y_ang:
            P_x = r * math.sin(math.pi / 2 - x + (193 / 1600 * 2 * math.pi)) * math.cos(y)
            P_y = r * math.sin(math.pi / 2 - x + (193 / 1600 * 2 * math.pi)) * math.sin(y)
            P_z = r * math.cos(math.pi / 2 - x + (193 / 1600 * 2 * math.pi))

            scanner_orientations[0].append(-P_x / 4)
            scanner_orientations[1].append(-P_y / 4)
            scanner_orientations[2].append(-P_z / 4)

            scanner_positions[0].append(P_x)
            scanner_positions[1].append(P_y)
            scanner_positions[2].append(P_z)

    return scanner_positions, scanner_orientations


def create_transformation_matrix(px, py, pz, alpha, beta, gamma):
    """
    outputs transformation matrix given the translation and rotation of an input frame of reference using the Euler
    Z-Y-X Rotation with the following convention for applied angles (right handed coord system):
    alpha: rotation around z-axis
    beta: rotation around y-axis
    gamma: rotation around x-axis
    returns 4x4 transformation matrix
    """

    Rxx = math.cos(alpha) * math.cos(beta)
    Ryx = math.cos(alpha) * math.sin(beta) * math.sin(gamma) - math.cos(gamma) * math.sin(alpha)
    Rzx = math.sin(alpha) * math.sin(gamma) + math.cos(alpha) * math.cos(gamma) * math.sin(beta)

    Rxy = math.cos(beta) * math.sin(alpha)
    Ryy = math.cos(alpha) * math.cos(gamma) + math.sin(alpha) * math.sin(beta) * math.sin(gamma)
    Rzy = math.cos(gamma) * math.sin(alpha) * math.sin(beta) - math.cos(alpha) * math.sin(gamma)

    Rxz = - math.sin(beta)
    Ryz = math.cos(beta) * math.sin(gamma)
    Rzz = math.cos(beta) * math.cos(gamma)

    Trans_Mat = [[Rxx, Ryx, Rzx, px],
                 [Rxy, Ryy, Rzy, py],
                 [Rxz, Ryz, Rzz, pz],
                 [0, 0, 0, 1]]

    return np.array(Trans_Mat)


if __name__ == '__main__':
    config = read_config_file(path=Path.cwd().parent.joinpath("example_config.yaml"))
    print(config["scanner_settings"])
    X, Y, Z = create_input_arrays(config)

    X_ang = convert_to_angles(X, inc_per_rot=1600)  # as the initial angle is view from below
    Y_ang = convert_to_angles(Y, inc_per_rot=1600)

    # max Z -> 40,000 at ~ 25 cm sensor to centre
    # min Z ->      0 at ~ 15 cm sensor to centre
    # measured 40,000 tics = ~ 10 cm +/- 0.1 cm

    # distance_tic -> convert to distance in meters to use as constant radius

    corrected_Z = (((Z[0] * (-1)) / 40000) * 10 + 15) / 100
    print(corrected_Z)

    scanner_positions, scanner_orientations = get_approx_cam_pos(X_ang=X_ang, Y_ang=Y_ang, r=corrected_Z)

    # compute transformation matrix
    trans_mat_start = create_transformation_matrix(px=scanner_positions[0][0],
                                                   py=scanner_positions[1][0],
                                                   pz=scanner_positions[2][0],
                                                   alpha=-Y_ang[0] + math.pi,
                                                   beta=0,
                                                   gamma=X_ang[0] - (193 / 1600 * 2 * math.pi))

    print(trans_mat_start)

    # Matplotlib solution
    fig = plt.figure()
    ax = Axes3D(fig)

    # create 3D plot
    ax = plt.axes(projection='3d')

    # mark every camera position
    ax.scatter(scanner_positions[0][1:], scanner_positions[1][1:], scanner_positions[2][1:], depthshade=True,
               label="all camera positions")

    # mark every camera orientation
    ax.quiver(scanner_positions[0][1:], scanner_positions[1][1:], scanner_positions[2][1:],
              scanner_orientations[0][1:], scanner_orientations[1][1:], scanner_orientations[2][1:], alpha=0.4)

    # place marker of scanned object in the centre
    ax.scatter(0, 0, 0, s=30, c="black", depthshade=True, marker="h", label="scanned subject")

    # mark initial orientation
    ax.scatter(scanner_positions[0][0], scanner_positions[1][0], scanner_positions[2][0], depthshade=True,
               s=30, c="red", label="initial camera position")
    ax.quiver(scanner_positions[0][0], scanner_positions[1][0], scanner_positions[2][0],
              scanner_orientations[0][0], scanner_orientations[1][0], scanner_orientations[2][0], alpha=0.4,
              color="red")

    ax.set_xlim3d(-0.3, 0.3)
    ax.set_ylim3d(-0.3, 0.3)
    ax.set_zlim3d(-0.22, 0.22)

    ax.set_xlabel('$X$')
    ax.set_ylabel('$Y$')
    ax.set_zlabel('$Z$')

    ax.legend(loc='upper left', bbox_to_anchor=(0.65, 1.05))

    plt.show()
