# 1. read config file to retrieve all processing info
# 2. stack images
# 3. mask  images
# 4. write meta data to images

import argparse
from pathlib import Path
from project_manager import read_config_file

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

    args = vars(ap.parse_args())

    folder = Path(args["images"])
    config = read_config_file(args["config"])
    exif = config["exif_data"]

    # after stacking, the image path needs to be updated to point to the "stacked" instead of the "RAW" folder
    