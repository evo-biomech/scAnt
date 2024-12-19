"""
Camera control module using gphoto2 for DSLR cameras.

This module provides a class to control DSLR cameras using the gphoto2 library.
It supports camera initialization, configuration, and image capture.
"""

import gphoto2 as gp
import time
import logging
import os
import locale
import subprocess
import re
import cv2


class CustomGPhotoCamera:
    """
    A class to control DSLR cameras using gphoto2.

    This class provides methods to initialize, configure, and capture images
    from DSLR cameras supported by the gphoto2 library.

    Attributes:
        camera: A gphoto2.Camera object.
        context: A gphoto2.Context object.
        config: The camera's configuration.
        config_tree: A dictionary containing the camera's configuration tree.
    """

    def __init__(self):
        """
        Initialize the CustomGPhotoCamera instance.

        Sets up logging, locale, and initializes the camera connection.
        Raises any exceptions encountered during camera detection.
        """
        # Initialize logging and locale
        locale.setlocale(locale.LC_ALL, '')
        logging.basicConfig(format="%(levelname)s: %(name)s: %(message)s", level=logging.INFO)
        gp.check_result(gp.use_python_logging())
        
        # Initialize camera
        self.camera = None
        # is set when camera is detected
        self.camera_model = None
        self.context = gp.Context()
        
        # Store camera config
        self.config = None
        self.config_tree = {}

    def _detect_camera(self, name=None, addr=None):
        """
        Detect and initialize the camera connection.

        Attempts to connect to the selected camera and retrieves its summary.

        Raises:
            Exception: If no camera is detected or connection fails.
        """
        try:
            if name is None or addr is None:
                # by default, get first camera found
                name, addr = select_camera_cli()
            
            # Initialize camera with selected device
            self.camera = gp.Camera()
            
            # Get port info
            port_info_list = gp.PortInfoList()
            port_info_list.load()
            idx = port_info_list.lookup_path(addr)
            self.camera.set_port_info(port_info_list[idx])
            
            # Get camera abilities
            abilities_list = gp.CameraAbilitiesList()
            abilities_list.load()
            idx = abilities_list.lookup_model(name)
            self.camera.set_abilities(abilities_list[idx])
            
            # Initialize the camera
            self.camera.init(self.context)
            
            # Get camera summary
            text = self.camera.get_summary(self.context)
            logging.info(f"Camera summary:\n{str(text)}")

            self.camera_make = str(text).split("Manufacturer: ")[1].split("\n")[0].split(" ")[0].split(".")[0]
            logging.info(f"Camera make: {self.camera_make}")
            
        except Exception as e:
            logging.error(f"Error detecting camera: {str(e)}")
            list_connected_cameras()
            raise

    def _build_config_tree(self, config, tree=None):
        """
        Recursively build the camera configuration tree.

        Args:
            config: A gphoto2 widget containing camera configuration.
            tree: Optional dictionary to store the configuration tree.

        Returns:
            dict: A dictionary containing the camera's configuration tree.
        """
        if tree is None:
            tree = {}
        
        children = config.get_children()
        if children:
            for child in children:
                label = child.get_label()
                name = child.get_name()
                path = os.path.join(config.get_name(), name)
                
                subtree = {}
                self._build_config_tree(child, subtree)
                
                if subtree:
                    tree[name] = subtree
                else:
                    try:
                        value = child.get_value()
                        readonly = child.get_readonly()
                        type_ = child.get_type()
                        choices = []
                        
                        if type_ == gp.GP_WIDGET_RADIO or type_ == gp.GP_WIDGET_MENU:
                            choices = [c for c in child.get_choices()]
                        
                        tree[name] = {
                            'label': label,
                            'type': type_,
                            'current': value,
                            'readonly': readonly,
                            'choices': choices,
                            'path': path
                        }

                    except Exception as e:
                        logging.warning(f"Could not get value for {name}: {str(e)}")
        return tree
    
    
    def initialise_camera(self, print_settings=False):
        """Initialize camera and build configuration tree"""
        try:
            if not self.camera:
                raise ValueError("No camera detected")
            
            # Get and store camera config
            self.config = self.camera.get_config(self.context)
            self.config_tree = self._build_config_tree(self.config)

            self.camera_model = self.camera_make + " " + str(self.camera.get_summary(self.context)).split("Model: ")[1].split("\n")[0]
            logging.info(f"Camera model: {self.camera_model}")
            
            logging.info("Successfully initialized camera!")
            
            # Print available settings
            if print_settings:
                self._print_settings()
            
        except Exception as e:
            logging.error(f"Error initializing camera: {str(e)}")
            raise

    def _print_settings(self):
        """Print available camera settings"""
        logging.info("\nAvailable camera settings:")
        def print_widget(widget, prefix=""):
            children = widget.get_children()
            if children:
                for child in children:
                    print_widget(child, prefix + "  ")
            else:
                try:
                    readonly = widget.get_readonly()
                    readonly_str = " (readonly)" if readonly else ""
                    value = widget.get_value()
                    choices = []
                    if widget.get_type() in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                        choices = [c for c in widget.get_choices()]
                    choices_str = f", Choices: {choices}" if choices else ""
                    logging.info(f"{prefix}{widget.get_name()}: {value}{choices_str}{readonly_str}")
                except Exception as e:
                    logging.warning(f"Could not get value for {widget.get_name()}: {str(e)}")
        
        print_widget(self.config)

    def get_setting(self, setting_name):
        """Get current value of a camera setting"""
        try:
            OK, widget = gp.gp_widget_get_child_by_name(self.config, setting_name)
            if OK >= gp.GP_OK:
                return widget.get_value()
            else:
                raise ValueError(f"Setting {setting_name} not found")
        except Exception as e:
            logging.warning(f"Could not get value for {setting_name}: {str(e)}")
            return None

    def set_setting(self, setting_name, value):
        """Set a camera setting value directly using the setting name"""
        try:
            # Get the widget directly by name
            OK, widget = gp.gp_widget_get_child_by_name(self.config, setting_name)
            if OK >= gp.GP_OK:
                # Check if setting is read-only
                if widget.get_readonly():
                    logging.warning(f"Setting {setting_name} is readonly - skipping")
                    return
                
                # Get available choices if it's a RADIO or MENU widget
                if widget.get_type() in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                    choices = [c for c in widget.get_choices()]
                    if choices and value not in choices:
                        logging.warning(f"Invalid value for {setting_name}. Must be one of: {choices} - skipping")
                        return
                
                # Set the value
                widget.set_value(value)
                self.camera.set_config(self.config)
                
                logging.info(f"Successfully set {setting_name} to {value}")
                
            else:
                logging.warning(f"Setting {setting_name} not found - skipping")
                
        except Exception as e:
            logging.warning(f"Error setting {setting_name} to {value}: {str(e)} - skipping")

    def capture_image(self, img_name="example.jpg", save_to_camera_only=False, capture_delay=1):
        """Capture an image and save it"""
        try:
            logging.info("Capturing image...")
            
            # Wait for camera to be ready
            while True:
                try:
                    event_type, event_data = self.camera.wait_for_event(100)
                    if event_type == gp.GP_EVENT_TIMEOUT:
                        break
                except Exception as e:
                    logging.warning(f"Wait for event error: {str(e)}")
                    break
            
            # Capture the image
            file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE)
            logging.info(f"Camera file path: {file_path.folder}/{file_path.name}")
            
            if not save_to_camera_only:
                try:
                    # Get and save the file
                    camera_file = self.camera.file_get(
                        file_path.folder, 
                        file_path.name, 
                        gp.GP_FILE_TYPE_NORMAL)
                    
                    # automatically add the correctfile extension to the filename
                    camera_file.save(img_name.split(".")[0] + "." + file_path.name.split(".")[1])
                    logging.info(f"Image saved as {img_name}")
                    
                    # Clean up camera memory
                    self.camera.file_delete(
                        file_path.folder,
                        file_path.name)
                    
                    # Release the camera file object
                    del camera_file
                    
                except Exception as e:
                    logging.error(f"Error saving file: {str(e)}")
                    raise
            else:
                logging.info("Image captured and saved to camera only")
            
            # Refresh config
            try:
                self.config = self.camera.get_config()
                
            except Exception as e:
                logging.warning(f"Could not refresh config: {str(e)}")
            
            # Wait after capture to ensure camera stability
            time.sleep(capture_delay)
            
        except Exception as e:
            logging.error(f"Error capturing image: {str(e)}")
            raise

    def exit_camera(self):
        """Clean up camera resources"""
        if self.camera:
            self.camera.exit(self.context)
            logging.info("Camera released")

    def get_setting_choices(self, setting_name):
        """Get available choices or range for a camera setting"""
        try:
            OK, widget = gp.gp_widget_get_child_by_name(self.config, setting_name)
            if OK >= gp.GP_OK:
                widget_type = widget.get_type()
                if widget_type in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                    choices = [c for c in widget.get_choices()]
                    return choices
                elif widget_type == gp.GP_WIDGET_RANGE:
                    min_value, max_value, increment = widget.get_range()
                    # Convert to integers if increment is a whole number
                    if increment.is_integer():
                        return (int(min_value), int(max_value), int(increment))
                    return (min_value, max_value, increment)
                else:
                    logging.warning(f"Setting {setting_name} does not have choices or range")
                    return None
            else:
                logging.warning(f"Setting {setting_name} not found")
                return None
        except Exception as e:
            logging.warning(f"Error getting choices for {setting_name}: {str(e)}")
            return None

    def set_compression(self, format_type='Fine'):
        """Set the image format. Common names: 'imageformat', 'imagequality'"""
        format_props = ["imageformat", "imagequality"]
        
        # Try each possible property name
        for prop in format_props:
            try:
                choices = self.get_setting_choices(prop)
                if choices:
                    logging.info(f"Available {prop} options: {choices}")
                    # Find matching format
                    matching_format = None
                    for choice in choices:
                        if format_type.upper() in choice.upper():
                            matching_format = choice
                            break
                    
                    if matching_format:
                        self.set_setting(prop, matching_format)
                        return True
                    else:
                        logging.warning(f"No matching format found for {format_type} in {choices}")
            except Exception as e:
                logging.warning(f"Error setting {prop}: {str(e)}")
                continue
        
        return False
 
    def print_all_settings(self):
        """Print all available settings and their choices"""
        logging.info("\nAll available camera settings and their options:")
        
        def print_widget_choices(widget, prefix=""):
            children = widget.get_children()
            if children:
                for child in children:
                    print_widget_choices(child, prefix + "  ")
            else:
                try:
                    name = child.get_name()
                    label = child.get_label()
                    readonly = child.get_readonly()
                    readonly_str = " (readonly)" if readonly else ""
                    value = child.get_value()
                    
                    # Get choices if available
                    choices = []
                    if child.get_type() in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                        choices = [c for c in child.get_choices()]
                    
                    choices_str = f"\n    Choices: {choices}" if choices else ""
                    logging.info(f"{prefix}{name} ({label}): {value}{readonly_str}{choices_str}")
                    
                except Exception as e:
                    logging.warning(f"Could not get info for {widget.get_name()}: {str(e)}")
        
        print_widget_choices(self.config_tree)

    def print_image_format_options(self):
        """Print all available image format and quality options"""
        logging.info("\nAvailable Image Format Options:")
        
        # Common property names for image format/quality settings
        format_props = [
            "imageformat", 
            "imagequality",
            "compression",
            "compressionsetting",
            "captureformat"
        ]
        
        for prop in format_props:
            try:
                OK, widget = gp.gp_widget_get_child_by_name(self.config, prop)
                if OK >= gp.GP_OK:
                    choices = widget.get_choices()
                    current = widget.get_value()
                    print("\n")       
                    logging.info(f"{prop}:")
                    logging.info(f"  Current: {current}")
                    logging.info(f"  Available options: {[c for c in choices]}")
                    return choices, current
            except Exception as e:
                continue

    def set_whitebalance(self, mode='Choose Color Temperature'):
        """
        Set the white balance mode.
        Common property names: 'whitebalance', 'whitebalancemode'
        
        Args:
            mode (str): White balance mode to set (e.g., 'Choose Color Temperature', 'Auto', 'Daylight', etc.)
        
        Returns:
            bool: True if successful, False otherwise
        """
        wb_props = ["whitebalance", "whitebalancemode"]
        
        for prop in wb_props:
            try:
                choices = self.get_setting_choices(prop)
                if choices:
                    logging.info(f"Available {prop} options: {choices}")
                    # Find exact match first
                    if mode in choices:
                        self.set_setting(prop, mode)
                        logging.info(f"White balance mode set to: {mode}")
                        return True
                        
                    # If no exact match, try case-insensitive partial match
                    matching_mode = None
                    for choice in choices:
                        if mode.upper() in choice.upper():
                            matching_mode = choice
                            break
                    
                    if matching_mode:
                        self.set_setting(prop, matching_mode)
                        logging.info(f"White balance mode set to: {matching_mode}")
                        return True
                    else:
                        logging.warning(f"No matching white balance mode found for {mode} in {choices}")
                else:
                    logging.warning(f"No choices available for {prop}")
            except Exception as e:
                logging.warning(f"Error setting {prop}: {str(e)}")
                continue
        
        return False

    def set_white_balance_kelvin(self, kelvin):
        """
        Set the white balance color temperature in Kelvin.
        Common property names: 'colortemperature', 'whitebalancetemperature'
        
        Args:
            kelvin (int): Color temperature in Kelvin (typically 2500-10000)
        
        Returns:
            bool: True if successful, False otherwise
        """

        # Common property names for Kelvin setting
        kelvin_props = ["colortemperature", "whitebalancetemperature"]
        
        if camera.camera_make == "Sony":
            self.set_white_balance_mode("Choose Color Temperature")
            kelvin_val = int(kelvin)
        elif camera.camera_make == "Canon":
            self.set_white_balance_mode("Color Temperature")
            kelvin_val = str(kelvin)
        elif camera.camera_make == "Nikon":
            self.set_white_balance_mode("Color Temperature")
            kelvin_val = int(kelvin)
            # Now this is slightly more tricky, as the Nikon camera uses a different property name
            # The Nikon camera uses "White Balance Colour Temperature" but this cannot be accessed directly
            # Instead by the setting method, so we need to find the entry and use its hex code path to set it
            # It's very dumb but it works.
            text = self.camera.get_summary(self.context)
            for line in str(text).split("\n"):
                if "White Balance Colour Temperature" in line:
                    Nikon_hex_code = line.split("(0x")[1].split(")")[0]
                    break

            kelvin_props =[Nikon_hex_code]
        else:
            kelvin_val = int(kelvin)
        
        for prop in kelvin_props:
            try:
                # Try to set the Kelvin value as integer
                self.set_setting(prop, kelvin_val)
                logging.info(f"White balance temperature set to {kelvin_val}K")
                break
            except Exception as e:
                logging.warning(f"Error setting {prop}: {str(e)}")
                continue
            
        return False

    def print_white_balance_options(self):
        """Print all available white balance options and current settings"""
        logging.info("\nWhite Balance Settings:")
        
        # Common property names for white balance settings
        wb_props = {
            "Mode": ["whitebalance", "whitebalancemode"],
            "Temperature": ["colortemperature", "whitebalancetemperature"]
        }
        
        for category, props in wb_props.items():
            logging.info(f"\n{category}:")
            for prop in props:
                try:
                    OK, widget = gp.gp_widget_get_child_by_name(self.config, prop)
                    if OK >= gp.GP_OK:
                        current = widget.get_value()
                        logging.info(f"  {prop}:")
                        logging.info(f"    Current: {current}")
                        
                        if widget.get_type() in (gp.GP_WIDGET_RADIO, gp.GP_WIDGET_MENU):
                            choices = [c for c in widget.get_choices()]
                            logging.info(f"    Available options: {choices}")
                except Exception as e:
                    continue
    
    def set_iso(self, iso):
        """Set the ISO value"""
        self.set_setting("iso", iso)
    
    def set_shutterspeed(self, shutterspeed):
        """Set the shutterspeed value"""

        if self.camera_make == "Nikon":
            self.set_setting("shutterspeed2", shutterspeed)
        else:
            self.set_setting("shutterspeed", shutterspeed)
    
    def set_aperture(self, aperture):
        """Set the aperture value"""

        if self.camera_make in ["Nikon", "Sony"]:
            self.set_setting("f-number", "f/" + str(aperture))
        else:
            self.set_setting("aperture", aperture)

    def get_format(self):
        """Get current image format/quality and available options"""
        # Common property names for image format/quality settings
        format_props = [
            "imageformat", 
            "imagequality",
            "compression",
            "compressionsetting",
            "captureformat"
        ]
        
        for prop in format_props:
            try:
                OK, widget = gp.gp_widget_get_child_by_name(self.config, prop)
                if OK >= gp.GP_OK:
                    choices = [c for c in widget.get_choices()]
                    current = widget.get_value()
                    return current, choices
            except Exception as e:
                continue
        
        logging.warning("No image format/quality settings found")
        return None, None

    def get_iso(self):
        """Get current ISO and available options"""
        iso_choices = self.get_setting_choices("iso")
        current_iso = self.get_setting("iso")
        if not iso_choices:
            iso_choices = self.get_setting_choices("iso speed")
            current_iso = self.get_setting("iso speed")
        return current_iso, iso_choices

    def get_shutterspeed(self):
        """Get current shutter speed and available options"""
        if self.camera_make == "Nikon":
            shutter_choices = self.get_setting_choices("shutterspeed2")
            current_shutter = self.get_setting("shutterspeed2")
        else:
            shutter_choices = self.get_setting_choices("shutterspeed")
            current_shutter = self.get_setting("shutterspeed")
        return current_shutter, shutter_choices

    def get_aperture(self):
        """Get current aperture and available options"""
        if self.camera_make in ["Nikon", "Sony"]:
            aperture_choices = self.get_setting_choices("f-number")
            current_aperture = self.get_setting("f-number")
        else:
            aperture_choices = self.get_setting_choices("aperture")
            current_aperture = self.get_setting("aperture")
        return current_aperture, aperture_choices

    def get_whitebalance(self):
        """Get current white balance mode and available options"""
        wb_choices = self.get_setting_choices("whitebalance")
        current_wb = self.get_setting("whitebalance")
        if not wb_choices:
            wb_choices = self.get_setting_choices("whitebalancemode")
            current_wb = self.get_setting("whitebalancemode")
        return current_wb, wb_choices

    def get_colortemperature(self):
        """Get current color temperature and available options"""
        kelvin_choices = self.get_setting_choices("colortemperature")
        current_kelvin = self.get_setting("colortemperature")
        if not kelvin_choices:
            kelvin_choices = self.get_setting_choices("whitebalancetemperature")
            current_kelvin = self.get_setting("whitebalancetemperature")
        return current_kelvin, kelvin_choices

