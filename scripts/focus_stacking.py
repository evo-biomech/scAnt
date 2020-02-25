# approach implemented based on
# pyimagesearch.com/2015/09/07/blur-detection-with-opencv/

# Use in the console with
"""
$ python Focus_stacking.py --images images
"""

from imutils import paths
import argparse
import cv2
import os
from PIL import Image, ImageEnhance


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
    return cv2.Laplacian(blurred_image, cv2.CV_64F).var()


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--images", required=True,
                help="path to input directory of images")
ap.add_argument("-t", "--threshold", type=float, default=3.0,
                help="focus measures that fall below this value will be considered 'blurry'")
ap.add_argument("-s", "--sharpen", type=float, default=False,
                help="apply sharpening to final result")
args = vars(ap.parse_args())

usable_images = []
rejected_images = []

blurry_removed = input("Have you removed blurry images already? [y/n] default n")

cv2.ocl.setUseOpenCL(True)

# loop over the input images
for imagePath in sorted(paths.list_images(args["images"])):
    # load the image, convert it to grayscale, and compute the
    # focus measure of the image using the Variance of Laplacian
    # method

    if blurry_removed != "y":
        image = cv2.imread(imagePath)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fm = variance_of_laplacian(gray)

        # if the focus measure is less than the supplied threshold,
        # then the image should be considered "blurry"
        if fm < args["threshold"]:
            text = "BLURRY"
            color_text = (0, 0, 255)
            rejected_images.append(imagePath)
        else:
            text = "NOT Blurry"
            color_text = (255, 0, 0)
            usable_images.append(imagePath)

        print(imagePath, "is", text)

        # original window size (due to input image)
        # = 2448 x 2048 -> time to size it down!
        scale_percent = 30  # percent of original size
        width = int(image.shape[1] * scale_percent / 100)
        height = int(image.shape[0] * scale_percent / 100)
        dim = (width, height)
        # resize image
        resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

        # show the image
        cv2.putText(resized, "{}: {:.2f}".format(text, fm), (10, 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, color_text, 3)
        cv2.imshow("Image", resized)

        cv2.waitKey(10)

    else:
        # simply include all images if blurry images have already been removed
        usable_images.append(imagePath)

cv2.destroyAllWindows()

if len(usable_images) > 1:
    print("\nThe following images are sharp enough for focus stacking:\n")
    for path in usable_images:
        print(path)
else:
    print("No images suitable for focus stacking found!")
    exit()

path_to_external = os.path.dirname(os.getcwd()) + "\\external\\"

pics = len(usable_images)

output_folder = args["images"] + "_stacked"

if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print("made folder!")

for i in range(pics):

    # Align all images using Hugin's align_image_stack function

    print("\nAligning images...\n")
    image_str_align = ""

    current_stack_name = usable_images[0][:-15]
    print("Using:", current_stack_name, "\n")

    path_num = 0
    for path in usable_images:
        if current_stack_name == path[:-15]:
            image_str_align += " " + path
            path_num += 1
        else:
            break

    del usable_images[0:path_num]

    os.system(path_to_external + "align_image_stack -m -x -c 100 -a " + output_folder + "\\OUT" + image_str_align)

    image_str_focus = ""
    temp_files = []
    print("\nFocus stacking...")
    # go through list in reverse order (better results of focus stacking)
    for img in range(path_num):
        if img < 10:
            path = output_folder + "\\OUT000" + str(img) + ".tif"
        elif img < 100:
            path = output_folder + "\\OUT00" + str(img) + ".tif"
        elif img < 1000:
            path = output_folder + "\\OUT0" + str(img) + ".tif"
        else:
            path = output_folder + "\\OUT" + str(img) + ".tif"

        temp_files.append(path)
        image_str_focus += " " + path

    output_path = output_folder + "\\" + current_stack_name.split('\\')[-1] + ".tif"
    print(output_path)

    # --save-masks     to save soft and hard masks
    # --gray-projector=l-star alternative stacking method
    os.system(path_to_external + "enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 " +
              "--hard-mask --contrast-edge-scale=1 --output=" +
              output_path + image_str_focus)

    print("Stacked image saved as", output_path)

    stacked = Image.open(output_path)
    if args["sharpen"]:
        enhancer = ImageEnhance.Sharpness(stacked)
        sharpened = enhancer.enhance(1.5)
        sharpened.save(output_path)

    print("Sharpened", output_path)

    for temp_img in temp_files:
        os.system("del " + str(temp_img))

    print("Deleted temporary files.")

    # check if there are images left in the useable images
    if len(usable_images) < 2:
        break
    else:
        print("Images left to stack:", len(usable_images))

print("Stacking finalised!")
