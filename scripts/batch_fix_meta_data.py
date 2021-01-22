from scripts.write_meta_data import write_exif_to_img
from scripts.project_manager import read_config_file
from pathlib import Path
import os
import cv2
import numpy as np
import time
from scripts.mask_generator import apply_local_contrast

# enter the folder to your project here
folder = Path("C:\\Users\\Legos\\Desktop\\3D_scans\\0050_um\\RAW_stacked")
config = read_config_file(Path.cwd().parent.joinpath("example_config.yaml"))
exif = config["exif_data"]
use_CLAHE = False
scale_percent = 100

for img in os.listdir(str(folder)):
    print(img)
    if img[-5:] == "_.tif":
        img_tif = cv2.imread(str(folder.joinpath(img)), cv2.IMREAD_UNCHANGED)
        img_alpha = cv2.imread(str(folder.joinpath(img[:-4] + "_masked.png")))
        _, mask = cv2.threshold(cv2.cvtColor(img_alpha, cv2.COLOR_BGR2GRAY), 240, 255, cv2.THRESH_BINARY)
        print(img_tif.shape)
        img_jpg = cv2.bitwise_not(cv2.bitwise_not(img_tif[:, :, :3], mask=mask))

        print(img_jpg.shape)
        img_jpg[np.where((img_jpg == [255, 255, 255]).all(axis=2))] = [0, 0, 0]
        filename = str(folder.joinpath(img))[:-5] + "_new.jpg"
        print(filename)

        if use_CLAHE:
            img_jpg = apply_local_contrast(img_jpg)

        if scale_percent != 100:
            # Decrease resolution
            width = int(img_jpg.shape[1] * scale_percent / 100)
            height = int(img_jpg.shape[0] * scale_percent / 100)
            dim = (width, height)
            # resize image
            img_jpg = cv2.resize(img_jpg, dim, interpolation=cv2.INTER_AREA)

        cv2.imwrite(filename, img_jpg)
        write_exif_to_img(img_path=filename, custom_exif_dict=exif)

