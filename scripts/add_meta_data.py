import glob
import piexif
import pickle
from PIL import Image

images = []

#folder_name = "Run_HD"
folder_name = "Ant_Scan_V0.1_cropped"


def edit_exif(file, target_exiv):
    """
    Writes the data contained in the specified exiv to the loaded file

    :param file: location of image file (jpg format!)
    :param target_exiv: location of .pkl file containing the desired exiv
    :return: writes exiv to image
    """
    with open(target_exiv, 'rb') as f:
        imported_exif = pickle.load(f)

    new_exif_bytes = piexif.dump(imported_exif)

    piexif.insert(new_exif_bytes, file)


def extract_exif(file, output_path):
    """
    Writes the exif data from a file to a desired location as a .pkl file

    :param file: loaction of image file (jpg format!)
    :param output_path: loaction of output .pkl file
    :return: dict of the exif file (needs to be converted to bytes, using piexiv.dump)
    """

    exif_dict_goal = piexif.load(file)

    with open(output_path, 'wb') as f:
        pickle.dump(exif_dict_goal, f, pickle.HIGHEST_PROTOCOL)


for file in glob.glob(folder_name + '/*.jpg'):
    with open(file, 'rb') as image_file:
        images.append(Image.open(image_file))
    exif_dict = piexif.load(file)

print(len(images))

exif_file = folder_name + '/example_exif'


piexif.transplant(folder_name + '/example_exiv', folder_name + '/SICB- - Copy.jpg')

exif_dict_orig = piexif.load(folder_name + '/SICB- - Copy.jpg')
print(exif_dict_orig)  #