def list_connected_cameras():
    """
    List all connected camera devices, if they are recognised as drives and provide unmounting instructions.
    Specifically looks for major camera brands in USB devices.
    """
    try:
        # Run lsusb command and capture output
        result = subprocess.run(['lsusb'], capture_output=True, text=True)        
        # Camera brand patterns to look for
        camera_brands = r"(Nikon|Canon|Fujifilm|Sony|Olympus)"
        
        # Filter and display relevant devices
        cameras_found = False
        for line in result.stdout.split("\n"):
            if re.search(camera_brands, line, re.IGNORECASE):
                cameras_found = True
                logging.info(f"Found camera device: {line.strip()}")
        
        if cameras_found:
            logging.info("\nIf your camera is mounted as a drive, please unmount it:")
            logging.info("1. Linux: Right click on camera icon and and select 'Unmount' or use 'umount /path/to/camera'")
            logging.info("2. macOS: Eject the camera from Finder")
        else:
            logging.info("No supported cameras found in USB devices.")
            
    except Exception as e:
        logging.error(f"Error listing USB devices: {str(e)}")


def display_image(image_path, window_name="Captured Image", wait_time=0):
    """
    Display an image using OpenCV.
    
    Args:
        image_path (str): Path to the image file
        window_name (str): Name of the window to display the image
        wait_time (int): Time in milliseconds to display the image. 
                        0 means wait indefinitely until a key is pressed or window is closed
    """
    try:
        # Read the image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Create window with resizable property
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        
        # Resize if image is too large
        height, width = img.shape[:2]
        max_height = 800  # Maximum height for display
        if height > max_height:
            scale = max_height / height
            new_width = int(width * scale)
            img = cv2.resize(img, (new_width, max_height))
            
        # Display the image
        cv2.imshow(window_name, img)
        
        # Wait for key press or window close
        while cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) > 0:
            key = cv2.waitKey(100)  # Check every 100ms
            if key == 27:  # ESC key
                break
                
        # Ensure window is closed
        cv2.destroyWindow(window_name)
            
    except Exception as e:
        logging.error(f"Error displaying image: {str(e)}")

