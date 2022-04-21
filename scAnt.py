import datetime
import time
import sys
import traceback
import os
import cgitb
from pathlib import Path
from PyQt5 import QtWidgets, QtGui, QtCore

from GUI.scAnt_GUI_mw import Ui_MainWindow  # importing main window of the GUI

import scripts.project_manager as ymlRW
from scripts.Scanner_Controller import ScannerController
from scripts.processStack import getThreads, stack_images, mask_images
from scripts.write_meta_data import write_exif_to_img, get_default_values

"""
Locations of required executables and how to use them:
"""


# qt designer located at:
# C:\Users\PlumStation\Anaconda3\envs\tf-gpu\Lib\site-packages\pyqt5_tools\Qt\bin\designer.exe
# pyuic5 to convert UI to executable python code is located at:
# C:\Users\PlumStation\Anaconda3\envs\tf-gpu\Scripts\pyuic5.exe
# to convert the UI into the required .py file run:
# -x = generates extra code to make ui.py file executable     -o = output
# pyuic5.exe -x "I:\3D_Scanner\scAnt\GUI\test.ui" -o "I:\3D_Scanner\scAnt\GUI\test.py"
# or alternatively on Ubuntu
# pyuic5 scAnt_GUI_mw.ui -o scAnt_GUI_mw.py

