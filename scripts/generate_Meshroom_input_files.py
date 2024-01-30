from scripts.project_manager import read_config_file
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import numpy as np
import math
import os
import cv2
import json
from sfm_solve_visualiser import *


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
    trans_mats = []

    for x in X_ang[:-1]:
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

            trans_mats.append(create_transformation_matrix(px=scanner_positions[0][-1],
                                                           py=scanner_positions[1][-1],
                                                           pz=scanner_positions[2][-1],
                                                           alpha=-y + math.pi,
                                                           beta=0,
                                                           gamma=x - (193 / 1600 * 2 * math.pi)))

    return scanner_positions, scanner_orientations, trans_mats


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


def generate_sfm(project_location, use_cutouts=True, file_ending=".tif"):
    """
    Creates cameraInit.sfm, viewpoints.sfm, and cameras.sfm / cameras.json files based on the provided project file.
    These files are to be used with Alicevision Meshroom and (in this version) using a standard .json formatting
    :param project_location: string to project folder (NOT config file)
    :param use_cutouts: bool, if enabled image cutouts will be used as the input files. This option is given for the
    sake of completeness but technically obsolete as Meshroom now natively supports image masking.
    :param file_ending: string of file ending. Only change when using cutouts or images have been generated with DSLR
    instead of default FLIR machine vision cameras
    :return: None
    """
    for file in os.listdir(str(project_location)):
        if file.endswith(".yaml"):
            config = read_config_file(path=project_location.joinpath(file))
    try:
        X, Y, Z = create_input_arrays(config)
    except(UnboundLocalError):
        print("UnboundLocalError: No config file found at specified project location!")
        return

    image_list = []
    image_dir = project_location.joinpath("stacked")
    for img in os.listdir(str(image_dir)):
        if use_cutouts:
            if img[-10:-4] == "cutout":
                image_list.append(img)
        else:
            if img[-len(file_ending):] == file_ending:
                image_list.append(img)

    if len(image_list) == 0:
        print("ERROR: No suitable images found! Aborting process...")
        exit()
    else:
        print("INFO: Found", len(image_list), "viable images for SFM")

    # sort image_list alphabetically to maintain the same order
    image_list.sort()

    # get image dimensions of first image in loaded list
    image_example = cv2.imread(str(image_dir.joinpath(image_list[0])))
    image_dimensions = image_example.shape

    X_ang = convert_to_angles(X, inc_per_rot=1600)  # as the initial angle is view from below
    Y_ang = convert_to_angles(Y, inc_per_rot=1600)

    # max Z -> 40,000 at ~ 25 cm sensor to centre
    # min Z ->      0 at ~ 15 cm sensor to centre
    # measured 40,000 tics = ~ 10 cm +/- 0.1 cm

    # distance_tic -> convert to distance in meters to use as constant radius

    corrected_Z = (((Z[0] * (-1)) / 40000) * 10 + 15) / 100

    _, _, trans_mats = get_approx_cam_pos(X_ang=X_ang, Y_ang=Y_ang, r=corrected_Z)

    full_dict = {}

    """
    Define version and folders
    """

    full_dict["version"] = ["1", "2", "6"]
    full_dict["featuresFolders"] = []
    full_dict["matchesFolders"] = []

    full_dict["views"] = []
    full_dict["poses"] = []

    viewId = 10000000
    intrinsicId = 1000000000
    resectionId = 0
    locked = 0

    meshroom_img_path = str(project_location).replace("/", '\/')
    print(meshroom_img_path)

    """
    Enter all cameras and assign IDs to reference for each pose
    """

    for cam, trans_mat in enumerate(trans_mats):
        viewId += 1
        resectionId += 1

        views_temp = {"viewId": str(viewId),
                      "poseId": str(viewId),
                      "frameId": str(cam),
                      "intrinsicId": str(intrinsicId),
                      "resectionId": str(resectionId),
                      "path": str(os.path.join(meshroom_img_path, "stacked", image_list[cam])),
                      "width": str(image_dimensions[1]),
                      "height": str(image_dimensions[0]),
                      "metadata": {
                          "AliceVision:SensorWidth": "13.1",
                          "Exif:FocalLength": str(config["exif_data"]["FocalLength"]),
                          "Exif:FocalLengthIn35mmFilm": str(config["exif_data"]["FocalLengthIn35mmFormat"]),
                          "Exif:LensModel": "35.0 f / 2.2",
                          "Exif:BodySerialNumber": str(config["exif_data"]["CameraSerialNumber"]),
                          "Exif:ColorSpace": "65535",
                          "Make": str(config["exif_data"]["Make"]),
                          "MicrosoftPhoto:LensManufacturer": "Computar",
                          "Model": str(config["exif_data"]["Model"]),
                          "Orientation": "1",
                          "PixelAspectRatio": "1",
                          "ResolutionUnit": "in",
                          "XResolution": "150",
                          "YResolution": "150",
                          "compression": "lzw",
                          "oiio:BitsPerSample": "8",
                          "planarconfig": "contig",
                          "tiff:Compression": "5",
                          "tiff:PhotometricInterpretation": "2",
                          "tiff:PlanarConfiguration": "1",
                          "tiff:RowsPerStrip": "47",
                          "tiff:UnassociatedAlpha": "1",
                          "tiff:subfiletype": "0"
                      }
                      }
        poses_temp = {"poseId": str(viewId),
                      "pose": {
                          "transform": {
                              "rotation": [
                                  str(round(trans_mat[0][0], ndigits=17)),
                                  str(round(trans_mat[0][1], ndigits=17)),
                                  str(round(trans_mat[0][2], ndigits=17)),

                                  str(round(trans_mat[1][0], ndigits=17)),
                                  str(round(trans_mat[1][1], ndigits=17)),
                                  str(round(trans_mat[1][2], ndigits=17)),

                                  str(round(trans_mat[2][0], ndigits=17)),
                                  str(round(trans_mat[2][1], ndigits=17)),
                                  str(round(trans_mat[2][2], ndigits=17))
                              ],
                              "center": [
                                  str(round(trans_mat[0][3], ndigits=17)),
                                  str(round(trans_mat[1][3], ndigits=17)),
                                  str(round(trans_mat[2][3], ndigits=17))
                              ]
                          },
                          "locked": "0"
                      }
                      }

        full_dict["views"].append(views_temp)
        full_dict["poses"].append(poses_temp)

    full_dict["intrinsics"] = [{
        "intrinsicId": str(intrinsicId),
        "width": str(image_dimensions[1]),
        "height": str(image_dimensions[0]),
        "sensorWidth": "13.13",
        "sensorHeight": "8.753",
        "serialNumber": str(config["exif_data"]["CameraSerialNumber"]),
        "type": "radial3",
        "initializationMode": "estimated",
        "initialFocalLength": str(config["exif_data"]["FocalLength"]),
        "focalLength": str(config["exif_data"]["FocalLength"]),
        "pixelRatio": "1",
        "pixelRatioLocked": "true",
        "principalPoint": [
            "209.89391323262956",
            "75.439437418339779"
        ],
        "distortionInitializationMode": "none",
        "distortionParams": [
            "-0.045115948805775699",
            "41.139325141963582",
            "-930.4076823498674"
        ],
        "undistortionOffset": [
            "0",
            "0"
        ],
        "undistortionParams": "",
        "locked": "false"
    }]

    """
    Dump into the respective files:
    - cameraInit.sfm
    - viewpoints.sfm
    - cameras.sfm
    """

    with open(os.path.join(project_location, "TEST.json"), "w") as file:
        json.dump(full_dict, file, )

    print("Data stored successfully!")


if __name__ == '__main__':
    project_location = Path("S:/images/Amphipyra_pyramidea")
    config = read_config_file(path=Path.joinpath(project_location, "Amphipyra_pyramidea_config.yaml"))

    generate_sfm(project_location=project_location, use_cutouts=False, file_ending=".tif")
