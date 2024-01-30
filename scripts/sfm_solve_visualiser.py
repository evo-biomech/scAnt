import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from estimate_camera_positions import *


def read_cameras_from_sfm_solve(solve_file):
    with open(solve_file) as sf:
        solve_json = json.load(sf)

    poses_dict = solve_json["poses"]
    centers = [i["pose"]["transform"]["center"] for i in poses_dict]
    centers_fl = np.array(centers, np.float)
    return centers_fl


if __name__ == '__main__':
    file = "J:\\Meshroom-2023.3.0\\Amphipyra_Tests_360\\MeshroomCache\\" \
           "StructureFromMotion\\121bb81ac0be265bcf0a48abde410c8c614443de\\cameras.sfm"

    centers = read_cameras_from_sfm_solve(solve_file=file)

    # Matplotlib solution
    fig = plt.figure()
    ax = Axes3D(fig)

    # create 3D plot
    ax = plt.axes(projection='3d')

    # mark every camera position
    ax.scatter(centers[:, 0],
               centers[:, 1],
               centers[:, 2], depthshade=True,
               c="pink",
               label="all camera positions")

    # place marker of scanned object in the centre
    ax.scatter(0, 0, 0, s=30, c="black", depthshade=True, marker="h", label="0 position")

    ax.set_xlim3d(-1, 1)
    ax.set_ylim3d(-1, 1)
    ax.set_zlim3d(-1, 1)

    ax.set_xlabel('$X$')
    ax.set_ylabel('$Y$')
    ax.set_zlabel('$Z$')

    ax.legend(loc='upper left', bbox_to_anchor=(0.65, 1.05))

    plt.show()