class WorkerSignals(QtCore.QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    '''
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)


class Worker(QtCore.QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @QtCore.pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done


class scAnt_mainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(scAnt_mainWindow, self).__init__()

        self.setWindowIcon(QtGui.QIcon(str(Path.cwd().joinpath("images", "scAnt_icon.png"))))

        self.liveView = False

        self.exit_program = False

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)

        self.set_project_title()

        self.ui.pushButton_startLiveView.pressed.connect(self.begin_live_view)

        self.ui.pushButton_captureImage.pressed.connect(self.capture_image)

        self.ui.lineEdit_projectName.textChanged.connect(self.set_project_title)

        # start thread pool
        self.threadpool = QtCore.QThreadPool()

        # search for cameras connected to the computer and supported by installed drivers
        self.camera_type = None
        self.camera_model = None
        self.file_format = ".tif"
        self.DSLR_read_out = False
        self.ActiveSavingProcess = False

        # Find FLIR cameras, if attached
        try:
            from GUI.Live_view_FLIR import customFLIR
            self.FLIR = customFLIR()
            # camera needs to be initialised before use (self.cam.initialise_camera)
            # all detected FLIR cameras are listed in self.cam.device_names
            # by default, use the first camera found in the list
            self.cam = self.FLIR
            self.cam.initialise_camera(select_cam=0)
            # now retrieve the name of all found FLIR cameras and add them to the camera selection
            for cam in self.cam.device_names:
                self.ui.comboBox_selectCamera.addItem(str(cam[0] + " ID: " + cam[1]))
            self.camera_type = "FLIR"
            # cam.device_names contains both model and serial number
            self.camera_model = self.cam.device_names[0][0]
            self.FLIR_found = True
            self.FLIR_image_queue = []
        except IndexError:
            message = "No FLIR camera found!"
            self.log_info(message)
            print(message)
            self.FLIR_found = False
            self.disable_FLIR_inputs()
        except ModuleNotFoundError:
            message = "PYSPIN has not been installed - Disabling FLIR camera inputs"
            self.log_info(message)
            print(message)
            self.FLIR_found = False
            self.disable_FLIR_inputs()

        try:
            # TODO add support for the selection of multiple connected DSLR cameras
            from GUI.Live_view_DSLR import customDSLR
            self.DSLR_initialised = False
            self.DSLR = customDSLR()
            self.log_info("Found " + str(self.DSLR.camera_model))

            self.ui.comboBox_selectCamera.addItem(str(self.DSLR.camera_model))
            self.DSLR_found = True
            if not self.FLIR_found:
                self.ui.stacked_camera_settings.setCurrentIndex(1)
                self.cam = self.DSLR
                self.camera_type = "DSLR"
                self.camera_model = self.DSLR.camera_model
                # initialise DSLR by launching an instance of DigiCamControl
                worker = Worker(self.launch_DCC_threaded)
                worker.signals.finished.connect(self.finished_DCC_launch)

                self.threadpool.start(worker)

        except:
            self.log_info("No DSLR camera found!")
            self.DSLR_found = False

        # connect camera selection combo box to respective function
        self.ui.comboBox_selectCamera.currentTextChanged.connect(self.select_camera)

        try:
            self.scanner = ScannerController()
            self.scanner_initialised = True
        except IndexError:
            self.scanner_initialised = False
            self.disable_stepper_inputs()
            warning = "No Stepper Controller found!"
            self.log_info(warning)
            print(warning)

        # FLIR settings

        self.ui.checkBox_exposureAuto.stateChanged.connect(self.check_exposure)

        self.ui.doubleSpinBox_exposureTime.valueChanged.connect(self.set_exposure_manual)

        self.ui.checkBox_gainAuto.stateChanged.connect(self.check_gain)

        self.ui.doubleSpinBox_gainLevel.valueChanged.connect(self.set_gain_manual)

        self.ui.doubleSpinBox_gamma.valueChanged.connect(self.set_gamma)

        self.ui.doubleSpinBox_balanceRatioRed.valueChanged.connect(self.set_balance_ratio)

        self.ui.doubleSpinBox_balanceRatioBlue.valueChanged.connect(self.set_balance_ratio)

        # TODO Add support for Black level selection
        # self.ui.doubleSpinBox_blackLevel.valueChanged.connect(self.set_black_level)

        # DSLR settings
        self.ui.comboBox_shutterSpeed.currentTextChanged.connect(self.set_shutterspeed)

        self.ui.comboBox_aperture.currentTextChanged.connect(self.set_aperture)

        self.ui.comboBox_iso.currentTextChanged.connect(self.set_iso)

        self.ui.comboBox_whiteBalance.currentTextChanged.connect(self.set_whitebalance)

        self.ui.comboBox_compression.currentTextChanged.connect(self.set_compression)

        # Stepper settings

        self.ui.pushButton_xHome.pressed.connect(self.homeX)

        self.ui.pushButton_yReset.pressed.connect(self.resetY)

        self.ui.pushButton_zHome.pressed.connect(self.homeZ)

        self.ui.pushButton_stepperDeEnergise.pressed.connect(self.deEnergise)

        self.ui.pushButton_Energise.pressed.connect(self.energise)

        self.ui.horizontalSlider_xAxis.sliderReleased.connect(self.moveStepperX)

        self.ui.horizontalSlider_xAxis.valueChanged.connect(self.updateDisplayX)

        self.ui.horizontalSlider_yAxis.sliderReleased.connect(self.moveStepperY)

        self.ui.horizontalSlider_yAxis.valueChanged.connect(self.updateDisplayY)

        self.ui.horizontalSlider_zAxis.sliderReleased.connect(self.moveStepperZ)

        self.ui.horizontalSlider_zAxis.valueChanged.connect(self.updateDisplayZ)

        if self.scanner_initialised:
            # disable stepper control before they have been homed (except for y axis)
            self.deEnergise()
            self.homed_X = False
            self.homed_Z = False
            self.ui.horizontalSlider_xAxis.setEnabled(False)
            self.ui.horizontalSlider_zAxis.setEnabled(False)
            self.resetY()

            # get default scanner Range
            self.ui.doubleSpinBox_xMin.setValue(self.scanner.scan_pos[0][0])
            self.ui.doubleSpinBox_xMax.setValue(self.scanner.scan_pos[0][-1] + self.scanner.scan_stepSize[0])
            self.ui.doubleSpinBox_yMin.setValue(self.scanner.scan_pos[1][0])
            self.ui.doubleSpinBox_yMax.setValue(self.scanner.scan_pos[1][-1] + self.scanner.scan_stepSize[1])
            self.ui.doubleSpinBox_zMin.setValue(self.scanner.scan_pos[2][0])
            self.ui.doubleSpinBox_zMax.setValue(self.scanner.scan_pos[2][-1] + self.scanner.scan_stepSize[2])

            # adjust scanner range on input
            self.ui.doubleSpinBox_xMin.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_xStep.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_xMax.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_yMin.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_yStep.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_yMax.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_zMin.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_zStep.valueChanged.connect(self.setScannerRange)
            self.ui.doubleSpinBox_zMax.valueChanged.connect(self.setScannerRange)

            self.images_to_take = len(self.scanner.scan_pos[0]) * len(self.scanner.scan_pos[1]) * len(
                self.scanner.scan_pos[2])

        self.images_taken = 0
        self.progress = 0

        self.ui.pushButton_startScan.pressed.connect(self.runScanAndReport)

        self.xMoving = False
        self.yMoving = False
        self.zMoving = False

        self.posX = 0
        self.posY = 0
        self.posZ = 0

        self.abortScan = False
        self.scanInProgress = False

        self.showExposure = False

        # Scanner output setup
        self.output_location = str(Path.cwd())
        self.update_output_location()
        self.ui.pushButton_browseOutput.pressed.connect(self.set_output_location)

        self.output_location_folder = Path(self.output_location).joinpath(self.ui.lineEdit_projectName.text())

        # processing
        self.stackImages = False
        self.stackMethod = "Default"
        self.stackFocusThreshold = 10.0
        self.stackDisplayFocus = False
        self.stackSharpen = False
        self.ui.checkBox_stackImages.stateChanged.connect(self.enableStacking)

        self.maskImages = False
        self.maskThreshMin = 215
        self.maskThreshMax = 240
        self.maskArtifactSizeBlack = 1000
        self.maskArtifactSizeWhite = 2000
        self.ui.checkBox_maskImages.stateChanged.connect(self.enableMasking)

        # once the scan has been started check if new sets of images are available for stacking
        self.timerStack = QtCore.QTimer(self)
        self.timerStack.timeout.connect(self.checkActiveStackThreads)

        self.exif = get_default_values()
        self.createCutout = True

        # use config file
        self.loadedConfig = False
        self.ui.pushButton_browsePresets.pressed.connect(self.loadConfig)

        self.ui.pushButton_saveConfig.pressed.connect(self.writeConfig)

        # stack and mask images
        self.maxStackThreads = max(min([int(getThreads() / 6), 2]), 1)
        # run no more than 3 stacking threads simultaneously but no less than 1
        self.postScanStacking = False
        self.activeThreads = 0
        self.stackList = []

    """
    Stepper Control
    """

    def setScannerRange(self):
        self.scanner.setScanRange(stepper=0, min=self.ui.doubleSpinBox_xMin.value(),
                                  max=self.ui.doubleSpinBox_xMax.value() + self.ui.doubleSpinBox_xStep.value(),
                                  step=self.ui.doubleSpinBox_xStep.value())
        self.scanner.setScanRange(stepper=1, min=self.ui.doubleSpinBox_yMin.value(),
                                  max=self.ui.doubleSpinBox_yMax.value() + self.ui.doubleSpinBox_yStep.value(),
                                  step=self.ui.doubleSpinBox_yStep.value())
        self.scanner.setScanRange(stepper=2, min=self.ui.doubleSpinBox_zMin.value(),
                                  max=self.ui.doubleSpinBox_zMax.value() + self.ui.doubleSpinBox_zStep.value(),
                                  step=self.ui.doubleSpinBox_zStep.value())

    def updateDisplayX(self):
        pos = self.ui.horizontalSlider_xAxis.value()
        self.ui.lcdNumber_xAxis.display(pos)

    def updateDisplayY(self):
        pos = self.ui.horizontalSlider_yAxis.value()
        self.ui.lcdNumber_yAxis.display(pos)

    def updateDisplayZ(self):
        pos = self.ui.horizontalSlider_zAxis.value()
        self.ui.lcdNumber_zAxis.display(pos)

    def energise(self):
        self.scanner.resume()
        self.log_info("Energised steppers")

    def deEnergise(self):
        self.scanner.deEnergise()
        self.log_info("De-energised steppers")
        self.ui.horizontalSlider_xAxis.setEnabled(False)
        self.ui.horizontalSlider_zAxis.setEnabled(False)
        self.homed_X = False
        self.homed_Z = False

    def homeX_threaded(self, progress_callback):
        self.ui.horizontalSlider_xAxis.setEnabled(False)
        self.scanner.home(0)
        self.log_info("Homed X Axis")
        self.ui.horizontalSlider_xAxis.setEnabled(True)
        self.scanner.getStepperPosition(0)
        self.ui.lcdNumber_xAxis.display(self.scanner.stepper_position[0])
        self.ui.horizontalSlider_xAxis.setValue(self.scanner.stepper_position[0])
        self.homed_X = True
        self.posX = 0

    def homeZ_threaded(self, progress_callback):
        self.ui.horizontalSlider_zAxis.setEnabled(False)
        self.scanner.home(2)
        self.log_info("Homed Z Axis")
        self.ui.horizontalSlider_zAxis.setEnabled(True)
        self.scanner.getStepperPosition(2)
        self.ui.lcdNumber_zAxis.display(self.scanner.stepper_position[2])
        self.ui.horizontalSlider_zAxis.setValue(self.scanner.stepper_position[2])
        self.homed_Z = True
        self.posZ = 0

    def homeX(self):
        worker = Worker(self.homeX_threaded)
        self.threadpool.start(worker)

    def resetY(self):
        self.ui.horizontalSlider_yAxis.setValue(0)
        self.updateDisplayY()
        self.scanner.home(1)
        self.log_info("Reset Y Axis")

    def homeZ(self):
        worker = Worker(self.homeZ_threaded)
        self.threadpool.start(worker)

    def moveStepperX_threaded(self, progress_callback):
        self.ui.horizontalSlider_xAxis.setEnabled(False)
        self.ui.pushButton_xHome.setEnabled(False)
        pos = self.ui.horizontalSlider_xAxis.value()
        self.scanner.moveToPosition(stepper=0, pos=pos)
        self.ui.horizontalSlider_xAxis.setEnabled(True)
        self.ui.pushButton_xHome.setEnabled(True)
        self.posX = pos
        self.xMoving = False

    def moveStepperX(self):
        self.xMoving = True
        worker = Worker(self.moveStepperX_threaded)
        self.threadpool.start(worker)

    def moveStepperY_threaded(self, progress_callback):
        self.ui.pushButton_yReset.setEnabled(False)
        self.ui.horizontalSlider_yAxis.setEnabled(False)
        pos = self.ui.horizontalSlider_yAxis.value()
        self.scanner.moveToPosition(stepper=1, pos=pos)
        self.ui.horizontalSlider_yAxis.setEnabled(True)
        self.ui.pushButton_yReset.setEnabled(True)
        self.posY = pos
        self.yMoving = False

    def moveStepperY(self):
        self.yMoving = True
        worker = Worker(self.moveStepperY_threaded)
        self.threadpool.start(worker)

    def moveStepperZ_threaded(self, progress_callback):
        self.ui.pushButton_zHome.setEnabled(False)
        self.ui.horizontalSlider_zAxis.setEnabled(False)
        pos = self.ui.horizontalSlider_zAxis.value()
        self.scanner.moveToPosition(stepper=2, pos=pos)
        self.ui.horizontalSlider_zAxis.setEnabled(True)
        self.ui.pushButton_zHome.setEnabled(True)
        self.posZ = pos
        self.zMoving = False

    def moveStepperZ(self):
        self.zMoving = True
        worker = Worker(self.moveStepperZ_threaded)
        self.threadpool.start(worker)

    """
    Camera Settings
    """

    def select_camera(self):
        self.disable_FLIR_inputs()
        self.disable_DSLR_inputs()
        selected_camera = self.ui.comboBox_selectCamera.currentText()
        self.log_info("Selected camera: " + str(selected_camera))

        # stop the live view if currently in use
        if self.liveView:
            self.begin_live_view()  # sets live view false if already running

        # de-initialised previous FLIR, if it was in use
        if self.camera_type == "FLIR":
            # de-initialise the previous camera before setting up the newly selected one
            self.cam.deinitialise_camera()

        # new camera -> FLIR
        if selected_camera.split(" ")[0] == "Blackfly":
            for ID, FLIR in enumerate(self.FLIR.device_names):
                if self.ui.comboBox_selectCamera.currentText() == str(FLIR[0] + " ID: " + FLIR[1]):
                    self.cam = self.FLIR
                    self.cam.initialise_camera(select_cam=ID)
                    self.log_info("Camera in use: " + str(FLIR[0] + " ID: " + FLIR[1]))
                    self.camera_type = "FLIR"
                    self.begin_live_view()
                    self.camera_model = self.FLIR.device_names[ID][0]
                    self.enable_FLIR_inputs()
                    self.file_format = ".tif"

        # new camera -> DSLR
        else:
            self.cam = self.DSLR
            self.camera_type = "DSLR"
            self.camera_model = self.DSLR.camera_model
            # initialise DSLR by launching an instance of DigiCamControl
            worker = Worker(self.launch_DCC_threaded)
            worker.signals.finished.connect(self.finished_DCC_launch)

            self.threadpool.start(worker)

    def launch_DCC_threaded(self, progress_callback):
        self.cam.initialise_camera()
        self.DSLR_initialised = True

    def finished_DCC_launch(self):
        self.log_info("Launched DCC and retrieved camera settings")
        self.enable_DSLR_inputs()

    # FLIR Settings

    def check_exposure(self):
        if self.ui.checkBox_exposureAuto.isChecked():
            self.set_exposure_auto()
        else:
            self.set_exposure_manual()

    def set_exposure_auto(self):
        self.cam.reset_exposure()
        self.ui.label_exposureTime.setEnabled(False)
        self.ui.doubleSpinBox_exposureTime.setEnabled(False)
        self.log_info("Enabled automatic exposure")

    def set_exposure_manual(self):
        self.ui.label_exposureTime.setEnabled(True)
        self.ui.doubleSpinBox_exposureTime.setEnabled(True)
        value = self.ui.doubleSpinBox_exposureTime.value()
        if value is not None:
            self.log_info("Exposure time set to " + str(value) + " [us]")
            self.cam.configure_exposure(float(value))

    def check_gain(self):
        if self.ui.checkBox_gainAuto.isChecked():
            self.set_gain_auto()
        else:
            self.set_gain_manual()

    def set_gain_auto(self):
        self.cam.reset_gain()
        self.ui.label_gainLevel.setEnabled(False)
        self.ui.doubleSpinBox_gainLevel.setEnabled(False)
        self.log_info("Enabled automatic exposure")

    def set_gain_manual(self):
        self.ui.label_gainLevel.setEnabled(True)
        self.ui.doubleSpinBox_gainLevel.setEnabled(True)
        value = self.ui.doubleSpinBox_gainLevel.value()
        if value is not None:
            self.log_info("Gain level set to " + str(value) + " [dB]")
            self.cam.set_gain(float(value))

    def set_gamma(self):
        value = self.ui.doubleSpinBox_gamma.value()
        if value is not None:
            self.log_info("Gain set to " + str(value))
            self.cam.set_gamma(float(value))

    def set_balance_ratio(self):
        value_red = self.ui.doubleSpinBox_balanceRatioRed.value()
        value_blue = self.ui.doubleSpinBox_balanceRatioBlue.value()
        if value_red is not None and value_blue is not None:
            self.log_info("White balance ratio set to " + str(value_red) + " and " + str(value_blue))
            self.cam.set_white_balance(float(value_red), float(value_blue))

    def set_black_level(self):
        # TODO -> not yet functional, error thrown from PySpin
        value = self.ui.doubleSpinBox_blackLevel.value()
        if value is not None:
            self.log_info("Gain set to " + str(value))
            self.cam.set_black_level(float(value))

    def update_live_view(self, progress_callback):
        while self.liveView and self.camera_type == "FLIR":
            try:
                img = self.cam.live_view()
                # if enabled, display exposure as histogram and highlight over exposed areas
                if self.ui.checkBox_highlightExposure.isChecked():
                    img = self.cam.showExposure(img)

                live_img = QtGui.QImage(img, img.shape[1], img.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
                live_img_pixmap = QtGui.QPixmap.fromImage(live_img)

                # Setup pixmap with the acquired image
                live_img_scaled = live_img_pixmap.scaled(self.ui.label_liveView.width(),
                                                         self.ui.label_liveView.height(),
                                                         QtCore.Qt.KeepAspectRatio)
                # Set the pixmap onto the label
                self.ui.label_liveView.setPixmap(live_img_scaled)
                # Align the label to center
                self.ui.label_liveView.setAlignment(QtCore.Qt.AlignCenter)
            except AttributeError:
                print("Live view ended")
        self.ui.label_liveView.setText("Live view disabled.")

    # DSLR settings

    def set_shutterspeed(self):
        if not self.DSLR_read_out:
            self.cam.set_shutterspeed(self.ui.comboBox_shutterSpeed.currentText())
            self.log_info("Set shutter speed to " + self.ui.comboBox_shutterSpeed.currentText())

    def set_aperture(self):
        if not self.DSLR_read_out:
            self.cam.set_aperture(self.ui.comboBox_aperture.currentText())
            self.log_info("Set aperture to " + self.ui.comboBox_aperture.currentText())

    def set_iso(self):
        if not self.DSLR_read_out:
            self.cam.set_iso(self.ui.comboBox_iso.currentText())
            self.log_info("Set iso to " + self.ui.comboBox_iso.currentText())

    def set_whitebalance(self):
        if not self.DSLR_read_out:
            self.cam.set_whitebalance(self.ui.comboBox_whiteBalance.currentText())
            self.log_info("Set white balance to " + self.ui.comboBox_whiteBalance.currentText())

    def set_compression(self):
        if not self.DSLR_read_out:
            self.cam.set_compression(self.ui.comboBox_compression.currentText())
            self.log_info("Set compression to " + self.ui.comboBox_compression.currentText())

    def get_DSLR_file_ending(self):
        # first get the current compression setting
        compression_setting = self.cam.get_current_setting("compressionsetting")
        if compression_setting.split(" ")[0] == "JPEG":
            self.file_format = ".jpg"
        elif compression_setting.split(" ")[0] == "RAW":
            # different cameras use different RAW format endings
            brand = self.camera_model.split(" ")[0]
            # Nikon cameras are simply named D###
            if brand[0] == "D":
                self.file_format = ".nef"
            # Canon cameras use their brand name directly
            elif brand == "Canon":
                self.file_format = ".CR2"
        else:
            self.file_format = ".jpg"
            self.log_warning("Unknown image file format! Using JPEG as default!")
        # Info & Threading functions

    def log_info(self, info):
        now = datetime.datetime.now()
        self.ui.listWidget_log.addItem(now.strftime("%H:%M:%S") + " [INFO] " + info)
        self.ui.listWidget_log.sortItems(QtCore.Qt.DescendingOrder)

    def log_warning(self, warning):
        now = datetime.datetime.now()
        self.ui.listWidget_log.addItem(now.strftime("%H:%M:%S") + " [ERROR] " + warning)
        self.ui.listWidget_log.sortItems(QtCore.Qt.DescendingOrder)

    def thread_complete(self):
        self.ui.pushButton_startScan.setText("Start Scan")
        self.scanInProgress = False
        self.changeInputState()
        self.log_info("Scanning completed!")

    def begin_live_view(self):
        if not self.liveView:
            self.log_info("Began camera live view")
            self.ui.pushButton_startLiveView.setText("Stop Live View")
            self.liveView = True

            if self.camera_type == "FLIR":
                worker = Worker(self.update_live_view)
                self.threadpool.start(worker)
            else:
                # starts live view in external Window
                self.ui.label_liveView.setText("Live view opened in external DCC window!")
                self.cam.start_live_view()

        else:
            self.ui.label_liveView.setText("Live view disabled.")
            self.ui.pushButton_startLiveView.setText("Start Live View")
            self.log_info("Ended camera live view")
            self.liveView = False

            if self.camera_type == "DSLR":
                self.cam.stop_live_view()

    def capture_image(self):
        now = datetime.datetime.now()

        self.create_output_folders()
        # create unique filename
        file_name = str(self.output_location_folder.joinpath(now.strftime("%Y-%m-%d_%H-%M-%S-%MS_" + self.file_format)))
        self.cam.capture_image(file_name)
        self.log_info("Captured " + file_name)

    def create_output_folders(self):
        self.output_location_folder = Path(self.output_location).joinpath(self.ui.lineEdit_projectName.text())
        if not os.path.exists(self.output_location_folder):
            os.makedirs(self.output_location_folder)
            self.log_info("Created folder at:" + str(self.output_location_folder))
        if not os.path.exists(self.output_location_folder.joinpath("RAW")):
            os.makedirs(self.output_location_folder.joinpath("RAW"))
        if not os.path.exists(self.output_location_folder.joinpath("stacked")):
            os.makedirs(self.output_location_folder.joinpath("stacked"))

    """
    Scanner Setup
    """

    def getProgress(self):
        self.progress = min(int(100 * (self.images_taken / self.images_to_take)), 100)

    def set_project_title(self):
        name = self.ui.lineEdit_projectName.text()
        self.setWindowTitle("scAnt V 1.2  :  " + name)

    def set_output_location(self):
        new_location = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose output location",
                                                                  str(Path.cwd()))
        if new_location:
            self.output_location = new_location

        self.update_output_location()

    def loadConfig(self):
        file = QtWidgets.QFileDialog.getOpenFileName(self, "Load existing config file",
                                                     str(Path.cwd()), "config file (*.yaml)")
        config_location = file[0]
        if config_location:
            # if a file has been selected, convert it into a Path object
            config_location = Path(config_location)
            config = ymlRW.read_config_file(config_location)

            # check if the camera type in the config file matches the connected/selected camera type
            if config["general"]["camera_type"] != self.camera_type:
                self.log_warning("The selected config file was generated for a different camera type!")
                QtWidgets.QMessageBox.critical(self, "Failed to load " + str(config_location.name),
                                               "The selected config file was generated for a different camera type!")
                return

            # camera_settings:

            if config["general"]["camera_type"] == "FLIR":
                # FLIR
                self.ui.doubleSpinBox_exposureTime.setValue(config["camera_settings"]["exposure_time"])
                if config["camera_settings"]["exposure_auto"]:
                    self.ui.checkBox_exposureAuto.setChecked(True)
                else:
                    self.set_exposure_manual()

                self.ui.doubleSpinBox_gainLevel.setValue(config["camera_settings"]["gain_level"])
                if config["camera_settings"]["gain_auto"]:
                    self.ui.checkBox_gainAuto.setChecked(True)
                else:
                    self.ui.checkBox_gainAuto.setChecked(False)

                self.ui.doubleSpinBox_gamma.setValue(config["camera_settings"]["gamma"])
                self.set_gamma()

                self.ui.doubleSpinBox_balanceRatioRed.setValue(config["camera_settings"]["balance_ratio_red"])
                self.ui.doubleSpinBox_balanceRatioBlue.setValue(config["camera_settings"]["balance_ratio_blue"])
                self.set_balance_ratio()

                # self.ui.doubleSpinBox_blackLevel.setValue(config["camera_settings"]["black_level"])
                # self.set_black_level()
            else:
                # DSLR
                self.ui.comboBox_shutterSpeed.setCurrentIndex(
                    self.ui.comboBox_shutterSpeed.findText(str(config["camera_settings"]["shutterspeed"])))
                self.ui.comboBox_aperture.setCurrentIndex(
                    self.ui.comboBox_aperture.findText(str(config["camera_settings"]["aperture"])))
                self.ui.comboBox_iso.setCurrentIndex(
                    self.ui.comboBox_iso.findText(str(config["camera_settings"]["iso"])))
                self.ui.comboBox_whiteBalance.setCurrentIndex(
                    self.ui.comboBox_whiteBalance.findText(str(config["camera_settings"]["whitebalance"])))
                self.ui.comboBox_compression.setCurrentIndex(
                    self.ui.comboBox_compression.findText(str(config["camera_settings"]["compression"])))

            if self.scanner_initialised:

                # scanner_settings
                self.ui.doubleSpinBox_xMin.setValue(config["scanner_settings"]["x_min"])
                self.ui.doubleSpinBox_yMin.setValue(config["scanner_settings"]["y_min"])
                self.ui.doubleSpinBox_zMin.setValue(config["scanner_settings"]["z_min"])

                self.ui.doubleSpinBox_xMax.setValue(config["scanner_settings"]["x_max"])
                self.ui.doubleSpinBox_yMax.setValue(config["scanner_settings"]["y_max"])
                self.ui.doubleSpinBox_zMax.setValue(config["scanner_settings"]["z_max"])

                self.ui.doubleSpinBox_xStep.setValue(config["scanner_settings"]["x_step"])
                self.ui.doubleSpinBox_yStep.setValue(config["scanner_settings"]["y_step"])
                self.ui.doubleSpinBox_zStep.setValue(config["scanner_settings"]["z_step"])

                self.setScannerRange()
            else:
                self.log_warning("Stepper controllers are not connected!")

            # stacking
            self.ui.checkBox_stackImages.setChecked(config["stacking"]["stack_images"])

            if config["stacking"]["stacking_method"] == "default":
                self.ui.comboBox_stackingMethod.setCurrentIndex(0)
            elif config["stacking"]["stacking_method"] == "1-star":
                self.ui.comboBox_stackingMethod.setCurrentIndex(1)
            elif config["stacking"]["stacking_method"] == "masks":
                self.ui.comboBox_stackingMethod.setCurrentIndex(2)

            self.stackFocusThreshold = config["stacking"]["threshold"]
            self.ui.spinBox_thresholdFocus.setValue(self.stackFocusThreshold)

            self.stackDisplayFocus = config["stacking"]["display_focus_check"]
            self.stackSharpen = config["stacking"]["additional_sharpening"]

            # masking
            self.ui.checkBox_maskImages.setChecked(config["masking"]["mask_images"])
            self.maskThreshMin = config["masking"]["mask_thresh_min"]
            self.ui.spinBox_thresholdMin.setValue(self.maskThreshMin)
            self.maskThreshMax = config["masking"]["mask_thresh_max"]
            self.ui.spinBox_thresholdMax.setValue(self.maskThreshMax)
            self.maskArtifactSizeBlack = config["masking"]["min_artifact_size_black"]
            self.maskArtifactSizeWhite = config["masking"]["min_artifact_size_white"]

            # meta data (exif)
            self.exif = config["exif_data"]

            self.loadedConfig = True
            self.log_info("Loaded config-file successfully!")

            print(config)

    def writeConfig(self):
        if self.ui.comboBox_stackingMethod.currentIndex() == 0:
            stacking_method = "default"
        elif self.ui.comboBox_stackingMethod.currentIndex() == 1:
            stacking_method = "1-star"
        elif self.ui.comboBox_stackingMethod.currentIndex() == 2:
            stacking_method = "mask"

        if self.camera_type == "DSLR":
            self.get_DSLR_file_ending()

        config = {'general': {'project_name': self.ui.lineEdit_projectName.text(),
                              'camera_type': self.camera_type,
                              'camera_model': self.camera_model,
                              },
                  'camera_settings': {'exposure_auto': self.ui.checkBox_exposureAuto.isChecked(),
                                      'exposure_time': self.ui.doubleSpinBox_exposureTime.value(),
                                      'gain_auto': self.ui.checkBox_gainAuto.isChecked(),
                                      'gain_level': self.ui.doubleSpinBox_gainLevel.value(),
                                      'gamma': self.ui.doubleSpinBox_gamma.value(),
                                      'balance_ratio_red': self.ui.doubleSpinBox_balanceRatioRed.value(),
                                      'balance_ratio_blue': self.ui.doubleSpinBox_balanceRatioBlue.value(),
                                      # values specific to DSLR cameras
                                      'shutterspeed': self.ui.comboBox_shutterSpeed.currentText(),
                                      'aperture': self.ui.comboBox_aperture.currentText(),
                                      'iso': self.ui.comboBox_iso.currentText(),
                                      'whitebalance': self.ui.comboBox_whiteBalance.currentText(),
                                      'compression': self.ui.comboBox_compression.currentText()
                                      },
                  'scanner_settings': {'x_min': self.ui.doubleSpinBox_xMin.value(),
                                       'x_max': self.ui.doubleSpinBox_xMax.value(),
                                       'x_step': self.ui.doubleSpinBox_xStep.value(),
                                       'y_min': self.ui.doubleSpinBox_yMin.value(),
                                       'y_max': self.ui.doubleSpinBox_yMax.value(),
                                       'y_step': self.ui.doubleSpinBox_yStep.value(),
                                       'z_min': self.ui.doubleSpinBox_zMin.value(),
                                       'z_max': self.ui.doubleSpinBox_zMax.value(),
                                       'z_step': self.ui.doubleSpinBox_zStep.value()},
                  'stacking': {'stack_images': self.ui.checkBox_stackImages.isChecked(),
                               'stacking_method': stacking_method,
                               'threshold': self.ui.spinBox_thresholdFocus.value(),
                               'display_focus_check': self.stackDisplayFocus,
                               'additional_sharpening': self.stackSharpen},
                  'masking': {'mask_images': self.ui.checkBox_maskImages.isChecked(),
                              'mask_thresh_min': self.ui.spinBox_thresholdMin.value(),
                              'mask_thresh_max': self.ui.spinBox_thresholdMax.value(),
                              'min_artifact_size_black': self.maskArtifactSizeBlack,
                              'min_artifact_size_white': self.maskArtifactSizeWhite},
                  "exif_data": self.exif}

        self.create_output_folders()
        ymlRW.write_config_file(config, Path(self.output_location_folder))
        self.log_info("Exported config_file successfully!")

    def update_output_location(self):
        self.ui.lineEdit_outputLocation.setText(self.output_location)

    def enableStacking(self, set_to=False):
        self.stackImages = self.ui.checkBox_stackImages.isChecked()

        self.ui.label_stackingMethod.setEnabled(self.stackImages)
        self.ui.comboBox_stackingMethod.setEnabled(self.stackImages)
        self.ui.label_thresholdFocus.setEnabled(self.stackImages)
        self.ui.spinBox_thresholdFocus.setEnabled(self.stackImages)
        self.ui.label_maskImages.setEnabled(self.stackImages)
        self.ui.checkBox_maskImages.setEnabled(self.stackImages)

    def enableMasking(self, set_to=False):
        self.maskImages = self.ui.checkBox_maskImages.isChecked()

        self.ui.label_thresholdMasking.setEnabled(self.maskImages)
        self.ui.label_thresholdMaskingMin.setEnabled(self.maskImages)
        self.ui.label_thresholdMaskingMax.setEnabled(self.maskImages)
        self.ui.spinBox_thresholdMin.setEnabled(self.maskImages)
        self.ui.spinBox_thresholdMax.setEnabled(self.maskImages)

    def displayProgress(self, progress):
        print("Displaying progress!")
        self.ui.progressBar_total.setValue(int(progress))
        self.ui.horizontalSlider_xAxis.setValue(self.posX)
        self.ui.horizontalSlider_yAxis.setValue(self.posY)
        self.ui.horizontalSlider_zAxis.setValue(self.posZ)
        self.ui.lcdNumber_xAxis.display(self.posX)
        self.ui.lcdNumber_yAxis.display(self.posY)
        self.ui.lcdNumber_zAxis.display(self.posZ)

    def disable_stepper_inputs(self):
        self.ui.horizontalSlider_xAxis.setEnabled(False)
        self.ui.horizontalSlider_yAxis.setEnabled(False)
        self.ui.horizontalSlider_zAxis.setEnabled(False)
        self.ui.pushButton_xHome.setEnabled(False)
        self.ui.pushButton_yReset.setEnabled(False)
        self.ui.pushButton_zHome.setEnabled(False)
        self.ui.doubleSpinBox_xMin.setEnabled(False)
        self.ui.doubleSpinBox_yMin.setEnabled(False)
        self.ui.doubleSpinBox_zMin.setEnabled(False)
        self.ui.doubleSpinBox_xStep.setEnabled(False)
        self.ui.doubleSpinBox_yStep.setEnabled(False)
        self.ui.doubleSpinBox_zStep.setEnabled(False)
        self.ui.doubleSpinBox_xMax.setEnabled(False)
        self.ui.doubleSpinBox_yMax.setEnabled(False)
        self.ui.doubleSpinBox_zMax.setEnabled(False)
        self.ui.pushButton_Energise.setEnabled(False)
        self.ui.pushButton_stepperDeEnergise.setEnabled(False)
        self.ui.pushButton_startScan.setEnabled(False)
        self.ui.lcdNumber_xAxis.setEnabled(False)
        self.ui.lcdNumber_yAxis.setEnabled(False)
        self.ui.lcdNumber_zAxis.setEnabled(False)

    def disable_FLIR_inputs(self):
        self.ui.checkBox_exposureAuto.setEnabled(False)
        self.ui.doubleSpinBox_exposureTime.setEnabled(False)
        self.ui.checkBox_gainAuto.setEnabled(False)
        self.ui.doubleSpinBox_gainLevel.setEnabled(False)
        self.ui.doubleSpinBox_gamma.setEnabled(False)
        self.ui.doubleSpinBox_balanceRatioBlue.setEnabled(False)
        self.ui.doubleSpinBox_balanceRatioRed.setEnabled(False)
        self.ui.pushButton_startLiveView.setEnabled(False)
        self.ui.pushButton_startScan.setEnabled(False)
        self.ui.pushButton_captureImage.setEnabled(False)
        self.ui.checkBox_highlightExposure.setEnabled(False)
        # self.ui.doubleSpinBox_blackLevel.setEnabled(False)

    def enable_FLIR_inputs(self):
        self.ui.stacked_camera_settings.setCurrentIndex(0)
        self.ui.checkBox_exposureAuto.setEnabled(True)
        self.ui.doubleSpinBox_exposureTime.setEnabled(True)
        self.ui.checkBox_gainAuto.setEnabled(True)
        self.ui.doubleSpinBox_gainLevel.setEnabled(True)
        self.ui.doubleSpinBox_gamma.setEnabled(True)
        self.ui.doubleSpinBox_balanceRatioBlue.setEnabled(True)
        self.ui.doubleSpinBox_balanceRatioRed.setEnabled(True)
        self.ui.pushButton_startLiveView.setEnabled(True)
        self.ui.pushButton_startScan.setEnabled(True)
        self.ui.pushButton_captureImage.setEnabled(True)
        self.ui.checkBox_highlightExposure.setEnabled(True)
        # self.ui.doubleSpinBox_blackLevel.setEnabled(False)

    def enable_DSLR_inputs(self):
        # disable setting changes based on read out values:
        self.DSLR_read_out = True
        # set the index of the stacked widget to 1 to access DSLR settings
        self.ui.stacked_camera_settings.setCurrentIndex(1)
        # set retrieved values as combo box entries for each setting.
        # Clear each combo box in case different options are available for different cameras
        self.ui.comboBox_shutterSpeed.clear()
        for shutterspeed in self.cam.all_shutterspeed_vals:
            self.ui.comboBox_shutterSpeed.addItem(shutterspeed)
        # set current value to the selected item
        self.ui.comboBox_shutterSpeed.setCurrentIndex(
            self.ui.comboBox_shutterSpeed.findText(self.cam.shutterspeed))

        self.ui.comboBox_aperture.clear()
        for aperture in self.cam.all_aperture_vals:
            self.ui.comboBox_aperture.addItem(aperture)
        # set current value to the selected item
        self.ui.comboBox_aperture.setCurrentIndex(
            self.ui.comboBox_aperture.findText(self.cam.aperture))

        self.ui.comboBox_iso.clear()
        for iso in self.cam.all_iso_vals:
            self.ui.comboBox_iso.addItem(iso)
        # set current value to the selected item
        self.ui.comboBox_iso.setCurrentIndex(
            self.ui.comboBox_iso.findText(self.cam.iso))

        self.ui.comboBox_whiteBalance.clear()
        for whitebalance in self.cam.all_whitebalance_vals:
            self.ui.comboBox_whiteBalance.addItem(whitebalance)
        # set current value to the selected item
        self.ui.comboBox_whiteBalance.setCurrentIndex(
            self.ui.comboBox_whiteBalance.findText(self.cam.whitebalance))

        self.ui.comboBox_compression.clear()
        for compression in self.cam.all_compression_vals:
            self.ui.comboBox_compression.addItem(compression)
        # set current value to the selected item
        self.ui.comboBox_compression.setCurrentIndex(
            self.ui.comboBox_compression.findText(self.cam.compression))

        # enable live_view/capture/scanning
        self.ui.pushButton_startLiveView.setEnabled(True)
        self.ui.pushButton_startScan.setEnabled(True)
        self.ui.pushButton_captureImage.setEnabled(True)

        # allow for changes to the setting boxes to affect the camera
        self.DSLR_read_out = False

        self.ui.comboBox_shutterSpeed.setEnabled(True)
        self.ui.comboBox_aperture.setEnabled(True)
        self.ui.comboBox_iso.setEnabled(True)
        self.ui.comboBox_whiteBalance.setEnabled(True)
        self.ui.comboBox_compression.setEnabled(True)

    def disable_DSLR_inputs(self):
        self.ui.pushButton_startScan.setEnabled(False)
        self.ui.pushButton_captureImage.setEnabled(False)
        self.ui.comboBox_shutterSpeed.setEnabled(False)
        self.ui.comboBox_aperture.setEnabled(False)
        self.ui.comboBox_iso.setEnabled(False)
        self.ui.comboBox_compression.setEnabled(False)
        self.ui.comboBox_whiteBalance.setEnabled(False)

    def changeInputState(self):
        enableInputs = True
        if self.scanInProgress:
            enableInputs = False
            print("disabling inputs!")
        else:
            print("enabling inputs!")
        # disable panels that could interfere with the scan
        # stepper motor inputs
        self.ui.horizontalSlider_xAxis.setEnabled(enableInputs)
        self.ui.horizontalSlider_yAxis.setEnabled(enableInputs)
        self.ui.horizontalSlider_zAxis.setEnabled(enableInputs)
        self.ui.pushButton_xHome.setEnabled(enableInputs)
        self.ui.pushButton_yReset.setEnabled(enableInputs)
        self.ui.pushButton_zHome.setEnabled(enableInputs)
        self.ui.doubleSpinBox_xMin.setEnabled(enableInputs)
        self.ui.doubleSpinBox_yMin.setEnabled(enableInputs)
        self.ui.doubleSpinBox_zMin.setEnabled(enableInputs)
        self.ui.doubleSpinBox_xStep.setEnabled(enableInputs)
        self.ui.doubleSpinBox_yStep.setEnabled(enableInputs)
        self.ui.doubleSpinBox_zStep.setEnabled(enableInputs)
        self.ui.doubleSpinBox_xMax.setEnabled(enableInputs)
        self.ui.doubleSpinBox_yMax.setEnabled(enableInputs)
        self.ui.doubleSpinBox_zMax.setEnabled(enableInputs)
        self.ui.pushButton_Energise.setEnabled(enableInputs)
        self.ui.pushButton_stepperDeEnergise.setEnabled(enableInputs)

        # camera selection
        self.ui.comboBox_selectCamera.setEnabled(enableInputs)

        # FLIR inputs
        self.ui.checkBox_exposureAuto.setEnabled(enableInputs)
        self.ui.doubleSpinBox_exposureTime.setEnabled(enableInputs)
        self.ui.checkBox_gainAuto.setEnabled(enableInputs)
        self.ui.doubleSpinBox_gainLevel.setEnabled(enableInputs)
        self.ui.doubleSpinBox_gamma.setEnabled(enableInputs)
        self.ui.doubleSpinBox_balanceRatioBlue.setEnabled(enableInputs)
        self.ui.doubleSpinBox_balanceRatioRed.setEnabled(enableInputs)
        # self.ui.doubleSpinBox_blackLevel.setEnabled(enableInputs)

        # DSLR inputs
        self.ui.comboBox_shutterSpeed.setEnabled(enableInputs)
        self.ui.comboBox_aperture.setEnabled(enableInputs)
        self.ui.comboBox_iso.setEnabled(enableInputs)
        self.ui.comboBox_compression.setEnabled(enableInputs)
        self.ui.comboBox_whiteBalance.setEnabled(enableInputs)

        # project name
        self.ui.lineEdit_projectName.setEnabled(enableInputs)

    def runScanAndReport(self):
        if not self.scanner_initialised:
            self.log_warning("No stepper drivers set up! Aborting scan!")
            self.abortScan = True
            return

        # if the used camera is a DSLR, adjust the file ending.
        if self.camera_type == "DSLR":
            self.get_DSLR_file_ending()

        if not self.scanInProgress:
            # create output folder
            self.create_output_folders()
            # save configuration file
            self.writeConfig()
            # enable and show progress
            self.ui.progressBar_total.setEnabled(True)
            self.ui.label_progressTotal.setEnabled(True)

            worker = Worker(self.runScanAndReport_threaded)
            worker.signals.progress.connect(self.displayProgress)
            worker.signals.finished.connect(self.thread_complete)

            if self.homed_X and self.homed_Z:
                if not self.xMoving and not self.yMoving and not self.zMoving:
                    self.ui.pushButton_startScan.setText("Abort Scan")
                    self.scanInProgress = True
                    self.changeInputState()
                    self.abortScan = False

                    # check for images in the saving & stacking Queue
                    print("Started background processing queue...")
                    # prioritise writing images over stacking until the scan is either completed or aborted
                    self.postScanStacking = False
                    self.timerStack.start(500)

                    self.threadpool.start(worker)
                else:
                    self.log_warning("Steppers are still moving!")
            else:
                self.log_info("Steppers need to be homed before scanning!")
        else:
            self.abortScan = True
            self.log_info("SCAN ABORTED!")
            if self.stackImages:
                self.postScanStacking = True

    def runScanAndReport_threaded(self, progress_callback):
        # number of images taken over the number of images to take
        self.images_taken = 0
        self.images_to_take = len(self.scanner.scan_pos[0]) * len(self.scanner.scan_pos[1]) * len(
            self.scanner.scan_pos[2])
        self.log_info("Running Scan!")
        print(self.scanner.scan_pos)
        for posX in self.scanner.scan_pos[0]:

            self.scanner.moveToPosition(0, posX)
            self.posX = posX
            progress_callback.emit(self.progress)
            for posY in self.scanner.scan_pos[1]:
                self.scanner.moveToPosition(1, posY + self.scanner.completedRotations * self.scanner.stepper_maxPos[1])
                self.posY = posY
                progress_callback.emit(self.progress)

                # create list of images associated with each stack for simultaneous processing
                stackName = []

                for posZ in self.scanner.scan_pos[2]:
                    save_time = time.time()
                    if self.abortScan:
                        return

                    self.scanner.moveToPosition(2, posZ)
                    # to follow the naming convention when focus stacking
                    img_name = str(self.output_location_folder.joinpath("RAW",
                                                                        "_x_" + self.scanner.correctName(posX)
                                                                        + "_y_" + self.scanner.correctName(posY)
                                                                        + "_step_" + self.scanner.correctName(
                                                                            posZ) + "_" + self.file_format))
                    stackName.append(img_name)

                    if self.camera_type == "FLIR":
                        captured_image = self.cam.capture_image(img_name, return_image=True)
                        self.FLIR_image_queue.append([captured_image, img_name])
                    if self.camera_type == "DSLR":
                        self.cam.capture_image(img_name)
                        # wait for the camera to capture the image before moving further
                        time.sleep(1)
                    self.images_taken += 1
                    self.getProgress()
                    self.posZ = posZ
                    progress_callback.emit(self.progress)

                    print('Time to write image to device:', time.time() - save_time, "seconds")

                if self.camera_type == "DSLR":
                    # TODO this is a temporary fix to ensure images are fully saved to the computer before stacking
                    time.sleep(2)

                self.stackList.append(stackName)

                self.scanner.completedStacks += 1
            self.scanner.completedRotations += 1
        # return to default position
        # reset settings
        self.log_info("Scan completed! Homing scanner...")
        if self.stackImages:
            self.log_info("Stacking remaining images in queue...")
            self.postScanStacking = True
        self.images_taken = 0
        self.deEnergise()
        self.homeX()
        self.homeZ()
        self.resetY()
        self.scanner.moveToPosition(1, self.ui.doubleSpinBox_yStep.value())
        self.resetY()
        self.scanner.completedRotations = 0

    """
    process captured images simultaneously
    """

    def checkActiveStackThreads(self):
        # prevent multiple simultaneous saving processes
        if not self.ActiveSavingProcess:
            if self.camera_type == "FLIR":
                if len(self.FLIR_image_queue) > 0:
                    self.ActiveSavingProcess = True
                    """
                    first check for any queued captured images and save them to the drive
                    create a local copy of the queue to not overwrite the external queue 
                    and not allow further entries while processing.
                    """
                    temp_FLIR_image_queue = self.FLIR_image_queue.copy()
                    for img in temp_FLIR_image_queue:
                        # write image to drive with pre-determined name
                        try:
                            img[0].Save(img[1])
                            print('Image saved as %s' % img[1])
                            # Release image
                        except Exception as error_save_FLIR_img:
                            print("Failed to save:", img[1])
                            print(error_save_FLIR_img)
                        img[0].Release()
                        # remove entries from queue once done
                        self.FLIR_image_queue.remove(img)

            if self.stackImages:
                if self.activeThreads < self.maxStackThreads and len(self.stackList) > 0:
                    worker = Worker(self.processStack)
                    self.activeThreads += 1
                    self.threadpool.start(worker)

            self.ActiveSavingProcess = False

        # additionally ensure that stacking is continued when capture finishes
        if self.postScanStacking:
            if self.activeThreads < self.maxStackThreads and len(self.stackList) > 0:
                worker = Worker(self.processStack)
                self.activeThreads += 1
                self.threadpool.start(worker)

    def processStack(self, progress_callback):
        stack = self.stackList[0]
        del self.stackList[0]
        # stack images
        print("\nSTACKING: \n\n", stack)

        stacked_output = stack_images(input_paths=stack, threshold=self.stackFocusThreshold, sharpen=self.stackSharpen,
                                      stacking_method=self.stackMethod)

        write_exif_to_img(img_path=stacked_output[0], custom_exif_dict=self.exif)

        if self.maskImages:
            mask_images(input_paths=stacked_output, min_rgb=self.maskThreshMin, max_rgb=self.maskThreshMax,
                        min_bl=self.maskArtifactSizeBlack, min_wh=self.maskArtifactSizeWhite, create_cutout=True)

            if self.createCutout:
                write_exif_to_img(img_path=str(stacked_output[0])[:-4] + '_cutout.jpg', custom_exif_dict=self.exif)

        self.activeThreads -= 1

    def closeEvent(self, event):
        # de-energise steppers, if connected
        if self.scanner_initialised:
            print("de energising stepper motors")
            # de energise steppers
            self.scanner.deEnergise()

        # report the program is to be closed so threads can be exited
        self.exit_program = True

        # stop the live view if currently in use
        if self.liveView:
            self.begin_live_view()  # sets live view false if already running

        if self.camera_type == "FLIR":
            # release camera
            self.cam.exit_cam()

        print("Application Closed!")


if __name__ == "__main__":
    # (for debugging only, to report errors to the console)
    cgitb.enable(format='text')

    app = QtWidgets.QApplication([])

    application = scAnt_mainWindow()

    application.show()

    sys.exit(app.exec())
