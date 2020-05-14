from time import sleep
from time import time
import datetime
import os
import numpy as np

"""
00281470,         Tic T500 Stepper Motor Controller -> Z-Axis (turntable)
00281480,         Tic T500 Stepper Motor Controller -> Y-Axis (camera arm)
00282144,         Tic T500 Stepper Motor Controller -> camera Focus
"""

import numpy as np
from PySpin import PySpin

NUM_IMAGES = 1  # number of images to save
img = 0


def configure_exposure(cam):
    """
     This function configures a custom exposure time. Automatic exposure is turned
     off in order to allow for the customization, and then the custom setting is
     applied.

     :param cam: Camera to configure exposure for.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """

    print('*** CONFIGURING EXPOSURE ***\n')

    try:
        result = True

        # Turn off automatic exposure mode
        #
        # *** NOTES ***
        # Automatic exposure prevents the manual configuration of exposure
        # times and needs to be turned off for this example. Enumerations
        # representing entry nodes have been added to QuickSpin. This allows
        # for the much easier setting of enumeration nodes to new values.
        #
        # The naming convention of QuickSpin enums is the name of the
        # enumeration node followed by an underscore and the symbolic of
        # the entry node. Selecting "Off" on the "ExposureAuto" node is
        # thus named "ExposureAuto_Off".
        #
        # *** LATER ***
        # Exposure time can be set automatically or manually as needed. This
        # example turns automatic exposure off to set it manually and back
        # on to return the camera to its default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to disable automatic exposure. Aborting...')
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        print('Automatic exposure disabled...')

        # Set exposure time manually; exposure time recorded in microseconds
        #
        # *** NOTES ***
        # Notice that the node is checked for availability and writability
        # prior to the setting of the node. In QuickSpin, availability and
        # writability are ensured by checking the access mode.
        #
        # Further, it is ensured that the desired exposure time does not exceed
        # the maximum. Exposure time is counted in microseconds - this can be
        # found out either by retrieving the unit with the GetUnit() method or
        # by checking SpinView.

        if cam.ExposureTime.GetAccessMode() != PySpin.RW:
            print('Unable to set exposure time. Aborting...')
            return False

        # Ensure desired exposure time does not exceed the maximum
        exposure_time_to_set = 100000
        # 90000  # with grey backdrop and full illumination
        # 200751  # with grey backdrop and half illumination
        exposure_time_to_set = min(cam.ExposureTime.GetMax(), exposure_time_to_set)
        cam.ExposureTime.SetValue(exposure_time_to_set)
        print('Shutter time set to %s us...\n' % exposure_time_to_set)

        """
        Gain, black level, gamma settings
        
        nodemap = cam.GetTLDeviceNodeMap()

        # Retrieve node (Enumeration node in this case)
        node_gainauto_mode = PySpin.CEnumerationPtr(nodemap.GetNode("GainAuto"))
        # EnumEntry node (always associated with an Enumeration node)
        node_gainauto_mode_off = node_gainauto_mode.GetEntryByName("Off")
        # Turn off Auto Gain
        node_gainauto_mode.SetIntValue(node_gainauto_mode_off.GetValue())

        gain_level = 0
        # Retrieve node (float)
        node_igain_float = PySpin.CFloatPtr(nodemap.GetNode("Gain"))
        # Set gain to gain_level dB
        node_igain_float.SetValue(gain_level)

        black_level = 10
        node_black_level_float = PySpin.CFloatPtr(nodemap.GetNode("BlackLevel"))
        node_black_level_float.SetValue(black_level)

        """

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def reset_exposure(cam):
    """
    This function returns the camera to a normal state by re-enabling automatic exposure.

    :param cam: Camera to reset exposure on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Turn automatic exposure back on
        #
        # *** NOTES ***
        # Automatic exposure is turned on in order to return the camera to its
        # default state.

        if cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print('Unable to enable automatic exposure (node retrieval). Non-fatal error...')
            return False

        cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)

        print('Automatic exposure enabled...')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def print_device_info(cam):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param cam: Camera to get device information from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        result = True
        nodemap = cam.GetTLDeviceNodeMap()

        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                """
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))
                """
        else:
            print('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex.message)
        return False

    return result


def get_and_export_images(cam, img_name):
    """
    This function acquires and saves 10 images from a device; please see
    Acquisition example for more in-depth comments on the acquisition of images.

    :param cam: Camera to acquire images from.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    print('*** IMAGE ACQUISITION ***')

    global img

    try:
        result = True

        # Set acquisition mode to continuous
        if cam.AcquisitionMode.GetAccessMode() != PySpin.RW:
            print('Unable to set acquisition mode to continuous. Aborting...')
            return False

        # always retrieve the newest captured image for the live view
        cam.TLStream.StreamBufferHandlingMode.SetValue(PySpin.StreamBufferHandlingMode_NewestOnly)
        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        # print('Acquisition mode set to continuous...')

        # Begin acquiring images
        cam.BeginAcquisition()

        print('Acquiring images...')

        # Get device serial number for filename
        device_serial_number = ''
        if cam.TLDevice.DeviceSerialNumber is not None and cam.TLDevice.DeviceSerialNumber.GetAccessMode() == PySpin.RO:
            device_serial_number = cam.TLDevice.DeviceSerialNumber.GetValue()

            # print('Device serial number retrieved as %s...' % device_serial_number)

        # Retrieve, convert, and save images
        for i in range(NUM_IMAGES):

            try:
                # Retrieve next received image and ensure image completion
                image_result = cam.GetNextImage()

                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                else:
                    # Print image information
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    print('Grabbed Image %d, width = %d, height = %d' % (i, width, height))

                    # Create a unique filename
                    filename = img_name  # 'COLOUR_ExposureQS' + str(img) + '_.jpg'
                    img += 1
                    # Save RAW image
                    image_result.Save(filename)

                    print('Image saved at %s' % filename)

                # Release image
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                result = False

        # End acquisition
        cam.EndAcquisition()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def capture_image(cam, img_name):
    """
     This function acts as the body of the example; please see NodeMapInfo_QuickSpin example for more
     in-depth comments on setting up cameras.

     :param cam: Camera to run example on.
     :type cam: CameraPtr
     :return: True if successful, False otherwise.
     :rtype: bool
    """
    try:
        # Initialize camera
        cam.Init()

        # Print device info
        result = print_device_info(cam)

        # Configure exposure
        if not configure_exposure(cam):
            return False

        # Acquire images
        result &= get_and_export_images(cam, img_name)

        # Reset exposure
        # result &= reset_exposure(cam)

        # Deinitialize camera
        cam.DeInit()

        return result

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False


