from scripts.write_meta_data import write_exif_to_img
from scripts.project_manager import read_config_file
from pathlib import Path
import os
import cv2
import numpy as np

# enter the folder to your project here
folder = Path("I:\\3D_Scanner\\Reconstruction\\Orthomeria_versicolor\\stacked")
config = read_config_file(Path.cwd().parent.joinpath("example_config.yaml"))
exif = config["exif_data"]

for img in os.listdir(str(folder)):
    print(img)
    if img[-5:] == "_.tif":
        img_tif = cv2.imread(str(folder.joinpath(img)), cv2.IMREAD_UNCHANGED)
        img_alpha = cv2.imread(str(folder.joinpath(img[:-4] + "_masked.png")), cv2.IMREAD_UNCHANGED)

        _, mask = cv2.threshold(img_alpha, 240, 255, cv2.THRESH_BINARY)

        print(img_tif.shape)
        img_jpg = cv2.bitwise_not(cv2.bitwise_not(img_tif[:, :, :3], mask=mask))
        print(img_jpg.shape)
        img_jpg[np.where((img_jpg == [255, 255, 255]).all(axis=2))] = [0, 0, 0]
        filename = str(folder.joinpath(img))[:-5] + "_blk.jpg"
        print(filename)

        
        # Decrease resolution
        scale_percent = 75  # percent of original size
        width = int(img_jpg.shape[1] * scale_percent / 100)
        height = int(img_jpg.shape[0] * scale_percent / 100)
        dim = (width, height)
        # resize image
        resized = cv2.resize(img_jpg, dim, interpolation=cv2.INTER_AREA)

        cv2.imwrite(filename, resized)
        write_exif_to_img(img_path=filename, custom_exif_dict=exif)
