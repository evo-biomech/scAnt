from os.path import join, sep
from os import system
import subprocess
from pathlib import Path
from time import sleep


def get_all_settings(key):
    sp = subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c list " + key,
                          stdout=subprocess.PIPE, universal_newlines=True, shell=False)
    (output, err) = sp.communicate()
    raw_vals = (str(output).split("[")[-1].split("]")[0].split(","))
    all_vals = []
    for val in raw_vals:
        all_vals.append(val.split('"')[1])

    return all_vals


# Update with the path to CameraControlCmd.exe file.
digi_cam_path = join('C:' + sep, 'Program Files (x86)', 'digiCamControl')
digi_cam_cmd_path = join(digi_cam_path, 'CameraControlCmd.exe')
digi_cam_app_path = join(digi_cam_path, 'CameraControl.exe')
digi_cam_remote_path = join(digi_cam_path, 'CameraControlRemoteCmd.exe')

current_folder = str(Path.cwd().parent)

# get camera info. If none is connected, exit the program
p = subprocess.Popen('"' + str(digi_cam_cmd_path) + '" /verbose',
                     stdout=subprocess.PIPE, universal_newlines=True, shell=False)
(output, err) = p.communicate()
try:
    camera_model = output.split("Driver :")[-1]
    if camera_model[0:4] == "digi" or not camera_model:
        print("No camera detected!")
        exit()
    else:
        print("Detected:", camera_model)
except IndexError:
    print("No camera detected!")
    exit()

# launch DigiCamControl
p = subprocess.Popen('"' + str(digi_cam_app_path) + '"')

"""
APPLY SETTINGS AND CAPTURE
"""

# wait for the application to launch before proceeding
sleep(4)

iso = "500"
aperture = "1.8"
shutter_speed = "1/50"

# apply camera settings
# passing the output to DEVNULL avoids printing to the console, as there is no relevant info returned

# iso
all_iso_vals = get_all_settings("iso")
print("\n camera iso range")
print(all_iso_vals)
p = subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c set iso " + iso,
                     stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

# aperture
all_aperture_vals = get_all_settings("aperture")
print("\n camera aperture range")
print(all_aperture_vals)
p = subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c set aperture " + aperture,
                     stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

# shutter speed
all_shutterspeed_vals = get_all_settings("shutterspeed")
print("\n camera shutter speed range")
print(all_shutterspeed_vals)
p = subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c set shutterspeed " + shutter_speed,
                     stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

exit()

# open live view window
system('"' + str(digi_cam_remote_path) + '"' + " /c do LiveViewWnd_Show")

# TODO get highlight exposure to work
# system('"' + str(digi_cam_remote_path) + '"' + " /c set liveview.highlightoverexp true")

# and now capture 3 images with unique names
for i in range(3):
    system('"' + str(digi_cam_remote_path) + '"' + " /c capturenoaf " + current_folder + "\\0_0_blob" + str(i) + ".jpg")

# close live view window
system('"' + str(digi_cam_remote_path) + '"' + " /c do LiveViewWnd_Hide")
