import numpy as np
from PySpin import PySpin
import cv2


class customFLIR:

    def __init__(self):

        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()

        # Get current library version
        version = self.system.GetLibraryVersion()
        print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

        # Retrieve list of cameras from the system
        self.cam_list = self.system.GetCameras()

        # use first camera in retrieved list (so currently only supports one connected camera at a time)
        self.cam = self.cam_list[0]

        num_cameras = self.cam_list.GetSize()

        print('Number of cameras detected: %d' % num_cameras)

        # Finish if there are no cameras
        if num_cameras == 0:
            # Clear camera list before releasing system
            self.cam_list.Clear()

            # Release system instance
            self.system.ReleaseInstance()

            print('Not enough cameras!')
            input('Done! Press Enter to exit...')
            return False

        # initialise camera, apply settings and begin acquisition
        # Initialize camera
        self.cam.Init()

        # Set acquisition mode to continuous
        if self.cam.AcquisitionMode.GetAccessMode() != PySpin.RW:
            print('Unable to set acquisition mode to continuous. Aborting...')
            return False

        # always retrieve the newest captured image for the live view
        self.cam.TLStream.StreamBufferHandlingMode.SetValue(PySpin.StreamBufferHandlingMode_NewestOnly)
        self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        print('Acquisition mode set to continuous...')

        self.set_gain(gain=1.83)
        self.set_gamma(gamma=0.8)
        self.set_white_balance(red=1.58, blue=1.79)
        self.configure_exposure(exposure_time_to_set=90000)

        # Begin Acquisition of image stream
        self.cam.BeginAcquisition()

    def configure_exposure(self, exposure_time_to_set=100000):
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

            if self.cam.ExposureAuto.GetAccessMode() != PySpin.RW:
                print('Unable to disable automatic exposure. Aborting...')
                return False

            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
            print('Automatic exposure disabled...')

            if self.cam.ExposureTime.GetAccessMode() != PySpin.RW:
                print('Unable to set exposure time. Aborting...')
                return False

            # Ensure desired exposure time does not exceed the maximum
            # 90000  # with grey backdrop and full illumination
            # 200751  # with grey backdrop and half illumination
            exposure_time_to_set = min(self.cam.ExposureTime.GetMax(), exposure_time_to_set)
            self.cam.ExposureTime.SetValue(exposure_time_to_set)
            print('Shutter time set to %s us...\n' % exposure_time_to_set)


        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def set_gain(self, gain=1.83):
        self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        self.cam.Gain.SetValue(gain)

    def set_gamma(self, gamma=0.8):
        self.cam.Gamma.SetValue(gamma)

    def set_white_balance(self, red=1.58, blue=1.79):
        self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off)
        self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
        self.cam.BalanceRatio.SetValue(red)
        self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
        self.cam.BalanceRatio.SetValue(blue)

    def set_black_level(self, level):
        pass
        ### TODO
        # self.cam.BlackLevelRaw.SetValue(level)

    def reset_exposure(self):
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

            if self.cam.ExposureAuto.GetAccessMode() != PySpin.RW:
                print('Unable to enable automatic exposure (node retrieval). Non-fatal error...')
                return False

            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Continuous)

            print('Automatic exposure enabled...')

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def reset_gain(self):
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

            if self.cam.GainAuto.GetAccessMode() != PySpin.RW:
                print('Unable to enable automatic gain (node retrieval). Non-fatal error...')
                return False

            self.cam.GainAuto.SetValue(PySpin.GainAuto_Continuous)

            print('Automatic gain enabled...')

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def print_device_info(self):
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
            nodemap = self.cam.GetTLDeviceNodeMap()

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

    def live_view(self):
        """
        This function acquires and saves 10 images from a device; please see
        Acquisition example for more in-depth comments on the acquisition of images.

        :param cam: Camera to acquire images from.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """

        try:

            try:
                # Retrieve next received image and ensure image completion
                image_result = self.cam.GetNextImage()

                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                else:
                    # Print image information
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()

                    # convert from FLIR format to OpenCV np array
                    img_conv = image_result.Convert(PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)

                    scale_percent = 15  # percent of original size
                    width = int(width * scale_percent / 100)
                    height = int(height * scale_percent / 100)
                    dim = (width, height)
                    # resize image

                    resized = cv2.resize(img_conv.GetNDArray(), dim, interpolation=cv2.INTER_AREA)

                    # Release image
                    image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

        return resized

    def capture_image(self, img_name="example.tif"):
        try:
            try:
                # Retrieve next received image and ensure image completion
                image_result = self.cam.GetNextImage()

                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d...' % image_result.GetImageStatus())

                else:
                    # Print image information
                    width = image_result.GetWidth()
                    height = image_result.GetHeight()
                    print('Captured Image with width = %d, height = %d' % (width, height))

                    # Create a unique filename
                    filename = img_name
                    # Save RAW image
                    image_result.Save(filename)

                    print('Image saved as %s' % filename)

                # Release image
                image_result.Release()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)

    def exit_cam(self):
        """ ###  End acquisition ### """
        self.cam.EndAcquisition()
        # Deinitialize camera
        self.cam.DeInit()
        del self.cam

        # Clear camera list before releasing system
        self.cam_list.Clear()

        # Release system instance
        self.system.ReleaseInstance()


if __name__ == '__main__':
    display_for_num_images = 10

    # initialise camera
    FLIR = customFLIR()
    # custom settings
    FLIR.set_gain(4)

    for i in range(display_for_num_images):
        img = FLIR.live_view()
        cv2.imshow("Live view", img)
        cv2.waitKey(1)

    FLIR.capture_image(img_name="testy_mac_testface.tif")

    # release camera
    FLIR.exit_cam()
