from scripts.project_manager import read_config_file
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import numpy as np
import math
import os
import cv2


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


def tab_x_REALTAB(n):
    # produces real tabs
    string = "\n"
    for i in range(n):
        string += "\t"
    return string


def tab_x(n):
    # produces 4 spaces instead of tabs
    string = "\n"
    for i in range(n):
        string += "    "
    return string


def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def generate_sfm(project_location, use_cutouts=True):
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
            if img[-5] == "_":
                image_list.append(img)

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

    """
    Define version and folders
    """
    print(project_location.joinpath("cameras.sfm"))
    out = open(project_location.joinpath("cameras.sfm"), "w+")
    out.write("{")
    out.write(tab_x(1) + '"version": [')
    out.write(tab_x(2) + '"1",')
    out.write(tab_x(2) + '"0",')
    out.write(tab_x(2) + '"0"')
    out.write(tab_x(1) + '],')

    out.write(tab_x(1) + '"featuresFolders": [')
    out.write(tab_x(2) + '""')
    out.write(tab_x(2))
    out.write(tab_x(1) + '],')

    out.write(tab_x(1) + '"matchesFolders": [')
    out.write(tab_x(2) + '""')
    out.write(tab_x(2))
    out.write(tab_x(1) + '],')

    out.write(tab_x(1) + '"views": [')

    viewId = 10000000
    intrinsicId = 1000000000
    resectionId = 0
    locked = 1

    image_location = splitall(project_location.joinpath("stacked"))
    meshroom_img_path = image_location[0][:-1]
    for dir in image_location[1:]:
        meshroom_img_path += "\/" + dir

    """
    Enter all cameras and assign IDs to reference for each pose
    """

    for cam in range(len(trans_mats)):
        out.write(tab_x(2) + '{')
        viewId += 1
        resectionId += 1
        out.write(tab_x(3) + '"viewId": "' + str(viewId) + '",')
        out.write(tab_x(3) + '"poseId": "' + str(viewId) + '",')
        out.write(tab_x(3) + '"intrinsicId": "' + str(intrinsicId) + '",')
        out.write(tab_x(3) + '"resectionId": "' + str(resectionId) + '",')
        out.write(tab_x(3) + '"path": "' + meshroom_img_path + '\/' + image_list[cam] + '",')
        out.write(tab_x(3) + '"width": "' + str(image_dimensions[1]) + '",')
        out.write(tab_x(3) + '"height": "' + str(image_dimensions[0]) + '",')
        out.write(tab_x(3) + '"metadata": {')
        out.write(tab_x(4) + '"AliceVision:SensorWidth": "13.1",')
        out.write(tab_x(4) + '"Exif:FocalLength": "' + str(config["exif_data"]["FocalLength"]) + '",')
        out.write(tab_x(4) + '"Exif:FocalLengthIn35mmFilm": "'
                  + str(config["exif_data"]["FocalLengthIn35mmFormat"]) + '",')
        out.write(tab_x(4) + '"FNumber": "16",')
        out.write(tab_x(4) + '"Make": "' + str(config["exif_data"]["Make"]) + '",')
        out.write(tab_x(4) + '"Model": "' + str(config["exif_data"]["Model"]) + '",')
        out.write(tab_x(4) + '"Orientation": "1",')
        out.write(tab_x(4) + '"PixelAspectRatio": "1",')
        out.write(tab_x(4) + '"ResolutionUnit": "in",')
        out.write(tab_x(4) + '"XResolution": "150",')
        out.write(tab_x(4) + '"YResolution": "150",')
        out.write(tab_x(4) + '"compression": "lzw",')
        out.write(tab_x(4) + '"oiio:BitsPerSample": "8",')
        out.write(tab_x(4) + '"planarconfig": "contig",')

        out.write(tab_x(4) + '"tiff:Compression": "5",')
        out.write(tab_x(4) + '"tiff:PhotometricInterpretation": "2",')
        out.write(tab_x(4) + '"tiff:PlanarConfiguration": "1",')
        out.write(tab_x(4) + '"tiff:RowsPerStrip": "47",')
        out.write(tab_x(4) + '"tiff:UnassociatedAlpha": "1",')
        out.write(tab_x(4) + '"tiff:subfiletype": "0"')

        out.write(tab_x(3) + '}')

        out.write(tab_x(2) + '}')

        if cam != len(trans_mats) - 1:
            # add a comma to all but the last entry
            out.write(',')

    """
    Enter intrinsics of camera model(s)
    These values need to be calculated / estimated by Meshroom and entered here
    """

    out.write(tab_x(1) + '],')
    out.write(tab_x(1) + '"intrinsics": [')

    out.write(tab_x(2) + '{')
    out.write(tab_x(3) + '"intrinsicId": "' + str(intrinsicId) + '",')
    out.write(tab_x(3) + '"width": "' + str(image_dimensions[1]) + '",')
    out.write(tab_x(3) + '"height": "' + str(image_dimensions[0]) + '",')
    out.write(tab_x(3) + '"serialNumber": "' + meshroom_img_path + '_' + str(config["exif_data"]["Model"]) + '",')
    out.write(tab_x(3) + '"type": "radial3",')
    out.write(tab_x(3) + '"initializationMode": "estimated",')
    out.write(tab_x(3) + '"pxInitialFocalLength": "14619.847328244276",')
    out.write(tab_x(3) + '"pxFocalLength": "15519.947135073095",')
    out.write(tab_x(3) + '"principalPoint": [')

    out.write(tab_x(4) + '"2716.6301443869565",')
    out.write(tab_x(4) + '"1867.8392268971065"')

    out.write(tab_x(3) + '],')
    out.write(tab_x(3) + '"distortionParams": [')

    out.write(tab_x(4) + '"-0.17524723918970503",')
    out.write(tab_x(4) + '"64.900546663178233",')
    out.write(tab_x(4) + '"-2556.4868417370758"')

    out.write(tab_x(3) + '],')
    out.write(tab_x(3) + '"locked": "' + str(locked) + '"')

    out.write(tab_x(2) + '}')

    """
    All estimated poses are 
    """

    out.write(tab_x(1) + '],')
    out.write(tab_x(1) + '"poses": [')

    # reset viewID to begin at the initial count and move sequentially through all cameras
    viewId = 10000000
    cam = 0
    for trans_mat in trans_mats:
        out.write(tab_x(2) + '{')
        viewId += 1
        out.write(tab_x(3) + '"poseId": "' + str(viewId) + '",')
        out.write(tab_x(3) + '"pose": {')
        out.write(tab_x(4) + '"transform": {')
        out.write(tab_x(5) + '"rotation": [')

        # rotation of camera
        out.write(tab_x(6) + '"' + str(round(trans_mat[0][0], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[0][1], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[0][2], ndigits=17)) + '",')

        out.write(tab_x(6) + '"' + str(round(trans_mat[1][0], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[1][1], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[1][2], ndigits=17)) + '",')

        out.write(tab_x(6) + '"' + str(round(trans_mat[2][0], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[2][1], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[2][2], ndigits=17)) + '"')

        out.write(tab_x(5) + '],')
        out.write(tab_x(5) + '"center": [')

        # translation of camera
        out.write(tab_x(6) + '"' + str(round(trans_mat[0][3], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[1][3], ndigits=17)) + '",')
        out.write(tab_x(6) + '"' + str(round(trans_mat[2][3], ndigits=17)) + '"')

        out.write(tab_x(5) + ']')
        out.write(tab_x(4) + '},')
        out.write(tab_x(4) + '"locked": "' + str(locked) + '"')
        out.write(tab_x(3) + '}')
        out.write(tab_x(2) + '}')

        if cam != len(trans_mats) - 1:
            # add a comma to all but the last entry
            out.write(',')
        cam += 1

    out.write(tab_x(1) + ']')
    out.write('\n}')

    out.close()


