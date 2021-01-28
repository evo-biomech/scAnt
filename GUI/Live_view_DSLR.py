from os.path import join, sep
from os import system
import subprocess
from pathlib import Path
from time import sleep
import psutil

# Update with the path to CameraControlCmd.exe file.
digi_cam_path = join('C:' + sep, 'Program Files (x86)', 'digiCamControl')
digi_cam_cmd_path = join(digi_cam_path, 'CameraControlCmd.exe')
digi_cam_app_path = join(digi_cam_path, 'CameraControl.exe')
digi_cam_remote_path = join(digi_cam_path, 'CameraControlRemoteCmd.exe')


class customDSLR():

    def __init__(self):

        # get camera info. If none is connected, exit the program
        p = subprocess.Popen('"' + str(digi_cam_cmd_path) + '" /verbose',
                             stdout=subprocess.PIPE, universal_newlines=True, shell=False)
        (output, err) = p.communicate()
        try:
            self.camera_model = output.split("Driver :")[-1]
            if self.camera_model[0:4] == "digi" or not self.camera_model:
                print("No camera detected!")
                self.camera_model = None
                return
            else:
                print("Detected:", self.camera_model)
        except IndexError:
            print("No camera detected!")
            return

        # get all values as soon as camera is initialised
        self.all_iso_vals = []
        self.all_aperture_vals = []
        self.all_shutterspeed_vals = []

    def initialise_camera(self):

        # launch DigiCamControl
        subprocess.Popen('"' + str(digi_cam_app_path) + '"')

        # check for instance of CameraControl.exe for 20 seconds until timeout
        for i in range(20):
            sleep(1)
            sp = subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c list sessions",
                                  stdout=subprocess.PIPE, universal_newlines=True, shell=False)
            (output, err) = sp.communicate()
            message = str(output).split(":")[-1].split("\n")[0]
            if message == "no camera is connected":
                print("Waiting for instance of CameraControl.exe to launch...")
            else:
                print(message)
                print("CameraControl.exe launched successfully!")
                break

            if i == 19:
                print("Timeout! No response from Camera or CameraControl.exe!")
                return

        # iso
        self.all_iso_vals = self.get_all_settings("iso")
        # aperture
        self.all_aperture_vals = self.get_all_settings("aperture")
        # shutter speed
        self.all_shutterspeed_vals = self.get_all_settings("shutterspeed")

    def get_all_settings(self, key):
        sp = subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c list " + key,
                              stdout=subprocess.PIPE, universal_newlines=True, shell=False)
        (output, err) = sp.communicate()
        print(output)
        raw_vals = (str(output).split("[")[-1].split("]")[0].split(","))
        all_vals = []
        for val in raw_vals:
            all_vals.append(val.split('"')[1])

        return all_vals

    def configure_exposure(self, shutterspeed="1/100"):
        subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c set shutterspeed " + shutterspeed,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def set_iso(self, iso="500"):
        subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c set iso " + iso,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def set_aperture(self, aperture="5.6"):
        subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c set aperture " + aperture,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def start_live_view(self):
        # open live view window
        subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c do LiveViewWnd_Show",
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def stop_live_view(self):
        # close live view window
        subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c do LiveViewWnd_Hide",
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    def capture_image(self, img_name="example.jpg"):
        subprocess.Popen('"' + str(digi_cam_remote_path) + '"' + " /c capturenoaf " + img_name,
                         stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


if __name__ == '__main__':

    # example settings
    iso = "500"
    aperture = "1.8"
    shutterspeed = "1/50"

    # where to save images
    current_folder = str(Path.cwd().parent)

    # calling the class for the first time is meant to aid in finding attached cameras.
    # the name of the connected camera is then stored in DSLR.camera_model
    DSLR = customDSLR()
    if DSLR.camera_model is None:
        # exit program when no camera is connected
        exit()

    # if a camera is connected, it needs to be initialised before use
    DSLR.initialise_camera()

    DSLR.start_live_view()

    DSLR.set_iso(iso)
    DSLR.set_aperture(aperture)
    DSLR.configure_exposure(shutterspeed)

    # TODO get highlight exposure to work
    # system('"' + str(digi_cam_remote_path) + '"' + " /c set liveview.highlightoverexp true")

    capture_images = 3
    # and now capture 3 images with unique names
    for i in range(capture_images):
        DSLR.capture_image(current_folder + "\\test_image_" + str(i) + ".jpg")

    DSLR.stop_live_view()
