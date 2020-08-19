# scAnt - Open Source 3D Scanner

**scAnt** is a completely open source and low-cost macro 3D scanner, designed to digitise insects of a vast size range and in full colour. Aiming to automate the capturing process of specimens as much as possible, the project comes complete with example configurations for the scanning process, scripts including stacking and complex masking of images to prepare them for various photogrammetry software.

![](images/model_collection_showcase_04.png)


All structural components of the scanner are manufactured using 3D-printers and laser cutters and are available for download as .ipt, .iam, .stl, and .svg files from our [thingiverse](https://www.thingiverse.com/fabianplum/designs) page


![](images/scanner_3D_comp.png)

## Installation
**scAnt** is supported by 64 bit versions of **Windows 10** and **Ubuntu 18.04**. Newer releases of Ubuntu will likely not pose an issue but only these configurations have been tested so far. The pipeline and GUI have been designed specifically for use with [FLIR Blackfly](https://www.flir.co.uk/products/blackfly-s-usb3/) cameras, and [Pololu USB Stepper drivers](https://www.pololu.com/category/212/tic-stepper-motor-controllers) to limit the number of required components for the scanner as much as possible. We are planning on including support for other cameras and stepper drivers in the future as well. Please refer to our [thingiverse](https://www.thingiverse.com/fabianplum/designs) page for a full list of components.

The easiest way to get your scanner up and running is by installing our pre-configured anaconda environment. 

```bash
cd conda_environment
conda env create -f scAnt.yml
```

Additional drivers and libraries for the used FLIR camera and stepper drivers need to be installed specific to your system.

## Usage

```python
import scAnt

this is where code could be
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
scAnt - Open Source 3D Scanner and Processing Pipeline

© Fabian Plum, 2020
[MIT License](https://choosealicense.com/licenses/mit/)
