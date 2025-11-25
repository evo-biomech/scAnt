import cv2
import platform
import numpy as np
import time

# NOTE: import of the PySpin/Spinnaker bindings can sometimes block or hang
# depending on the process working directory, environment, or loaded DLLs.
# Defer importing PySpin until we actually initialise the camera so that
# creating a `customFLIR()` instance is lightweight and won't freeze GUI
# applications that import this module (for example `scAnt.py`).


class customFLIR():

    def __init__(self):
        # Lightweight constructor: do not import or initialise Spinnaker here
        # because importing PySpin can block in some environments. Instead
        # defer loading until initialise_camera() is called.
        self.PySpin = None
        self._spinnaker_loaded = False
        self.system = None
        self.cam_list = None
        self.cam = None
        self.device_names = []
        print("customFLIR instance created (Spinnaker not yet loaded)")

    def _ensure_spinnaker(self):
        """Import the PySpin/Spinnaker module and set up the system instance.

        This is performed lazily to avoid import-time hangs in applications
        that import this module but don't immediately need camera access.
        """
        if self._spinnaker_loaded:
            return True

        used_platform = platform.system()
        try:
            if used_platform == "Linux":
                import PySpin as _PySpin
            else:
                # On Windows the PySpin package exposes the PySpin module
                # name in different ways; import it generically and keep a
                # reference on self so other methods can use it.
                from PySpin import PySpin as _PySpinClass
                # wrap to keep API consistent
                class _WinPySpinWrapper:
                    # provide attributes expected by code that uses `PySpin`
                    def __getattr__(self, name):
                        return getattr(_PySpinClass, name)
                _PySpin = _WinPySpinWrapper()

            self.PySpin = _PySpin
            # Retrieve singleton reference to system object
            self.system = self.PySpin.System.GetInstance()
            self._spinnaker_loaded = True
            return True
        except Exception as e:
            print(f"Error loading Spinnaker/PySpin: {e}")
            return False

    def initialise_camera(self, select_cam=0):
        # Lazy-load the PySpin module and initialise the system/camera list
        if not self._ensure_spinnaker():
            return False

        try:
            # Retrieve list of cameras from the system if not already retrieved
            if self.cam_list is None:
                self.cam_list = self.system.GetCameras()
                # get all serial numbers of connected and support FLIR cameras
                self.device_names = []
                for id, cam in enumerate(self.cam_list):
                    nodemap = cam.GetTLDeviceNodeMap()
                    node_device_serial_number = self.PySpin.CStringPtr(nodemap.GetNode("DeviceSerialNumber"))
                    node_device_model = self.PySpin.CStringPtr(nodemap.GetNode("DeviceModelName"))
                    if self.PySpin.IsAvailable(node_device_serial_number) and self.PySpin.IsReadable(node_device_serial_number):
                        self.device_names.append([node_device_model.GetValue(), node_device_serial_number.GetValue()])
                        print("Detected", self.device_names[id][0], "with Serial ID", self.device_names[id][1])

            # overwrite the selected cam at initialisation if desired
            self.cam = self.cam_list[select_cam]

            # initialise camera, apply settings and begin acquisition
            # Initialize camera
            self.cam.Init()

            # Set acquisition mode to continuous
            if self.cam.AcquisitionMode.GetAccessMode() != self.PySpin.RW:
                print('Unable to set acquisition mode to continuous. Aborting...')
                return False

            # always retrieve the newest captured image for the live view
            self.cam.TLStream.StreamBufferHandlingMode.SetValue(self.PySpin.StreamBufferHandlingMode_NewestOnly)
            self.cam.AcquisitionMode.SetValue(self.PySpin.AcquisitionMode_Continuous)
            print('Acquisition mode set to continuous...')

            self.set_gain(gain=1.83)
            self.set_gamma(gamma=0.8)
            self.set_white_balance(red=1.58, blue=1.79)
            self.configure_exposure(exposure_time_to_set=90000)

            # Begin Acquisition of image stream
            self.cam.BeginAcquisition()

            nodemap = self.cam.GetTLDeviceNodeMap()
            name = self.PySpin.CStringPtr(nodemap.GetNode("DeviceModelName"))
            if name.GetValue() == "Blackfly S BFS-U3-51S5C":
                self.cam.ExposureMode.SetValue(1)
                self.cam.ExposureMode.SetValue(0)
        except Exception as e:
            print("Error while initialising FLIR camera: " + str(e))
            return False


    def deinitialise_camera(self):
        # required to release camera for other applications in case another one is selected while running scAnt
        self.cam.EndAcquisition()
        # Deinitialize camera
        self.cam.DeInit()

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

            if self.cam.ExposureAuto.GetAccessMode() != self.PySpin.RW:
                print('Unable to disable automatic exposure. Aborting...')
                return False

            self.cam.ExposureAuto.SetValue(self.PySpin.ExposureAuto_Off)
            print('Automatic exposure disabled...')

            if self.cam.ExposureTime.GetAccessMode() != self.PySpin.RW:
                print('Unable to set exposure time. Aborting...')
                return False

            # Ensure desired exposure time does not exceed the maximum
            exposure_time_to_set = min(self.cam.ExposureTime.GetMax(), exposure_time_to_set)
            self.cam.ExposureTime.SetValue(exposure_time_to_set)
            print('Shutter time set to %s us...\n' % exposure_time_to_set)

        except Exception as ex:
            print('Error: %s' % ex)
            result = False

        return result

    def suggest_values(self, img):
        overall_min = 255
        overall_max = 0
        mask = np.zeros(img.shape[:2], dtype="uint8")
        cv2.rectangle(mask, (500, 500), (5000, 3000), 255, -1)
        mask = cv2.bitwise_not(mask)
        for i in range(3):    
            hist=cv2.calcHist([img], [i], mask,[256],[0,256])
            thresh_val = round(0.02*np.max(hist))
            hist[0] = 0
            min_val = np.min(np.where(hist > thresh_val)[0])
            if min_val < overall_min:
                overall_min = min_val
            max_val = np.max(np.where(hist > thresh_val)[0])
            if max_val > overall_max:
                overall_max = max_val
        min_bgr = round(overall_min - 0.05 * overall_min)
        max_bgr = round(overall_max + 0.05 * overall_max)   

        return (min_bgr, max_bgr)
    
    def showFocus(self, raw_img, img):
        fm = variance_of_laplacian(raw_img)
        new_img = cv2.putText(img, "{:.2f}".format(fm), (0, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 2 ,(150,150,150), 2, cv2.LINE_AA)
        return new_img 
    
    def set_gain(self, gain=1.83):
        self.cam.GainAuto.SetValue(self.PySpin.GainAuto_Off)
        self.cam.Gain.SetValue(gain)

    def set_gamma(self, gamma=0.8):
        self.cam.Gamma.SetValue(gamma)

    def set_white_balance(self, red=1.58, blue=1.79):
        self.cam.BalanceWhiteAuto.SetValue(self.PySpin.BalanceWhiteAuto_Off)
        self.cam.BalanceRatioSelector.SetValue(self.PySpin.BalanceRatioSelector_Red)
        self.cam.BalanceRatio.SetValue(red)
        self.cam.BalanceRatioSelector.SetValue(self.PySpin.BalanceRatioSelector_Blue)
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

            if self.cam.ExposureAuto.GetAccessMode() != self.PySpin.RW:
                print('Unable to enable automatic exposure (node retrieval). Non-fatal error...')
                return False

            self.cam.ExposureAuto.SetValue(self.PySpin.ExposureAuto_Continuous)

            print('Automatic exposure enabled...')

        except Exception as ex:
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

            if self.cam.GainAuto.GetAccessMode() != self.PySpin.RW:
                print('Unable to enable automatic gain (node retrieval). Non-fatal error...')
                return False

            self.cam.GainAuto.SetValue(self.PySpin.GainAuto_Continuous)

            print('Automatic gain enabled...')

        except Exception as ex:
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

            node_device_information = self.PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

            if self.PySpin.IsAvailable(node_device_information) and self.PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = self.PySpin.CValuePtr(feature)
                    """
                    print('%s: %s' % (node_feature.GetName(),
                                      node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))
                    """
            else:
                print('Device control information not available.')

        except Exception as ex:
            print('Error: %s' % ex)
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
        resized = None

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
                    img_conv = image_result.Convert(self.PySpin.PixelFormat_BGR8, self.PySpin.HQ_LINEAR)

                    scale_percent = 15  # percent of original size
                    width = int(width * scale_percent / 100)
                    height = int(height * scale_percent / 100)

                    # ensure dims are even to prevent diagonal cut in resized image
                    if (width % 2) != 0:
                        width = (width + 1)
                    if (height % 2) != 0:
                        height = (height + 1)
                    
                    dim = (width, height)
                    # resize image
                    resized = cv2.resize(img_conv.GetNDArray(), dim, interpolation=cv2.INTER_AREA)

                    # Release image
                    image_result.Release()

            except Exception as ex:
                print('Error: %s' % ex)

        except Exception as ex:
            print('Error: %s' % ex)

        return resized

    def capture_image(self, img_name="example.tif", return_image=False):
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

                    # NEW
                    if return_image:
                        return image_result
                    else:
                        # Save RAW image
                        image_result.Save(filename)

                        print('Image saved as %s' % filename)

                # Release image
                image_result.Release()


            except Exception as ex:
                print('Error: %s' % ex)

        except Exception as ex:
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

def variance_of_laplacian(image):
    # compute the Laplacian of the image and then return the focus
    # measure, which is simply the valirance of the Laplacian
    # using the following 3x3 convolutional kernel
    """
    [0   1   0]
    [1  -4   1]
    [0   1   0]

    as recommenden by Pech-Pacheco et al. in their 2000 ICPR paper,
    Diatom autofocusing in brightfield microscopy: a comparative study.
    """
    # apply median blur to image to suppress noise in RAW files
    blurred_image = cv2.medianBlur(image, 3)
    lap_image = cv2.Laplacian(blurred_image, cv2.CV_64F)
    lap_var = lap_image.var()

    return lap_var

if __name__ == '__main__':
    display_for_num_images = 10

    # initialise camera
    FLIR = customFLIR()
    FLIR.initialise_camera(select_cam=0)

    # custom settings
    gain = 5

    for i in range(display_for_num_images):
        FLIR.set_gain(gain + i * 0.2)

        img = FLIR.live_view()
        overlay = FLIR.showExposure(img)

        cv2.imshow("Live view", overlay)

        cv2.waitKey(1)

    FLIR.capture_image(img_name="testy_mac_test_face.tif")

    # release camera
    FLIR.exit_cam()
