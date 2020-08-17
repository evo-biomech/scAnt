import subprocess
import time
from pathlib import Path
import platform
from scripts.project_manager import read_config_file

# follow installation guide for Ubuntu or use executable directly under Windows (located in "/external")
# sudo apt install libimage-exiftool-perl

def show_me_what_you_got(img_path):
    if platform.system() == "Linux":
        exifToolPath = "exiftool"
    else:
        exifToolPath = str(Path.cwd().parent.joinpath("external", "exiftool.exe"))
        # for Windows user have to specify the Exif tool exe path for metadata extraction.

    infoDict = {}  # Creating the dict to get the metadata tags
    ''' use Exif tool to get the metadata '''
    process = subprocess.Popen([exifToolPath, img_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True)
    """ get the tags in dict """
    for tag in process.stdout:
        line = tag.strip().split(':')
        infoDict[line[0].strip()] = line[-1].strip()

    for k, v in infoDict.items():
        print(k, ':', v)


def write_exif_to_img(img_path, custom_exif_dict):
    if platform.system() == "Linux":
        exifToolPath = "exiftool"
    else:
        exifToolPath = str(Path.cwd().parent.joinpath("external", "exiftool.exe"))
        # for Windows user have to specify the Exif tool exe path for metadata extraction.

    complete_command = [exifToolPath, img_path]
    for key in custom_exif_dict:
        write_str = "-" + key + "=" + str(custom_exif_dict[key])
        print(write_str)
        complete_command.append(write_str)

    subprocess.Popen(complete_command)


if __name__ == '__main__':
    # img_path = "_DSC0743.jpg"
    # img_path = "porcellio_dilatatus_x_00000_y_00000_.tif"
    img_path = "_x_00000_y_00000__cutout.tif"

    print("original file: ")
    show_me_what_you_got(img_path)

    config = read_config_file(Path.cwd().parent.joinpath("example_config.yaml"))
    custom_exif_dict = config["exif_data"]

    write_exif_to_img(img_path=img_path, custom_exif_dict=custom_exif_dict)

    # wait for file to be updated before opening it again
    time.sleep(1)

    print("\nupdated file")
    show_me_what_you_got(img_path)
