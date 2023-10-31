from write_meta_data import write_exif_to_img
from project_manager import read_config_file
import argparse
from pathlib import Path
import os
import cv2
import numpy as np

if __name__ == '__main__':
    """
    ### Loading image paths into queue from disk ###
    """

    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--images", type=str, required=True,
                    help="path to input directory of images, or list of image paths")
    ap.add_argument("-c", "--config", type=str, required=True,
                    help="path to your config file containing your camera data")
    ap.add_argument("-cu", "--cutout", type=bool, default=False,
                    help="create jpg cutouts from original images and their masks [True / False]")
    ap.add_argument("-s", "--scale", type=float, default=100,
                    help="rescale images in percent [default = 100]")

    args = vars(ap.parse_args())

    folder = Path(args["images"])
    config = read_config_file(args["config"])
    exif = config["exif_data"]

    for img in os.listdir(str(folder)):
        print(img)
        if img[-4:] == ".tif" or img[-4:] == ".jpg":
            img_tif = cv2.imread(str(folder.joinpath(img)), cv2.IMREAD_UNCHANGED)

            if args["cutout"]:
                # creates a .jpg cutout from the original image file and the supplied mask
                # this requires for the masks to be located in the same folder
                try:
                    img_alpha = cv2.imread(str(folder.joinpath(img[:-4] + "_masked.png")))
                    _, mask = cv2.threshold(cv2.cvtColor(img_alpha, cv2.COLOR_BGR2GRAY), 240, 255, cv2.THRESH_BINARY)
                except cv2.error:
                    print("WARNING! Could not find corresponding masks!\n Exiting...")
                    break

                print(img_tif.shape)
                img_jpg = cv2.bitwise_not(cv2.bitwise_not(img_tif[:, :, :3], mask=mask))

                print(img_jpg.shape)
                img_jpg[np.where((img_jpg == [255, 255, 255]).all(axis=2))] = [0, 0, 0]
                filename = str(folder.joinpath(img))[:-5] + "_new.jpg"
                print(filename)

                if args["scale"] != 100:
                    # Decrease resolution
                    width = int(img_jpg.shape[1] * args["scale"] / 100)
                    height = int(img_jpg.shape[0] * args["scale"] / 100)
                    dim = (width, height)
                    # resize image
                    img_jpg = cv2.resize(img_jpg, dim, interpolation=cv2.INTER_AREA)

                cv2.imwrite(filename, img_jpg)
                write_exif_to_img(img_path=filename, custom_exif_dict=exif)

            cv2.imwrite(str(folder.joinpath(img)), img_tif)
            write_exif_to_img(img_path=str(folder.joinpath(img)), custom_exif_dict=exif)
