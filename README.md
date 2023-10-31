# scAnt - Open Source 3D Scanner

[**scAnt**](https://peerj.com/articles/11155/) is an open-source, low-cost macro 3D scanner, designed to automate the creation of digital 3D models of insects of various sizes in full colour. **scAnt** provides example configurations for the scanning process, as well as scripts for stacking and masking of images to prepare them for the photogrammetry software of your choice. Some examples of models generated with **scAnt** can be found on http://bit.ly/ScAnt-3D as well as on our [Sketchfab Collection](https://sketchfab.com/EvoBiomech/collections/scant-collection)!

![](images/model_collection_showcase_04_updated.jpg)

The [**scAnt**](https://peerj.com/articles/11155/) paper can be found [here](https://peerj.com/articles/11155/):

Plum F, Labonte D. 2021. scAnt—an open-source platform for the creation of 3D models of arthropods (and other small objects) PeerJ 9:e11155 https://doi.org/10.7717/peerj.11155

All structural components of the scanner can be manufactured using 3D-printing and laser cutting; the required files are available for download in .ipt, .iam, .stl, and .svg format on our [thingiverse](https://www.thingiverse.com/thing:4694713) page.

![](images/scanner_3D_comp.png)

## Updates
- **scAnt 1.2** Significantly improved image capture speed for FLIR cameras. As this increases the hardware demand during scanning, it may be advisable to run stacking and masking separately (see [provided python cli scripts](https://github.com/evo-biomech/scAnt/tree/master/scripts)), instead of during scanning. We also updated the respective stacking, masking, and meta data scripts to accomodate a wider range of applications.
- **scAnt 1.1** now supports the use of **DSLR** cameras on **Windows 10**, in combination with [DigiCamControl](http://digicamcontrol.com/). Please refer to the [official documentation](http://digicamcontrol.com/cameras) to check whether your camera model is currently supported. **Ubuntu** support will be added soon. An updated version of the scanner construction files will be made available on our [Thingiverse](https://www.thingiverse.com/thing:4694713) page.  


## Installation
**scAnt** is supported by 64 bit versions of **Windows 10** and **Ubuntu 18.04** (newer releases of Ubuntu will likely work but have not been tested). The pipeline and GUI have been designed specifically for use with [FLIR Blackfly](https://www.flir.co.uk/products/blackfly-s-usb3/) cameras, and [Pololu USB Stepper drivers](https://www.pololu.com/category/212/tic-stepper-motor-controllers). We have now added support for **DSLR** cameras for **Windows** operating systems as well. Please refer to our [Thingiverse](https://www.thingiverse.com/thing:4694713) page for a full list of components.

The easiest way to get your scanner up and running is through installation of our pre-configured anaconda environment:

**for Ubuntu 18.04**

```bash
cd conda_environment
conda env create -f scAnt_UBUNTU.yml
```

**for Windows 10**

```bash
cd conda_environment
conda env create -f scAnt_WINDOWS.yml
```

After the environment has been created successfully, re-start the terminal, and run the following line to activate the environment, and to continue the installation.

 ```bash
conda activate scAnt
```

If you do not wish to install the pre-configured environment, here are the dependencies:

  - python >= 3.6
  - pip
  - numpy
  - matplotlib
  - opencv >= 4.1.0
  - pyqt 5
  - imutils
  - pillow
  - scikit-image


Additional drivers and libraries for the camera and stepper drivers need to be installed, as described for both Ubuntu and Windows below.
***

### Ubuntu 18.04

**FLIR setup**

***

**NOTE** The latest version (3.0 and above) of **Spinnaker** & **PySpin** causes the **scAnt** application to freeze for some capture commands. 
For now, we reccomend using a legacy version (1.29 - 2.7) of **Spinnaker** & **PySpin** to avoid this issue! These versions can be found under **FLIR Support / Spinnaker / archive**. In there, you will find both **Ubuntu** as well as **Windows** files, so be sure to double check you are using the version appropriate to your system and python installation.

***

Download the drivers and python bindings for **Spinnaker & Pyspin** from the official FLIR page: [FLIR - Spinnaker & PySpin](https://www.flir.co.uk/products/spinnaker-sdk/?vertical=machine+vision&segment=iis)

Spinnaker has recently moved their API and criver files into a new repository and you will need to create an account in order to access them.
Once you have created an account head to the bottom of the download page to the section **Previous Versions** and download the **2.7.0.128** version for your respective operating system.
Unpack the folder and you should find both the Spinakker API installation, as well as the required python package inside.

Unpack all files in a folder of your choice. Then proceed with the following steps:

1. Install all required dependencies

```bash
sudo apt-get install libavcodec57 libavformat57 libswscale4 libswresample2 libavutil55 libusb-1.0-0 libgtkmm-2.4-dev
```

2. Install spinnaker from its extracted folder. During installation, ensure to add your user to the user-group and accept increasing allocated USB-FS memory size to 1000 MB in order to increase the video stream buffer size.

```bash
sudo sh install_spinnaker.sh
```

3. **Reboot** your computer

In some cases the installer will not be able to update the allocated memory automatically. Check that the memory is set to at least **1000** MB by running:

```bash
cat /sys/module/usbcore/parameters/usbfs_memory_mb
```

In case the **memory allocation** has **not been updated**, you can either increase it temporarily by running

```bash
sudo sh -c 'echo 1000 > /sys/module/usbcore/parameters/usbfs_memory_mb'
```

or permanently, by following the instructions outlined in the **README** file of the downloaded **Spinnaker installation** folder.

4. Launch spinview and connect your FLIR camera to verify your installation (if the application is already launched when plugging in your camera, refresh the list)

5. Next, install the downloaded **.whl** file for your python environment. Ensure you activate your python environment before running the **pip install** command below.

```bash
pip install spinnaker_python-2.7.x.x-cp37-cp37m-linux_x86_64.whl
```

6. To verify everything has been installed correctly, run **Live_view_FLIR.py** from the GUI folder. 

```bash
cd scant/GUI
python Live_view_FLIR.py
```

If a live preview of the camera appears for a few seconds and an example image is saved (within the GUI folder), all camera drivers and libraries have been installed correctly.

**Stepper driver setup**

1. The Pololu stepper drivers can be controlled and set up via a console. Download the drivers specific to your system from [pololu.com](https://www.pololu.com/docs/0J71/3.2), which also provides additional information regarding installation and a list of supported commands. All drivers are open-source, and the respective code can be found on [Pololu's Git](https://github.com/pololu/pololu-tic-software).

2. Unpack the downloaded .tar.xy file and install the driver:

```bash
sudo pololu-tic-*/install.sh
```

3. Next, **reboot** your computer to update your user privileges automatically, otherwise you will have to use **sudo** to access your USB stepper drivers.

4. If one or all of the stepper controllers were previously plugged into your computer re-plug them, so they are recognised correctly by your computer. Now, open the terminal and run:

```bash
ticcmd --list
```

This should output a list of all connected USB stepper drivers.

6. To test which ID corresponds to which stepper, launch the **Tic Control Center** application and move the sliders. You can use this application to test each motor and set up turning speeds and assign pins for the connected endstops. 

Double check your end-stop cables are connected to the correct pins on the pololu-tic board:

- **GND**: Black
- **TX**: Green
- **RX**: Red

Then the setup should be:

**for the Z-axis (camera slider)**

![](images/stepper_set_up.png)

The TX of the limit switch of the **Z-axis** (camera slider) needs to be set to *"limit switch forward"* and to *"limit switch reverse"* for the **X-axis** (gimbal).

From **/scripts**, open the **Scanner_Controller.py** script in an editor of choice and add the **IDs** of each the stepper to the corresponding axes:

```python
self.stepperX_ID = "XXXXXXXX"
self.stepperY_ID = "YYYYYYYY"
self.stepperZ_ID = "ZZZZZZZZ"
```


**Image Processing**

A number of open source tools are used for processing the RAW images captured by the scanner. For a detailed explanation of each, refer to the official [hugin](http://hugin.sourceforge.net/docs/) and [exiftool](https://exiftool.org/) documentation. The following lines will install _all_ the good stuff:

```bash
sudo add-apt-repository ppa:hugin/hugin-builds
sudo apt-get update
sudo apt-get install hugin enblend
sudo apt install hugin-tools
sudo apt install enfuse
sudo apt install libimage-exiftool-perl
```

***

### Windows 10

#### FLIR setup

(**Optional**: you only need to install the software required for your respective camera)

(Instructions for using **DSLR** cameras in the section below. You can skip the **FLIR** installation section, if you are not planning on using **FLIR** cameras.) 

***

**NOTE** The latest version (3.0 and above) of **Spinnaker** & **PySpin** causes the **scAnt** application to freeze for some capture commands. 
For now, we reccomend using a legacy version (1.29 - 2.7) of **Spinnaker** & **PySpin** to avoid this issue! These versions can be found under **FLIR Support / Spinnaker / archive**. In there, you will find both **Ubuntu** as well as **Windows** files, so be sure to double check you are using the version appropriate to your system and python installation.

***

Download the drivers and python bindings for **Spinnaker & Pyspin** from the official FLIR page: [FLIR - Spinnaker & PySpin](https://www.flir.co.uk/products/spinnaker-sdk/?vertical=machine+vision&segment=iis)

Spinnaker has recently moved their API and criver files into a new repository and you will need to create an account in order to access them.
Once you have created an account head to the bottom of the download page to the section **Previous Versions** and download the **2.7.0.128** version for your respective operating system.
Unpack the folder and you should find both the Spinakker API installation, as well as the required python package inside.

Unpack all files in a folder of your choice. Then proceed with the following steps:

1. Install the SpinnakerSDK...exe (likely the x64 version):
* choose **Application Development** in the installation profile.
* if you have **not** installed Visual Studio, choose the latest version shown in the installer and the recommeneded packages
* select "I will use GigE cameras" if applicable (we use a USB 3.0 version of the FLIR BFS) 
* no need to participate in any evaluation programs if you don't want to

2. Next, install the downloaded **.whl** file for your python environment. Ensure you activate your python environment before running the **pip install** command below. Ensure your python environment is active and that it corresponds to the version of the chosen **.whl** file, e.g. ```python version 3.7 -> spinnaker_python-2.7.0.128-cp37-cp37m-win_amd64.whl```.

```bash
pip install spinnaker_python-x.x.x.x-cpX-cpXm-win_amd64.whl
```

3. To verify everything has been installed correctly, run **Live_view_FLIR.py** from the GUI folder. 

```bash
cd scant/GUI
python Live_view_FLIR.py
```

If a live preview of the camera appears for a few seconds and an example image is saved (within the GUI folder), all camera drivers and libraries have been installed correctly.


#### DSLR setup

(**Optional**: you only need to install the software required for your respective camera)
To use scAnt with DSLR cameras, instead of FLIR machine vision cameras, you need to install [DigiCamControl](http://digicamcontrol.com/) from the following website:

[digiCamControl Stable Version](http://digicamcontrol.com/download)

Follow the installation instructions and note the **installation path**. By default the path should be:

```bash
'C:Program Files (x86)/digiCamControl'
```

If your installation **path is different**, you will need to add the updated folder path to **GUI/Live_view_DSLR.py**

```python
# Update with the path to CameraControlCmd.exe file.
digi_cam_path = join('C:' + sep, 'Program Files (x86)', 'digiCamControl')
```

To check whether the installation and setup was successful, connect your DSLR camera to the computer (must be in MANUAL mode) and run the following commands:

```bash
conda activate scAnt
cd GUI
python Live_view_DSLR.py
```

The script will launch an instance of **digiCamControl**, read the current camera settings, and capture three images at different ISO values.


**Stepper driver setup**

1. The Pololu stepper drivers can be controlled and set up via a console. Download the drivers specific to your system from [pololu.com](https://www.pololu.com/docs/0J71/3.1), which also provides additional information regarding installation and a list of supported commands. All drivers are open-source, and the respective code can be found on [Pololu's Git](https://github.com/pololu/pololu-tic-software).

2. Unpack the downloaded pololu-tic-x.x.x-win.msi file and install the driver:
* double click the file to start the installation
* check "Add the bin directory to the **PATH environment variable**"

3. If one or all of the stepper controllers were previously plugged into your computer re-plug them, so they are recognised correctly by your computer. Now, open the terminal and run:

```bash
ticcmd --list
```

This should output a list of all connected USB stepper drivers.

4. To test which ID corresponds to which stepper, launch the **Tic Control Center** application and move the sliders. You can use this application to test each motor and set up turning speeds and assign pins for the connected endstops. 

Double check your end-stop cables are connected to the correct pins on the pololu-tic board:

- **GND**: Black
- **TX**: Green
- **RX**: Red

Then the setup should be:

**for the Z-axis (camera slider)**

![](images/stepper_set_up.png)

The TX of the limit switch of the **Z-axis** (camera slider) needs to be set to *"limit switch forward"* and to *"limit switch reverse"* for the **X-axis** (gimbal).

From **/scripts**, open the **Scanner_Controller.py** script in an editor of choice and add the **IDs** of each the stepper to the corresponding axes:

```python
self.stepperX_ID = "XXXXXXXX"
self.stepperY_ID = "YYYYYYYY"
self.stepperZ_ID = "ZZZZZZZZ"
```

**Image Processing**

A number of open source tools are used for processing the RAW images captured by the scanner. For a detailed explanation of each access to their source code, refer to the official [hugin](http://hugin.sourceforge.net/docs/) and [exiftool](https://exiftool.org/), as well as PetteriAimonen's [focus-stack](https://github.com/PetteriAimonen/focus-stack) documentation. For Windows, we provide a set of precombiled executable files of the required applications in **/external**.

***

## Quick Start Guide

After the installation, the scanner hardware and connected camera can be fully controlled via the scAnt GUI (python scAnt.py). While there is no right or wrong order to configure each component and your workflow might depend on your exact hardware, we generally set up the scanner in 3 steps: **(1) Configuring the Camera**, **(2) configuring the Stepper Motors**, and **(3) Configuring the Scanning Process**, i.e. saving the project as well as starting the scan.

![](images/GUIScanTab.png)
![](images/GUIPostProcess.png)

**Configuring the Camera**

From the first box in the Camera Settings box, **select your connected camera**. Depending on which type of camera model you have connected, you will be able to control different settings. For FLIR Blackfly cameras, the options include:

* **Exposure auto** – Automatically sets exposure time. Useful for finding initial values but needs to be disabled for the scanning process
* **Exposure time [us]** – The total time to capture an entire scan scales linearly with the exposure time chosen here. However, as a larger exposure time allows the user to minimise the gain level which in turn minimises noise, quality may dominate speed here.  
* **Gain auto** – Similarly to Exposure auto, this option should only be used for the initial setup and not during scanning.
* **Gain Level** – influences the brightness of the image by setting the image sensor's sensitivity higher or lower. Lower levels generally reduce image noise.
* **Gamma** – Applies contrast correction, affecting primarily mid-tones.
* **Balance Ratio (Red/Blue)** – used to adjust the white balance of the image
* **Highlight Exposure** – Highlights overexposed regions of the live view image in red and displays normalised colour curves in the bottom right corner.
* **Start / Stop Live View** – displays the current video feed of the connected camera (when using DSLR cameras, an instance of DigiCamControl will be opened in an external window, and the camera live view is displayed there)
* **Capture image** – An image will be captured with the current settings and saved to the output folder specified in the **Scanner Setup section**.

1. Before picking your settings, you should first move the camera to a position where the specimen within the scanner is in focus and occupies as much of the field of view as possible while not extending beyond it. In the **Stepper Controller** section, you will first have to click "**Home X-Axis**" and "**Home Z-Axis**", which returns the motors to their zero positions. Afterwards, set the **X-Axis** to **190**, which moves the gimbal arm's pitch perpendicular to the ground. The position of the camera will depend on the used camera type and model. In our case, a value of ~ **-20000** will bring the specimen (partially) into focus. 

2. Turn on "**Start Live View**" and "**Highlight Exposure**" to display overexposed areas (red) and normalised colour curves on top of the live view image. 

3. Increase the **exposure/gain** until the image is evenly exposed. Ensure no parts of the specimen are highlighted in red, as these overexposed areas will result in loss of information (you may ignore the pin here).

4. Correct the white balance of the image by adjusting the red and blue **Balance Ratio**, respectively. You can use the colour curves displayed in the **Live View** as a rough guide by aligning the blue and red curves with the green curve, as the neutrally grey background makes up the largest number of image pixels. If you cannot find suitable settings or the specimen appears discoloured, remove it from the illumination chamber, and calibrate the white balance only based on the background. For a finer colour calibration and correction, refer to the official [OpenCV documentation](https://docs.opencv.org/master/d1/dc1/tutorial_ccm_color_correction_model.html) or your camera's manufacturer.

5. In the Post Processing tab, choose your camera's make and model if it hasn't automatically updated and fill in the lens and camera details (most importantly the focal length of your lens - the corresponding focal length in 35mm format should update automatically)

**Configuring the Stepper Motors**

The most critical parameters that need to be configured for the scan are the step sizes for each axis and the Min **[Z axis]** and Max **[Z axis]** values. 

1. We have achieved the best results with a **[X Axis]** step value of **50**, and a **[Y axis]** step value of **40**. Although finer resolutions are possible, we haven't observed notable changes in mesh quality when decreasing the step size further. The **Max [X Axis]** and **Max [Y Axis]** should be left unchanged unless the scanner is supposed to be used as a stacking rail only, in which case both values should be equivalent to their respective **Min** value.
2. The  **Step [Z Axis]** should be determined by your chosen lens and aperture's depth of field. As a rule of thumb, the step size should be equivalent to roughly half the field's depth to achieve adequate overlap of in-focus areas during image stacking.
3. The **Min [Z axis]** and **Max [Z axis]** values should be chosen based on the size of the scanned specimen, where the **Min [Z axis]** allows the nearest part and the **Max [Z axis]** the furthest part to be in focus. 

**ATTENTION**: It may be that these positions change depending on the **X** and **Y-axis** positions, so move both (by using the **sliders** of the respective axis) to find these points. Images that are not in focus can be removed automatically, but **if a part is never in focus** in specific orientations during the scan, it will be **poorly reconstructed**.

**Configuring the Scanning Process**

1. Choose an **Output Folder** location by clicking the browse button in the **Scanner Setup** section. Or open an existing scAnt project using ctrl+o.
2. Pick an easily identifiable name for your project, such as the species of your scanned specimen. When capturing an image, saving your configuration, or starting a scan, the GUI will generate a folder with your project name in the output folder you have chosen.
3. Next, configure which processing steps you want to execute in parallel with the scan. The number of threads run in the background will be automatically determined based on the number of (virtual) threads your computer suppports.

[OPTIONAL]

All processing functions, including removing out of focus images, generating Extended Depth Of Field (EDOF) images, and generating alpha masks, can be run while capturing images or through the standalone script (processStack.py). You can also choose to run all post processing steps from the GUI by selecting a RAW image folder and hitting **Run Post Processing** in the Post Processing tab. The default values shown in the GUI generally work well for most specimens with our setup. However, the following adjustments may aid in achieving the best quality for yours:

4. Enabling **Stack images** will cause scAnt to automatically process the captured files into EDOF images. Information on the default stacking method can be found [here](https://github.com/PetteriAimonen/focus-stack).  The **Threshold (focus)** is a scalar value representing the Laplacian variance of each image required for it to be considered *"sharp enough for stacking"*. Simply put, this is used to discard images that appear entirely out of focus. This parameter is sensitive to image noise, resolution, and specimen size. Pay close attention to the messages **printed in the console**. To anticipate the results to some degree, you can use stacking option in the standalone script **(processStack.py)** to monitor the process.

5. Enabling **Mask Images** will generate an alpha mask for each stacked EDOF image. While the outline is extracted using a pretrained [random forest](https://docs.opencv.org/3.1.0/d0/da5/tutorial_ximgproc_prediction.html), the infill is removed using a simple adaptive thresholding step where pixels of a specific brightness are removed from the mask, before being cleaned up using [connected component labelling]( https://aishack.in/tutorials/connected-component-labelling/). The upper and lower bounds of the threshold need to be defined here. The easiest way to find suitable values is to capture an image of your specimen (in the Camera Settings section, click on **Capture image**) and open it in an image editor of your choice (*e.g. GIMP, MS Paint, Photoshop*). Use the **colour picker tool** to return the RGB value from various background locations, ideally close to the specimen.  Note the lowest and highest values out of all channels and fill them into the respective box. You could also do this with a system-wide color picking tool such as the one in [Microsoft PowerToys](https://learn.microsoft.com/en-us/windows/powertoys/), in which case the values can be selected from the live view in the GUI. Again, you can use the masking function of the standalone script **(processStack.py)** to verify your tests before conducting a full scan. 

6. Once everything is set up to your liking, hit **Start Scan**, and grab a cup of coffee/tea/beer, depending on the time of day.

**Happy Scanning!**


***
## Meshroom Guide

**Add your camera to the sensor database**

Within the directory of the downloaded Meshroom installation, go to the following folder and edit the file “**cameraSensors.db**” using any common text editor:

*…/Meshroom-2019.2.0/AliceVision/share/AliceVision/cameraSensors.db*

The entry should contain the following:

```bash
Make;Model;SensorWidth
```
Ensure to enter these details as they are listed in your project configuration file, thus, metadata of your stacked and masked images. There should be no spaces between the entries. If you are using the same FLIR camera as in the original **scAnt**, add the following line:

```bash
FLIR;BFS-U3-200S6C-C;13.1
```
Adding the correct sensor width is crucial in computing the camera intrinsics, such as distortion parameters, object scale, and distances. Otherwise the camera alignment, during feature matching and structure-from-motion steps are likely to fail.

Once these details have been added, launch **Meshroom** and drag your images named *…cutout.tif* into **Meshroom**. If the metadata and added camera sensor are recognised, a **green aperture icon** should be displayed over all images.

![](images/meshroom_correctly_loaded.png)

If not all images are listed, or the aperture icon remains red / yellow, execute the helper script “batch_fix_meta_data.py” to fix any issues resulting from your images' exif files. 

**Setting up the reconstruction pipeline**

*Try to run the pipeline with this configuration, before attempting to use approximated camera positions. Approximate positions should only be used if issues with the alignment of multiple camera poses arise, as fine differences in the scanner setup can cause poorer reconstruction results, without **guided matching** (available only in the **2020 version** of **Meshroom**)!*

1. **CameraInit**

- *No parameters need to be changed here.*
- However, ensure that only one element is listed under **Intrinsics**. If there is more than one, remove all images you imported previously, delete all elements listed under **Intrinsics**, and load your images again. If the issue persists, execute the helper script “batch_fix_meta_data.py” to fix any issues resulting from your images exif files. 

2. **FeatureExtraction**

- Enable Advanced Attributes** by clicking on the three dots at the upper right corner.
- Describer Types: Check **sift** and **akaze**
- Describer Preset: Normal (pick High if your subject has many fine structures)
- Force CPU Extraction: Uncheck

3. **ImageMatching**

- Max Descriptors: 10000
- Nb Matches: 200

4. **FeatureMatching**

- Describer Types: Check **sift** and **akaze**
- Guided Matching: Check

5. **StructureFromMotion**

- Describer Types: Check **sift** and **akaze**
- Local Bundle Adjustment: Check
- Maximum Number of Matches: 0 (ensures all matches are retained)

6. **PrepareDenseScene**

- *No parameters need to be changed here.*

7. **DepthMap**

- Downscale: 1 (use maximum resolution of each image to compute depth maps)

8. **DepthMapFilter**

- Min View Angle: 1
- Compute Normal Maps: Check

9. **Meshing**

- Estimate Space from SfM: Uncheck (while this will potentially produce “floaters” that need to be removed during post processing it assists in reserving very fine / long structures, such as antennae)
- Min Observations for SfM Space Estimation: 2 (only required if above attribute remains checked)
- Min Observations Angle for SfM Space Estimation: 5 (only required if above attribute remains checked)
- Max Input Points: 100000000
- simGaussianSizeInit: 5
- simGaussianSize: 5
- Add landmarks to the Dense Point Cloud: Check	

10. **MeshFiltering**

- Filter Large Triangles Factor: 40
- Smoothing Iterations: 2

11. Texturing

- Texture Side: 16384
- Unwrap Method: **LSCM** (will lead to larger texture files, but much higher surface quality)
- Texture File Type: png
- Fill Holes: Check

Now click on **start** and watch the magic happen. Actually, this is the best time to grab a cup of coffee, as the reconstruction process takes between 3 and 10 hours, depending on your step size, camera resolution, and system specs.

**Exporting the textured mesh:**

All outputs within Meshroom are automatically saved in the project’s environment. By right clicking on the **Texturing node** and choosing “**Open Folder**” the location of the created mesh (**.obj** file) is shown.

***

## Todos

### Software updates / fixes

#### bug fixes

* compile all current requests / issues on the main scAnt Github to see where actual issues need to be addressed and where it is an improved documentation that is required

#### scAnt GUI updates

* check the use of experimental stacking on Linux (disable for now)
* add checkbox option under stacking for "crop to in-focus area" (Currently, stacking returns a cropped image of "only in focus regions" which can be enabled / disabled via the CLI command sent to the new stacking routine. While it generally helps the masking process to exclude the out-of-focus borders, it can lead to issues during reconstruction as the camera intrinsics no longer correspond to the image dimensions and the image centre may be shifted)

#### scAnt general functionality & documentation

* write a calibration routine (and later add to scAnt GUI, potentially in separate calibration Window from which additional calibration options like stacking, masking, camera intrinsics can be set by the user)
  * select stepper drivers and assign them to axes
  * check for the option to configure end-stop connection and location (front vs back)
* add support for generic USB stepper driver via 3D printer board / custom scAnt board (tbd)
* Add DSLR support through gphoto2 under Linux
* code-clean-up: remove all old post-processing code, make a single python file that contains all post-processing functions that can be both used from the scAnt GUI as well as a standalone command line-based script
* update documentation on anaconda environment use

#### make scAnt operating system agnostic
  * start by ensuring all file paths use path handling via (e.g.) ```os.Path``` rather than mixed use of ```\``` and ```//```
  * compile a list of features that are specific to certain operating systems and cannot be supported via the same methods, e.g. DSLR use via DigiCamControl (Windows) vs gphoto (Ubuntu)
  * bundle all dependencies to create installer / binary versions of the scAnt software stack
  * create "install wizard" for scAnt (starting with Windows first, as that's the largest user base)

### Hardware design and manufacturing

* use geared stepper for X axis or build geared stepper
* Research cost of making custom PCBs with ATmega based chipset and RAMPS for control, instead of expensive Pololu stepper drivers
  * check for the cost to manufacture PCBs
  * check for the cost of ATmega controllers
  * check which stepper drivers are needed (standard RAMP will likely suffice)
  * add controllable outputs for high voltage high amperage lights (that can be turned on and off via scAnt GUI / scanning routine)
  * add a connection for end stops and proper sockets to make everything plug-and-play
  * add clear separation between high and low power circuit for 24V 5A power supply
* Design interchangeable DSLR/FLIR mount
* Move the end-stop to the opposite side for the Z-axis (safer and more universally applicable)

***
## Original paper
Plum F, Labonte D. 2021. scAnt—an open-source platform for the creation of 3D models of arthropods (and other small objects) 
PeerJ 9:e11155 https://doi.org/10.7717/peerj.11155

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
**scAnt** - Open Source 3D Scanner and Processing Pipeline

© Fabian Plum, 2020
[MIT License](https://choosealicense.com/licenses/mit/)
