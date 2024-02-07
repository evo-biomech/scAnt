import json
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from estimate_camera_positions import *
import numpy as np
import pytransform3d.camera as pc
import pytransform3d.transformations as pt
import pytransform3d.visualizer as pv
import open3d


def read_cameras_from_sfm_solve(solve_file):
    with open(solve_file) as sf:
        solve_json = json.load(sf)

    poses_dict = solve_json["poses"]
    centers = [i["pose"]["transform"]["center"] for i in poses_dict]
    rotations = [i["pose"]["transform"]["rotation"] for i in poses_dict]
    intrinsics = solve_json["intrinsics"][0]
    centers_fl = np.array(centers, np.float)
    rotations_fl = np.array(rotations, np.float)
    return centers_fl, rotations_fl, intrinsics


if __name__ == '__main__':
    camera_filenames = ["cameras_REF.sfm"]

    fig = pv.figure()

    for camera_filename in camera_filenames:

        with open(camera_filename, "r") as f:
            cameras = json.load(f)

        camera_poses = cameras["poses"]
        camera_intrinsics = cameras["intrinsics"][0]

        px_focal_length = float(camera_intrinsics["focalLength"])
        sensorWidth = float(camera_intrinsics["sensorWidth"])
        sensorHeight = float(camera_intrinsics["sensorHeight"])

        M = np.array([
            [px_focal_length, 0, sensorWidth / 2.0],
            [0, px_focal_length, sensorHeight / 2.0],
            [0, 0, 1]
        ])

        sensor_size = (float(sensorWidth), float(sensorHeight))

        transformation_matrices = np.empty((len(camera_poses), 4, 4))

        ids = []  # image IDs

        for i, camera_pose in enumerate(camera_poses):
            R = np.array(list(map(float, camera_pose["pose"]["transform"]["rotation"]))).reshape(3, 3)
            p = np.array(list(map(float, camera_pose["pose"]["transform"]["center"])))
            poseId = camera_pose["poseId"]
            for view in cameras["views"]:
                if view["poseId"] == poseId:
                    ids.append(view["path"].split("\\")[-1])

            transformation_matrices[i] = pt.transform_from(R=R, p=p)

        num_pose = 0

        for pose, img in zip(transformation_matrices, ids):
            fig.plot_transform(A2B=pose, s=0.05)
            fig.plot_camera(M=M, cam2world=pose, virtual_image_distance=0.1, sensor_size=sensor_size)

            print(num_pose, img)
            num_pose += 1

    # world origin
    fig.plot_transform(pt.transform_from(R=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], p=[0, 0, 0]), s=0.25)
    fig.show()
