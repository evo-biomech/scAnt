import os
import cv2
import shutil
import numpy as np


def doLap(image):
    # YOU SHOULD TUNE THESE VALUES TO SUIT YOUR NEEDS
    kernel_size = 11  # Size of the laplacian window
    blur_size = 11  # How big of a kernal to use for the gaussian blur
    # Generally, keeping these two values the same or very close works well
    # Also, odd numbers, please...
    # blurred = cv2.GaussianBlur(image, (blur_size, blur_size), 0)               #not used
    return cv2.Laplacian(image, cv2.CV_64F, ksize=kernel_size)  # cv2.CV_64F


#
#   This routine finds the points of best focus in all images and produces a merged result...
#
def focus_stack(images, show_aligned_img=False):
    laps = []
    kernel = np.ones((13, 13), np.uint8)

    for i in range(len(images)):
        print("Lap {}".format(i))
        curlab = doLap(cv2.cvtColor(images[i], cv2.COLOR_BGR2GRAY))
        curlab = cv2.dilate(curlab, kernel, iterations=2)
        curlab = cv2.erode(curlab, kernel, iterations=2)
        laps.append(curlab)

    laps = np.asarray(laps)
    print("Shape of array of laplacians = {}".format(laps.shape))

    output = np.zeros(shape=images[0].shape, dtype=images[0].dtype)
    output2 = np.zeros(shape=images[0].shape, dtype=images[0].dtype)

    abs_laps = np.absolute(laps)
    maxima = abs_laps.max(axis=0)
    bool_mask = abs_laps == maxima
    mask = bool_mask.astype(np.uint8)
    for i in range(0, len(images)):
        FillValue = 255.0 / len(images) * i
        output2 = cv2.bitwise_not(images[i], output2, mask=mask[i])
        output = cv2.bitwise_not(np.full_like(images[i], (FillValue, FillValue, FillValue)), output, mask=mask[i])
    return (255 - output), (255 - output2)


if __name__ == "__main__":

    my_path = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(my_path, "images")
    OutP = os.path.join(my_path, "Out")

    ResizeImg = 'n'  # input('Resize? [y/n] Defaults to n : ') or 'n'
    if ResizeImg == 'y':
        scale_percent = float(input('Resize in Percent.  Defaults to 50 : ') or '50')

    # Get All Images in Dir
    for idx, file in enumerate(os.listdir(path)):
        filename = os.fsdecode(file)
        if filename.endswith((".tif", ".tiff", ".jpg", ".JPG", ".png", ".tga")):
            if idx == 0:
                Files = [os.path.join(path, filename)]
            else:
                Files = Files + [os.path.join(path, filename)]

    images = np.asarray([cv2.imread(p) for p in Files])

    for idx, i in enumerate(images):
        img = i
        if idx == 0:
            width = int(img.shape[1])
            height = int(img.shape[0])
            dim = (width, height)
            Finalimg = np.empty((height, width), dtype=np.float64)

        if ResizeImg == 'y':
            if idx == 0:
                width = int(width * scale_percent / 100)
                height = int(height * scale_percent / 100)
                dim = (width, height)
            ResImg = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
            img = ResImg

    Finalimg, stimg = focus_stack(images)

    ret, BGMask = cv2.threshold(stimg, 120, 255, cv2.THRESH_BINARY)
    Finalimg = cv2.addWeighted(Finalimg, 1, BGMask, 1, 0.0, Finalimg)
    Finalimg = cv2.cvtColor(Finalimg, cv2.COLOR_BGR2GRAY)
    # Finalimg = cv2.fastNlMeansDenoising(Finalimg,h=25,templateWindowSize=7,searchWindowSize=21)

    # Create Output folder

    if not os.path.exists(OutP):
        os.makedirs(OutP)
        print('Folder: "' + OutP + '" was created.')
        # Save Out images

    cv2.imwrite(os.path.join(my_path, OutP) + '\Out' + str(idx) + '.tiff', Finalimg)
    print('Saved File : ' + OutP + '\Out' + str(idx) + '.tif')
    shutil.copystat(Files[idx], (os.path.join(my_path, OutP) + '\Out' + str(idx) + '.tiff'))  # , follow_symlinks=True)
