import os
import numpy as np
from pathlib import Path

"""
00281470,         Tic T500 Stepper Motor Controller -> Z-Axis (turntable)
00281480,         Tic T500 Stepper Motor Controller -> Y-Axis (camera arm)
00282144,         Tic T500 Stepper Motor Controller -> camera Focus
"""


class ScannerController:

    def __init__(self):
        self.stepperX_ID = "00281480"
        self.stepperY_ID = "00281470"
        self.stepperZ_ID = "00282144"

        self.stepper_names = ["X", "Y", "Z"]
        self.stepper_IDs = [self.stepperX_ID, self.stepperY_ID, self.stepperZ_ID]
        self.stepper_home = ['rev', None, 'fwd']
        self.stepper_home_pos = [-1000, 0, 50000]
        self.stepper_maxAccel = [10000, 20000, 100000]
        self.stepper_maxVelocity = [800000, 1000000, 60000000]
        self.stepper_stepModes = [8, 8, 8]
        self.stepper_currents = [174, 174, 343]

        self.stepper_maxPos = [450, 1600, 0]
        self.stepper_minPos = [0, -1600, -45000]

        # get the current positions of all steppers
        self.stepper_position = [None, None, None]

        # settings for scanning
        self.scan_stepSize = [50, 80, 500]

        self.scan_pos = [None, None, None]
        # set list of scan poses
        self.setScanRange(stepper=0, min=0, max=450, step=self.scan_stepSize[0])
        self.setScanRange(stepper=1, min=0, max=1600, step=self.scan_stepSize[1])
        self.setScanRange(stepper=2, min=-25000, max=-8000, step=self.scan_stepSize[2])

        # keep track of position during scanning, skip to next full rotation of Y Axis
        self.completedRotations = 0
        self.completedStacks = 0

        for st in range(len(self.stepper_names)):
            self.setStepMode(st, self.stepper_stepModes[st])
            self.setCurrent(st, self.stepper_currents[st])
            self.setMaxAccel(st, self.stepper_maxAccel[st])
            self.setMaxSpeed(st, self.stepper_maxVelocity[st])
            self.getStepperPosition(st)

        self.images_taken = 0
        self.images_to_take = len(self.scan_pos[0]) * len(self.scan_pos[1]) * len(self.scan_pos[2])

        self.progress = self.getProgress()

        self.outputFolder = ""

    def correctName(self, val):
        """
        :param val: integer value to be brought into correct format
        :return: str of corrected name
        """
        if abs(val) < 10:
            step_name = "0000" + str(abs(val))
        elif abs(val) < 100:
            step_name = "000" + str(abs(val))
        elif abs(val) < 1000:
            step_name = "00" + str(abs(val))
        elif abs(val) < 10000:
            step_name = "0" + str(abs(val))
        else:
            step_name = str(abs(val))

        return step_name

    def deEnergise(self):
        for stepper_ID in self.stepper_IDs:
            os.system('ticcmd --deenergize -d ' + stepper_ID)

    def resume(self):
        for stepper_ID in self.stepper_IDs:
            os.system('ticcmd --resume --reset-command-timeout -d ' + stepper_ID)

    def setStepMode(self, stepper, step_mode):
        self.stepper_stepModes[stepper] = step_mode
        os.system('ticcmd --step-mode ' + str(step_mode) + ' -d ' + self.stepper_IDs[stepper])

    def setCurrent(self, stepper, current):
        self.stepper_currents[stepper] = current
        os.system('ticcmd --current ' + str(current) + ' -d ' + self.stepper_IDs[stepper])

    def setMaxAccel(self, stepper, max_accel):
        self.stepper_maxAccel[stepper] = max_accel
        os.system('ticcmd --max-accel ' + str(max_accel) + ' -d ' + self.stepper_IDs[stepper])

    def setMaxSpeed(self, stepper, max_velocity):
        self.stepper_maxVelocity[stepper] = max_velocity
        os.system('ticcmd --max-speed ' + str(max_velocity) + ' -d ' + self.stepper_IDs[stepper])

    def home(self, stepper):
        if self.stepper_home_pos[stepper] != 0:
            print("Homing stepper", self.stepper_names[stepper])
            os.system('ticcmd --resume --position ' + str(
                self.stepper_home_pos[stepper]) + ' --reset-command-timeout -d ' + self.stepper_IDs[stepper])

            while not self.getLimitState(stepper):
                os.system('ticcmd --resume --reset-command-timeout -d ' + self.stepper_IDs[stepper])
                # sleep(0.2)

        os.system('ticcmd --halt-and-set-position 0 -d ' + self.stepper_IDs[stepper])

    def getStepperPosition(self, stepper):
        info = os.popen('ticcmd --status -d ' + self.stepper_IDs[stepper]).read()
        # split returned results into its elements
        lines = info.split("\n")
        current_position = int(lines[21].split(" ")[-1])
        self.stepper_position[stepper] = current_position

    def getLimitState(self, stepper):
        info = os.popen('ticcmd --status -d ' + self.stepper_IDs[stepper]).read()
        # split returned results into its elements
        lines = info.split("\n")

        if self.stepper_home[stepper] == "fwd":
            state = lines[12].split(" ")[-1]
        elif self.stepper_home[stepper] == "rev":
            state = lines[13].split(" ")[-1]
        else:
            print("Home direction is not defined for stepper:", self.stepper_names[stepper])
            state = "Yes"

        if state == "Yes":
            print("Home reached for stepper:", self.stepper_names[stepper])
            return True
        else:
            return False

    def moveToPosition(self, stepper, pos):
        # for axes that do not require limits
        if self.stepper_home[stepper] is not None:
            if pos > self.stepper_maxPos[stepper]:
                pos = self.stepper_maxPos[stepper]
            elif pos < self.stepper_minPos[stepper]:
                pos = self.stepper_minPos[stepper]

            pos = int(pos)
            print("Moving stepper", self.stepper_names[stepper], "to position", pos)

        else:
            pos = int(pos)
            print("Moving stepper", self.stepper_names[stepper], "to position",
                  pos)

        os.system('ticcmd --resume --position ' + str(pos) + ' --reset-command-timeout -d ' + self.stepper_IDs[stepper])
        self.getStepperPosition(stepper)
        while self.stepper_position[stepper] != pos:
            os.system('ticcmd --resume --reset-command-timeout -d ' + self.stepper_IDs[stepper])
            self.getStepperPosition(stepper)

    def setScanRange(self, stepper, min, max, step):
        # set min and max poses according to input (within range)
        if max > self.stepper_maxPos[stepper]:
            max = self.stepper_maxPos[stepper]
        elif min < self.stepper_minPos[stepper]:
            min = self.stepper_minPos[stepper]

        # set desired step size (limited by GUI inputs as well as min and max values)
        self.scan_stepSize[stepper] = step

        self.scan_pos[stepper] = np.array(np.arange(int(min), int(max), int(self.scan_stepSize[stepper])), dtype=int)
        if len(self.scan_pos[stepper]) == 0:
            print("INPUT ERROR FOUND!")
            self.scan_pos[stepper] = np.array([0])

    def getProgress(self):
        progress = 100 * (self.images_taken / self.images_to_take)
        return progress

    def initCam(self, cam):
        self.cam = cam

    def runScan(self):
        for posX in self.scan_pos[0]:
            self.moveToPosition(0, posX)
            for posY in self.scan_pos[1]:
                self.moveToPosition(1, posY + self.completedRotations * self.stepper_maxPos[1])
                for posZ in self.scan_pos[2]:
                    self.moveToPosition(2, posZ)
                    # to follow the naming convention when focus stacking
                    img_name = self.outputFolder + "x_" + self.correctName(posX) + "_y_" + self.correctName(
                        posY) + "_step_" + self.correctName(posZ) + "_.tif"

                    self.cam.capture_image(img_name=img_name)
                    self.progress = self.getProgress()

                self.completedStacks += 1

            self.completedRotations += 1

        # return to default position
        print("Returning to default position")
        scAnt.moveToPosition(stepper=0, pos=190)
        scAnt.moveToPosition(stepper=1, pos=self.completedRotations * self.stepper_maxPos[1])
        scAnt.moveToPosition(stepper=2, pos=-20000)


