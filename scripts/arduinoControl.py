import time
import numpy as np
# import os
# import math
from re import findall
from pathlib import Path
import serial
import serial.tools.list_ports

class ScannerController:
    def __init__(self):
        self.controller_type = "Arduino"
        self.gear_ratio = 5.18

        self.stepper_names = ["X", "Y", "Z"]
        self.scan_stepSize = [50, 80, 500]
        self.stepper_position = [None, None, None]
        self.stepper_home = ['rev', None, 'rev']

        com = None
        ports = serial.tools.list_ports.comports()
        for port, desc, _ in ports:
            print(port, desc)
            ard_desc = ["USB-SERIAL CH340", "USB2.0-Ser!", "Arduino"]
            ard_desc = [s.lower() for s in ard_desc]
            if any(findall("|".join(ard_desc), desc.lower())):
                com = port

        if com:
            self.ser = serial.Serial(com, baudrate=9600, timeout=None)
            time.sleep(2)
            print("Arduino found on port:" + com)
        else:
            self.ser=None
            print("No Serial Connection to Arduino")


        self.flash_length = "300"
        self.setLength(self.flash_length)

        #Change Microstepping Resolution here
        # 1 = Full Step
        # 2 = Half Step
        # 4 = Quater Step
        # 8 = Eighth Step
        # 16 = Sixteenth Step
        self.stepper_stepMode = 8
        self.setStepMode(self.stepper_stepMode)

        self.stepper_maxPos = [450, 1600, 7000]
        self.stepper_minPos = [0, -1600, 0]

        # self.stepper_position = [None, None, None]
        self.scan_pos = [None, None, None]
        self.setScanRange(stepper=0, min=0, max=450, step=self.scan_stepSize[0])
        self.setScanRange(stepper=1, min=-1600, max=1600, step=self.scan_stepSize[1])
        self.setScanRange(stepper=2, min=0, max=7000, step=self.scan_stepSize[2])

        
        # keep track of position during scanning, skip to next full rotation of Y Axis
        self.completedRotations = 0
        self.completedStacks = 0

    def deEnergise(self):
        print("De-engergising Steppers")
        self.ser.write("DEENERGISE     \n".encode("utf-8"))
        self.ser.readline()

    def resume(self):
        print("Energising Steppers")
        self.ser.write("ENERGISE       \n".encode("utf-8"))
        self.ser.readline()

    def setStepMode(self, step_mode):

        #For a4988:
            # if step_mode == 1:
            #     ms_pins = [0, 0, 0]
            # elif step_mode == 2:
            #     ms_pins = [1, 0, 0]
            # elif step_mode == 4:
            #     ms_pins = [0, 1, 0]
            # elif step_mode == 8:
            #     ms_pins = [1, 1, 0]
            # elif step_mode == 16:
            #     ms_pins = [1, 1, 1]
            # else:
            #     ms_pins = [1, 1, 0] #Eighth as default
        #----------------------------------------------------------------
        #For TMC2208:
            # if step_mode == 2:
            #   ms_pins = [1,0]
            # elif step_mode == 4:
            #   ms_pins = [0,1]
            # elif step_mode == 8:
            #   ms_pins = [0,0]
            # elif step_mode == 16:
            #   ms_pins = [1,1]

        # print("Setting up step resolution")
        command = "STEPMODE " + str(step_mode) + "     \n"
        self.ser.write(command.encode("utf-8"))
        print(self.ser.readline())

    def moveToPosition(self, stepper, pos):

        if self.stepper_names[stepper] == "X":
            pos = str(int(self.gear_ratio*pos))
        else:
            pos = str(pos)
        num_space = 8 - len(pos)
        spaces = " " * num_space
        command = "MOVE " + str(self.stepper_names[stepper]) + " " + pos + spaces + "\n"
        self.ser.write(command.encode("utf-8"))
        print(self.ser.readline())
        self.getStepperPosition(stepper)
    
    def getStepperPosition(self, stepper):
        command = "GETPOS " + self.stepper_names[stepper] + "       \n"
        self.ser.write(command.encode("utf-8"))
        print(self.ser.readline())
        new_pos = int(self.ser.readline().decode("utf-8"))
        print("Current pos = " + str(new_pos))
        self.stepper_position[stepper] = new_pos
        return new_pos
    
    def home(self, stepper):
        if self.stepper_home[stepper] is not None:  
            print("Homing", str(self.stepper_names[stepper]))
            command = "HOME " + str(self.stepper_names[stepper]) + "         \n"
            self.ser.write(command.encode("utf-8"))
            for _ in range(2):
                print(self.ser.readline())
        else:
            print("Resetting Y axis")
            command = "RESET_Y        \n"
            self.ser.write(command.encode("utf-8"))
            print(self.ser.readline())
    
    # def setDelay(self, delay):
    #     num_space = 6 - len(delay)
    #     spaces = " " * num_space
    #     command = "SET_DELAY " + delay + spaces + "\n"
    #     self.ser.write(command.encode("utf-8"))
    #     for _ in range(2):
    #         print(self.ser.readline())
    
    def setLength(self, length):
        num_space = 5 - len(length)
        spaces = " " * num_space
        command = "SET_LENGTH " + length + spaces + "\n"
        self.ser.write(command.encode("utf-8"))
        for _ in range(2):
            print(self.ser.readline())

    def flash(self):
        command = "FLASH_LIGHT     \n"
        self.ser.write(command.encode("utf-8"))
        print(self.ser.readline())

    def setScanRange(self, stepper, min, max, step):
        # set min and max poses according to input (within range)
        if max >= self.stepper_maxPos[stepper]:
            max = self.stepper_maxPos[stepper]
        elif min <= self.stepper_minPos[stepper]:
            min = self.stepper_minPos[stepper]

        # set desired step size (limited by GUI inputs as well as min and max values)
        self.scan_stepSize[stepper] = step

        self.scan_pos[stepper] = np.array(np.arange(int(min), int(max), int(self.scan_stepSize[stepper])), dtype=int)
        if len(self.scan_pos[stepper]) == 0:
            print("INPUT ERROR FOUND!")
            self.scan_pos[stepper] = np.array([0])


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

    # def runScan(self):
    #     for posX in self.scan_pos[0]:
    #         self.moveToPosition(0, posX)
    #         for posY in self.scan_pos[1]:
    #             self.moveToPosition(1, posY + self.completedRotations * self.stepper_maxPos[1])
    #             for posZ in self.scan_pos[2]:
    #                 self.moveToPosition(2, posZ)
    #                 # to follow the naming convention when focus stacking
    #                 # img_name = self.outputFolder + "x_" + self.correctName(posX) + "_y_" + self.correctName(
    #                 #     posY) + "_step_" + self.correctName(posZ) + "_.tif"

    #                 # self.cam.capture_image(img_name=img_name)
    #                 # self.progress = self.getProgress()

    #             self.completedStacks += 1

    #         self.completedRotations += 1

    #     # return to default position
    #     print("Returning to default position")
    #     scAnt.moveToPosition(stepper=0, pos=190)
    #     scAnt.moveToPosition(stepper=1, pos=self.completedRotations * self.stepper_maxPos[1])
    #     scAnt.moveToPosition(stepper=2, pos=190)
    
