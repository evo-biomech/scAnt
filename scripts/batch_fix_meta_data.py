from scripts.write_meta_data import write_exif_to_img
from scripts.project_manager import read_config_file
from pathlib import Path
import os
import cv2

# enter the folder to your project here
folder = Path("I:\\3D_Scanner\\images\\leaffooted_fine_stacked")
config = read_config_file(Path.cwd().parent.joinpath("example_config.yaml"))
exif = config["exif_data"]

for img in os.listdir(str(folder)):
    if img[-5:] == "_.tif":
        img_tif = cv2.imread(str(folder.joinpath(img)), cv2.IMREAD_UNCHANGED)
        img_alpha = cv2.imread(str(folder.joinpath(img[:-4] + "_masked.png")), cv2.IMREAD_UNCHANGED)

        _, mask = cv2.threshold(img_alpha, 240, 255, cv2.THRESH_BINARY)

        print(img_tif.shape)
        img_jpg = cv2.bitwise_not(cv2.bitwise_not(img_tif[:, :, :3], mask=mask))
        print(img_jpg.shape)
        filename = str(folder.joinpath(img))[:-4] + "cutout_new.tif"
        print(filename)
        cv2.imwrite(filename, img_jpg)
        write_exif_to_img(img_path=filename, custom_exif_dict=exif)