if __name__ == '__main__':
    try:
        from GUI.Live_view_FLIR import customFLIR
    except ModuleNotFoundError:
        print("WARNING: PySpin module not found! You can ignore this message when not using FLIR cameras.")
    print("Testing funcitonality of components")
    scAnt = ScannerController()
    scAnt.initCam(customFLIR())

    # Home all steppers
    for stepper in range(3):
        scAnt.home(stepper)

    # Movement test of steppers
    scAnt.moveToPosition(stepper=0, pos=190)
    scAnt.moveToPosition(stepper=1, pos=200)
    scAnt.moveToPosition(stepper=1, pos=0)
    scAnt.moveToPosition(stepper=2, pos=-20000)

    # capture image, using custom FLIR scripts
    scAnt.cam.capture_image(img_name="testy_mac_testface.tif")

    # define output folder
    scAnt.outputFolder = Path.cwd()
    if not os.path.exists(scAnt.outputFolder):
        os.makedirs(scAnt.outputFolder)
        print("made folder!")

    # run example scan
    print("\nRunning Demo Scan!")
    scAnt.scan_stepSize = [200, 800, 5000]
    scAnt.setScanRange(stepper=0, min=0, max=250, step=50)
    scAnt.setScanRange(stepper=1, min=0, max=1600, step=400)
    scAnt.setScanRange(stepper=2, min=-20000, max=-5000, step=5000)

    scAnt.runScan()

    # de-energise steppers and release cam
    scAnt.deEnergise()
    scAnt.cam.exit_cam()

    print("\nDemo completed successfully!")
