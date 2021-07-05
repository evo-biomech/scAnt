import cv2
import platform
import numpy as np

# as the PySpin class seems to be written differently for the windows library it needs to be imported as follows:
used_plattform = platform.system()

if used_plattform == "Linux":
    import PySpin
else:
    from PySpin import PySpin  # to run on windows


class customWEBCAM():

    def __init__(self):

        # check the number of connected working webcams
        check_port = 0
        self.cam_list = []
        while is_working:
            test_camera = cv2.VideoCapture(check_port)
            if not test_camera.isOpened():
                is_working = False
                print("Port %s is not working." %check_port)
            else:
                is_reading, img = test_camera.read()
                if is_reading:
                    self.cam_list.append(check_port)
                    test_camera.release()
                    print("Detected camera port", self.cam_list[-1])
            check_port +=1

        # by default, use the first camera in the retrieved list
        self.cam = self.cam_list[0]

        num_cameras = len(self.cam_list)

        print('Number of cameras detected: %d' % num_cameras)

        # Finish if there are no cameras
        if num_cameras == 0:

            print('Not enough cameras!')
            input('Done! Press Enter to exit...')
            return False

        print("\nExecute CustomWEBCAM.initialise_camera and pass the number of the listed camera, "
              "in case more than one has been detected!\n")

    def initialise_camera(self, select_cam=0):
        # overwrite the selected cam at initialisation if desired
        # initialise camera, apply settings and begin acquisition
        # Initialize camera
        self.cam = cv2.VideoCapture(self.cam_list[select_cam])

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

    def deinitialise_camera(self):
        self.cam.release()

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
        pass

    def live_view(self):
        """
        This function acquires and saves 10 images from a device; please see
        Acquisition example for more in-depth comments on the acquisition of images.

        :param cam: Camera to acquire images from.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        resized = None

        # Retrieve next received image and ensure image completion
        success, frame = self.cam.read()

        if not success:
            print('Image incomplete with image status %d...' % success)

        else:
            # Print image information
            width = self.cam.get(3)
            height = self.cam.get(4)

            scale_percent = 15  # percent of original size
            width = int(width * scale_percent / 100)
            height = int(height * scale_percent / 100)
            dim = (width, height)
            # resize image

            resized = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)

        return resized

    def capture_image(self, img_name="example.tif"):
        # Retrieve next received image and ensure image completion
        success, image_result = self.cam.read()

        if not success:
            print('Image incomplete with image status %d...' % success)

        else:
            # Print image information
            width = self.cam.get(3)
            height = self.cam.get(4)

            print('Captured Image with width = %d, height = %d' % (width, height))

            # Create a unique filename
            filename = img_name
            # Save RAW image
            cv2.imwrite(filename,image_result)

            print('Image saved as %s' % filename)


    def exit_cam(self):
        """ ###  End acquisition ### """
        self.cam.release()

        # Clear camera list before releasing system
        self.cam_list = []

    def showExposure(self, img):
        try:
            """ ### pass recorded images into this function to return overlaid exposure warnings / histogram"""
            # code altered from official openCV documentation
            # https://docs.opencv.org/master/d8/dbc/tutorial_histogram_calculation.html
            # split bgr values into separate planes of the retrieved image
            bgr_planes = cv2.split(img)
            # define number of bins for colour histogram
            histSize = 256
            histRange = (0, 256)  # the upper boundary is exclusive
            # to enforce equal bin sizes
            accumulate = False

            b_hist = cv2.calcHist(bgr_planes, [0], None, [histSize], histRange, accumulate=accumulate)
            g_hist = cv2.calcHist(bgr_planes, [1], None, [histSize], histRange, accumulate=accumulate)
            r_hist = cv2.calcHist(bgr_planes, [2], None, [histSize], histRange, accumulate=accumulate)

            # define size of the generated histogram
            hist_w = 256
            hist_h = 200
            bin_w = int(round(hist_w / histSize))

            histImage = np.zeros((hist_h, hist_w, 3), dtype=np.uint8)

            # first all values are normalised to fall in the range of the image
            # might disable this later, as I'd rather have a constant scale on the refreshed inputs

            cv2.normalize(b_hist, b_hist, alpha=0, beta=hist_h, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(g_hist, g_hist, alpha=0, beta=hist_h, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(r_hist, r_hist, alpha=0, beta=hist_h, norm_type=cv2.NORM_MINMAX)

            for i in range(1, histSize):
                cv2.line(histImage, (bin_w * (i - 1), hist_h - int(np.round(b_hist[i - 1]))),
                         (bin_w * i, hist_h - int(np.round(b_hist[i]))),
                         (255, 20, 20), thickness=2)
                cv2.line(histImage, (bin_w * (i - 1), hist_h - int(np.round(g_hist[i - 1]))),
                         (bin_w * i, hist_h - int(np.round(g_hist[i]))),
                         (20, 255, 20), thickness=2)
                cv2.line(histImage, (bin_w * (i - 1), hist_h - int(np.round(r_hist[i - 1]))),
                         (bin_w * i, hist_h - int(np.round(r_hist[i]))),
                         (20, 20, 255), thickness=2)

            # next highlight overexposed areas

            lower_limit = np.array([0, 0, 0])
            upper_limit = np.array([254, 254, 254])

            mask = cv2.bitwise_not(cv2.inRange(img, lower_limit, upper_limit))

            over_exposed_img = np.zeros((img.shape[0], img.shape[1], 3))
            over_exposed_img[:, :, 2] = mask

            # combine histogram and over exposure to single overlay

            px_offset_x = 20
            px_offset_y = 20

            offset_hist = np.zeros((img.shape[0], img.shape[1], 3))
            offset_hist[img.shape[0] - hist_h - px_offset_y:img.shape[0] - px_offset_y,
            img.shape[1] - hist_w - px_offset_x:img.shape[1] - px_offset_x] = histImage

            overlay = over_exposed_img + offset_hist
            overlay = overlay.astype(np.uint8)

            # ret, alpha_overlay = cv2.threshold(np.sum(overlay, axis=2), 1, 255, cv2.THRESH_BINARY)
            alpha_overlay = np.sum(overlay, axis=2) != 0
            alpha_img = 1.0 - alpha_overlay

            combined_img = np.zeros((img.shape[0], img.shape[1], 3))

            # now for each colour channel blend the original image and the overlay together
            for c in range(0, 3):
                combined_img[:, :, c] = overlay[:, :, c] + (alpha_img * img[:, :, c])

            return combined_img.astype(np.uint8)
        except:
            # this function may fail to execute when the program is being shut down
            pass


if __name__ == '__main__':
    display_for_num_images = 10

    # initialise camera
    WEBCAM = customWEBCAM()
    WEBCAM.initialise_camera(select_cam=0)

    # custom settings
    gain = 5

    for i in range(display_for_num_images):
        WEBCAM.set_gain(gain + i * 0.2)

        img = WEBCAM.live_view()
        overlay = WEBCAM.showExposure(img)

        cv2.imshow("Live view", overlay)

        cv2.waitKey(1)

    WEBCAM.capture_image(img_name="testy_mac_test_face.tif")

    # release camera
    WEBCAM.exit_cam()
