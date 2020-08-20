# scAnt - Open Source 3D Scanner

**scAnt** is a completely open source and low-cost macro 3D scanner, designed to digitise insects of a vast size range and in full colour. Aiming to automate the capturing process of specimens as much as possible, the project comes complete with example configurations for the scanning process, as well as additional scripts including stacking and complex masking of images to prepare them for various photogrammetry software of your choice! For a look at a few **scAnt** results check-out http://bit.ly/ScAnt-3D

![](images/model_collection_showcase_04.png)

All structural components of the scanner can be manufactured using 3D-printing and laser cutting and are available for download as .ipt, .iam, .stl, and .svg files from our [thingiverse](https://www.thingiverse.com/fabianplum/designs) page.

![](images/scanner_3D_comp.png)

## Installation
**scAnt** is supported by 64 bit versions of **Windows 10** and **Ubuntu 18.04**. Newer releases of Ubuntu will likely not pose an issue but only these configurations have been tested so far. The pipeline and GUI have been designed specifically for use with [FLIR Blackfly](https://www.flir.co.uk/products/blackfly-s-usb3/) cameras, and [Pololu USB Stepper drivers](https://www.pololu.com/category/212/tic-stepper-motor-controllers) to limit the number of required components for the scanner as much as possible. We are planning on including support for other cameras and stepper drivers in the future as well. Please refer to our [thingiverse](https://www.thingiverse.com/fabianplum/designs) page for a full list of components.

The easiest way to get your scanner up and running is by installing our pre-configured anaconda environment. 

```bash
cd conda_environment
conda env create -f scAnt_UBUNTU.yml
```

After the environment has been created successfully, close the terminal and open a new one. Run the following line to activate your new environment and continue the installation.

 ```bash
conda activate scAnt
```

If you instead prefer to use other package managers or want to integrate the scanner into an existing environment, here is a list of package requirements:

  - python >= 3.6
  - pip
  - numpy
  - matplotlib
  - opencv >= 4.1.0
  - pyqt 5
  - imutils
  - pillow
  - scikit-image


Additionally, drivers and libraries for the used camera and stepper drivers need to be installed, specific to your system.
***

**Ubuntu 18.04**

Download the drivers and python bindings for **Spinnaker & Pyspin** from the official FLIR page:

[meta.box.lenovo.com](https://meta.box.lenovo.com/v/link/view/a1995795ffba47dbbe45771477319cc3)


**FLIR Support / Spinnaker / Linux Ubuntu / Ubuntu 18.04**

*download the tar.gz file for your architecture (usually amd64)*

**FLIR Support / Spinnaker / Linux Ubuntu / Python / Ubuntu 18.04 / x64**

*depending on your python version, download the respective file. For our conda environment download **...cp37-cp37m_linux_x86_64.tar.gz***


Unpack all files in a folder of your choice before you continue

1. Install all required dependencies before installing FLIR's Spinnaker software

```bash
sudo apt-get install libavcodec57 libavformat57 libswscale4 libswresample2 libavutil55 libusb-1.0-0 libgtkmm-2.4-dev
```

2. Once all dependencies are installed, install spinnaker from its extracted folder

```bash
sudo sh install_spinnaker.sh
```

3. during installation ensure to add your user to the user-group and accept increasing allocated USB-FS memory size to 1000 MB in order to increase the video stream buffer size

4. **Reboot** your computer to make the installation become effective

5. launch spinview and connect your FLIR camera to verify your installation (if the application is already launched when plugging in your camera, refresh the list in case it is not listed right away)

6. now install the downloaded **.whl** file for your python environment. Ensure you activate your python environment before running the **pip install** command below.

```bash
pip install spinnaker_python-1.x.x.x-cp37-cp37m-linux_x86_64.whl
```

7. To verify everything has to be installed correctly run **Live_view_FLIR.py** from the GUI folder. 

```bash
cd scant/GUI
python Live_view_FLIR.py
```

If a live preview of the camera appears for a few seconds and an example image is saved (within the GUI folder), all camera drivers and libraries have been installed correctly!

**Stepper driver setup**

1. The Pololu stepper drivers can be controlled and set up via console based commands. Simply download the drivers specific to your system from [pololu.com](https://www.pololu.com/docs/0J71/3) Additional information regarding installation and a list of supported commands can also be found there. As all drivers used are open source as well, their code can be found on [Pololu's Git](https://github.com/pololu/pololu-tic-software) as well.

2. Simply unpack the downloaded .tar.xy file and install the driver by:

```bash
sudo pololu-tic-*/install.sh
```

3. Afterwards, **reboot** your computer to update your user privileges automatically, otherwise you will have to use **sudo** to access your USB stepper drivers.

4. If one or all of the stepper controllers were previously plugged into your computer unplug them and then plug them back in, so they are recognised correctly by your computer. Now, open the terminal and run the following command:

```bash
ticcmd –list
```

This should output a list of all connected USB stepper drivers. 

5. Now that your camera and steppers are all set up, you can run a complete functionality check of the scanner by running the **Scanner_Controller.py** script.

```bash
cd scAnt/scripts
python Scanner_Controller.py
```
- the scanner will then home all axes, drive to a set of example positions and capture images as it would during scanning for a very coarse grid.
- If no errors appear, images will be saved and “Demo completed successfully” is printed to the console

**Image Processing**

A number of open source tools are used for processing the RAW images captured by the scanner. For a detailed explanation of each, just ask me tomorrow, because I'm a little tired right now. Anyway, here are the lines you need to install all the good stuff:

```bash
sudo add-apt-repository ppa:hugin/hugin-builds
sudo apt-get update
sudo apt-get install hugin enblend
sudo apt install hugin-tools
sudo apt install enfuse
sudo apt install libimage-exiftool-perl
```

***

**Windows** installation guide coming soon

***

## Usage

```python
import scAnt

Then run scAnt.py
#duh
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
**scAnt** - Open Source 3D Scanner and Processing Pipeline

© Fabian Plum, 2020
[MIT License](https://choosealicense.com/licenses/mit/)
