from scripts.write_meta_data import write_exif_to_img
from scripts.project_manager import read_config_file
from pathlib import Path
import os
import cv2

folder = Path("/home/fabi/camponotus_gigas/stacked")
config = read_config_file("/home/fabi/camponotus_gigas/example_config.yaml")
exif = config["exif_data"]

for img in os.listdir(str(folder)):
    if img[-10:] == "cutout.tif":
        img_tif = cv2.imread(str(folder.joinpath(img)), cv2.IMREAD_UNCHANGED)
        alpha = img_tif[:, :, 3]
        _, mask = cv2.threshold(alpha, 240, 255, cv2.THRESH_BINARY)

        print(alpha)
        print(img_tif.shape)
        img_jpg = cv2.bitwise_not(cv2.bitwise_not(img_tif[:, :, :3], mask=mask))
        cv2.waitKey(1)

        filename = str(folder.joinpath(img))[:-3] + "jpg"
        cv2.imwrite(filename, img_jpg)
        write_exif_to_img(img_path=filename, custom_exif_dict=exif)