if __name__ == "__main__":
    # try:
    #     from GUI.Live_view_FLIR import customFLIR
    # except ModuleNotFoundError:
    #     print("WARNING: PySpin module not found! You can ignore this message when not using FLIR cameras.")
    print("Testing funcitonality of components")
    scAnt = ScannerController()
    scAnt.resume()
    # scAnt.initCam(customFLIR())

    # Home all steppers
    # for stepper in range(3):
    #     scAnt.home(stepper)

    # Movement test of steppers
    # scAnt.moveToPosition(stepper=0, pos=800)
    # scAnt.moveToPosition(stepper=0, pos=1600)
    # scAnt.moveToPosition(stepper=0, pos=800)
    # scAnt.moveToPosition(stepper=0, pos=0)
    
    # scAnt.moveToPosition(stepper=1, pos=800)
    # scAnt.moveToPosition(stepper=1, pos=1600)
    # scAnt.moveToPosition(stepper=1, pos=800)
    # scAnt.moveToPosition(stepper=1, pos=0)

    # scAnt.moveToPosition(stepper=2, pos=800)
    # scAnt.moveToPosition(stepper=2, pos=1600)
    # scAnt.moveToPosition(stepper=2, pos=800)
    # scAnt.moveToPosition(stepper=2, pos=0)

    # capture image, using custom FLIR scripts
    # scAnt.cam.capture_image(img_name="testy_mac_testface.tif")

    # # define output folder
    # scAnt.outputFolder = Path.cwd()
    # if not os.path.exists(scAnt.outputFolder):
    #     os.makedirs(scAnt.outputFolder)
    #     print("made folder!")

    # # run example scan
    # print("\nRunning Demo Scan!")
    # scAnt.scan_stepSize = [200, 800, 5000]
    # scAnt.setScanRange(stepper=0, min=0, max=250, step=50)
    # scAnt.setScanRange(stepper=1, min=0, max=1600, step=400)
    # scAnt.setScanRange(stepper=2, min=0, max=2000, step=500)

    # scAnt.runScan()

    # # de-energise steppers and release cam
    # scAnt.deEnergise()
    # # scAnt.cam.exit_cam()

    # print("\nDemo completed successfully!")
    scAnt.flash()


    
    