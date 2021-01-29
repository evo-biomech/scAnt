import yaml
from pathlib import Path

"""
List of parameters:

# general
project_name:

# camera settings
camera_type:
camera_model:
exposure_auto:
exposure_time:
gain_auto:
gain_level:
gamma:
balance_ratio_red:
balance_ratio_blue:
shutterspeed:
aperture:
iso:
whitebalance:
compression:

# stacking
stack_images:
stacking_method:
threshold:
display_focus_check:
additional_sharpening

# masking
mask_images:
mask_thresh_min:
mask_thresh_mask:
min_artifact_size_black:
min_artifact_size_white:

# exif_data
Make:
Model:
SerialNumber:
Lens:
CameraSerialNumber:
LensManufacturer:
LensModel:
FocalLength:
FocalLengthIn35mmFormat:
"""

# All common exif data entries are supported. For additional entries refer to exiftool.org
# The examples above are included here, as they relevant for most reconstruction software


def read_config_file(path):
    # read config files from path and return its contents
    with open(path) as f:
        config_dict = yaml.load(f, Loader=yaml.FullLoader)

    return config_dict


def write_config_file(content, path):
    with open(path.joinpath(content["general"]["project_name"] + "_config.yaml"), "w") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)


if __name__ == '__main__':
    config = read_config_file(Path.cwd().parent.joinpath("example_config.yaml"))
    print(config)

    write_config_file(content=config, path=Path.cwd().parent)