def correctName(val):
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


def main():
    """
    Example entry point; please see Enumeration_QuickSpin example for more
    in-depth comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """
    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:
        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # - Initialization -------------------------------------------
    print("Initialising steppers...")
    os.system('ticcmd --deenergize -d 00281470')
    os.system('ticcmd --deenergize -d 00281480')
    os.system('ticcmd --deenergize -d 00282144')

    os.system('ticcmd --step-mode 8 -d 00281470')
    os.system('ticcmd --step-mode 8 -d 00281480')
    os.system('ticcmd --step-mode 8 -d 00282144')

    os.system('ticcmd --current 174 -d 00281470')
    os.system('ticcmd --current 174 -d 00281480')
    os.system('ticcmd --current 343 -d 00282144')

    os.system('ticcmd --max-accel 20000 -d 00281470')
    os.system('ticcmd --max-accel 10000 -d 00281480')
    os.system('ticcmd --max-accel 100000 -d 00282144')

    os.system('ticcmd --max-speed 1000000 -d 00281470')
    os.system('ticcmd --max-speed 800000 -d 00281480')
    os.system('ticcmd --max-speed 40000000 -d 00282144')

    sleep(2)

    print("Preparing and Homing!")
    # has to be send repeatedly as otherwise the stepper driver times out after 1 second
    os.system('ticcmd --resume --position ' + str(0) + ' --reset-command-timeout -d 00281470')
    os.system('ticcmd --resume --position ' + str(-1000) + ' --reset-command-timeout -d 00281480')
    os.system('ticcmd --resume --position ' + str(100000) + ' --reset-command-timeout -d 00282144')

    for i in range(20):
        os.system('ticcmd --resume --reset-command-timeout -d 00281470')
        os.system('ticcmd --resume --reset-command-timeout -d 00281480')
        os.system('ticcmd --resume --reset-command-timeout -d 00282144')
        sleep(0.5)

    os.system('ticcmd --halt-and-set-position 0 -d 00281470')
    os.system('ticcmd --halt-and-set-position 0 -d 00281480')
    os.system('ticcmd --halt-and-set-position 0 -d 00282144')

    # Move to listed positions
    positionsY = np.arange(0, 450, 50)
    positionsZ = np.arange(0, 1600, 80)
    focus_stack = np.arange(-25000, -8000, 500)

    """
    Stacking distances
    """
    # np.arange(-9000, 0, 500)          #  (medium animals 1.5 - 3 cm) -> two extension tubes
    # np.arange(-23000, -10000, 500)    #  (large animals 3 - 5 cm) -> one extension tube
    # np.arange(-25000, -8000, 500)     #  (very large animals 5 - 8 cm) -> one extension tube

    print("Homed! Actuators moving to default positions!")

    for i in range(20):
        os.system('ticcmd --resume --position ' + str(0) + ' --reset-command-timeout -d 00281470')
        os.system('ticcmd --resume --position ' + str(190) + ' --reset-command-timeout -d 00281480')
        os.system('ticcmd --resume --position ' + str(focus_stack[0]) + ' --reset-command-timeout -d 00282144')
        sleep(0.5)

    images_taken = 0
    images_to_take = len(positionsY) * len(positionsZ) * len(focus_stack)

    print("Turntable positions: ", positionsZ)
    print("Vertial positions: ", positionsY)
    print("Stacking positions: ", focus_stack)

    scanned_Ys = 0

    # Energize Motor
    os.system('ticcmd --energize -d 00281470')
    os.system('ticcmd --energize -d 00281480')
    os.system('ticcmd --energize -d 00282144')
    os.system('ticcmd --exit-safe-start -d 00281470')
    os.system('ticcmd --exit-safe-start -d 00281480')
    os.system('ticcmd --exit-safe-start -d 00282144')

    static = False

    begin = time()

    try:

        if not static:

            for p in positionsY:
                for i in range(4):
                    os.system('ticcmd --resume --position ' + str(p) + ' --pause-on-error -d 00281480')
                    sleep(0.5)

                for z in positionsZ:
                    for i in range(4):
                        os.system(
                            'ticcmd --resume --position ' + str(
                                z + (1600 * scanned_Ys)) + ' --pause-on-error -d 00281470')
                        sleep(0.5)

                    # Run example on each camera
                    for step in focus_stack:
                        for i in range(3):
                            os.system(
                                'ticcmd --resume --position ' + str(step) + ' --reset-command-timeout -d 00282144')
                            sleep(0.5)

                        # to follow the naming convention when focus stacking
                        step_name = correctName(step)
                        p_name = correctName(p)
                        z_name = correctName(z)

                        img_name = "y_" + p_name + "_z_" + z_name + "_step_" + step_name + "_.tif"

                        capture_image(cam_list[0], img_name)
                        sleep(0.5)
                        images_taken += 1
                        print("Images taken:", images_taken, "out of", images_to_take)

                    # reset focus ring
                    print("resetting focus!")
                    os.system(
                        'ticcmd --resume --position ' + str(focus_stack[0]) + ' --reset-command-timeout -d 00282144')
                    for i in range(20):
                        os.system('ticcmd --resume --reset-command-timeout -d 00282144')
                        sleep(0.5)
                    print("focus reset! Continue capture")

                print("Scanned Y position: ", scanned_Ys)
                scanned_Ys += 1
                sleep(0.3)

        else:
            # run for focus stacking only!
            for step in focus_stack:
                os.system('ticcmd --resume --position ' + str(step) + ' --pause-on-error -d 00282144')
                print()
                sleep(2)
                for i, cam in enumerate(cam_list):
                    result &= capture_image(cam, img)
                sleep(1)

    except():
        print("ABORT SCANNING!")

    # Return to home position
    print("Scanning complete")
    print("Elapsed time:", str(datetime.timedelta(seconds=time() - begin)))

    for i in range(20):
        os.system('ticcmd --resume --position ' + str(0) + ' --reset-command-timeout -d 00281470')
        os.system('ticcmd --resume --position ' + str(190) + ' --reset-command-timeout -d 00281480')
        os.system('ticcmd --resume --position ' + str(focus_stack[0]) + ' --reset-command-timeout -d 00282144')
        sleep(0.5)

    # Release reference to camera
    # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
    # cleaned up when going out of scope.
    # The usage of del is preferred to assigning the variable to None.
    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    os.system('ticcmd --deenergize -d 00281470')
    os.system('ticcmd --deenergize -d 00281480')
    os.system('ticcmd --deenergize -d 00282144')
    print("De-energizing steppers")

    print("Elapsed time:", str(datetime.timedelta(seconds=time() - begin)), "\n")


if __name__ == '__main__':
    main()