if __name__ == '__main__':
    config = read_config_file(path=Path.cwd().parent.joinpath("example_config.yaml"))

    generate_sfm(project_location=Path("/home/fabi/camponotus_gigas"), use_cutouts=False)

    exit()

    print(config["scanner_settings"])
    X, Y, Z = create_input_arrays(config)

    X_ang = convert_to_angles(X, inc_per_rot=1600)  # as the initial angle is view from below
    Y_ang = convert_to_angles(Y, inc_per_rot=1600)

    # max Z -> 40,000 at ~ 25 cm sensor to centre
    # min Z ->      0 at ~ 15 cm sensor to centre
    # measured 40,000 tics = ~ 10 cm +/- 0.1 cm

    # distance_tic -> convert to distance in meters to use as constant radius

    corrected_Z = (((Z[0] * (-1)) / 40000) * 10 + 15) / 100

    scanner_positions, scanner_orientations, trans_mats = get_approx_cam_pos(X_ang=X_ang, Y_ang=Y_ang,
                                                                             r=corrected_Z)

    # compute transformation matrices for every camera
    trans_mat_start = create_transformation_matrix(px=scanner_positions[0][0],
                                                   py=scanner_positions[1][0],
                                                   pz=scanner_positions[2][0],
                                                   alpha=-Y_ang[0] + math.pi,
                                                   beta=0,
                                                   gamma=X_ang[0] - (193 / 1600 * 2 * math.pi))

    print("\n transformation matrix of initial camera position")
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

    ####
    print("{\n\t{\n\tTesty\n\t}\n}")