def get_camera_choices():
    """
    Return a list of camera choices
    """
    camera_list = list(gp.Camera.autodetect())
    # Remove any cameras that are detected as mass storage devices
    camera_list = [cam for cam in camera_list if "Mass Storage" not in cam[0]]
    if not camera_list:
        logging.warning("No compatible cameras found after filtering mass storage devices")

    return camera_list

def select_camera_cli():
    """
    Allow user to select a camera when multiple cameras are detected.
    
    Returns:
        tuple: (camera_name, port_address) of selected camera
    Raises:
        Exception: If no camera is detected or selection fails
    """
    try:
        # Make a list of all available cameras
        camera_list = list(gp.Camera.autodetect())
        if not camera_list:
            raise Exception('No camera detected')
            
        # If only one camera, return it
        if len(camera_list) == 1:
            return camera_list[0]
            
        # Sort cameras by name
        camera_list.sort(key=lambda x: x[0])
        
        # Print available cameras
        logging.info("\nAvailable cameras:")
        for index, (name, addr) in enumerate(camera_list):
            logging.info(f'{index}:  {addr}  {name}')

        # Ask user to choose one
        while True:
            try:
                choice = input('Please input number of chosen camera: ')
                choice = int(choice)
                if 0 <= choice < len(camera_list):
                    return camera_list[choice]
                else:
                    logging.warning('Number out of range')
            except ValueError:
                logging.warning('Please enter a valid number!')
                
    except Exception as e:
        logging.error(f"Error selecting camera: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        # Initialize camera
        camera = CustomGPhotoCamera()
        camera_list = get_camera_choices()
        camera._detect_camera()
        camera.initialise_camera()

        # Get available choices for major camera settings
        logging.info("Available choices for major settings:\n")
        
        # Get and display all major settings
        settings = [
            ("Image format/quality", camera.get_format()),
            ("ISO", camera.get_iso()),
            ("Shutter speed", camera.get_shutterspeed()),
            ("Aperture", camera.get_aperture()),
            ("White balance", camera.get_whitebalance()),
            ("Color temperature", camera.get_colortemperature())
        ]

        for setting_name, (current, options) in settings:
            logging.info(f"{setting_name}:")
            logging.info(f"  Current: {current}")
            logging.info(f"  Available options: {options}\n")


        camera.set_white_balance_kelvin(4000)
        camera.set_iso("400")
        camera.set_shutterspeed("1/30")
        camera.set_aperture("5.6")
        
        # Capture test images with delay between captures
        last_image = None
        iso_range = ["400", "800", "1600", "3200", "6400"]
        for i in range(len(iso_range)):
            filename = f"test_image_{camera.camera_make}_iso_{iso_range[i]}.jpg"
            camera.set_iso(iso_range[i])
            camera.capture_image(filename, 
                                 save_to_camera_only=False,
                                 capture_delay=0.05)
            last_image = filename

        # Clean up
        camera.exit_camera()
        
        # Show the last captured image using OpenCV
        if last_image and os.path.exists(last_image):
            logging.info(f'Displaying image: {last_image}')
            display_image(last_image)
        
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")

