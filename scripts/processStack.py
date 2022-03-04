# image processing utilities to create stacked / blended / masked images while scanning


import cv2
import os

from PIL import Image, ImageEnhance
from skimage import measure
import sys
import numpy as np
from pathlib import Path
import platform


def getThreads():
    """ Returns the number of available threads on a linux/win based system """
    if sys.platform == 'win32':
        return int(os.environ['NUMBER_OF_PROCESSORS'])
    else:
        return int(os.popen('grep -c cores /proc/cpuinfo').read())


"""
Stacking Section
"""


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


def checkFocus(image_path, threshold, usable_images, rejected_images):
    image = cv2.imread(str(image_path))

    # original window size (due to input image)
    # = 2448 x 2048 -> time to size it down!
    scale_percent = 15  # percent of original size
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    # resize image
    resized = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    fm = variance_of_laplacian(gray)

    # if the focus measure is less than the supplied threshold,
    # then the image should be considered "blurry"
    if fm < threshold:
        text = "BLURRY"
        color_text = (0, 0, 255)
        rejected_images.append(image_path.name)
    else:
        text = "NOT Blurry"
        color_text = (255, 0, 0)
        usable_images.append(image_path.name)

    print(image_path.name, "is", text)

    return usable_images, rejected_images


def process_stack(data, output_folder, path_to_external, sharpen):
    stack_name = data.split(" ")[1]
    stack_name = Path(stack_name).name[:-15]

    temp_output_folder = output_folder.joinpath(stack_name)

    used_platform = platform.system()

    if used_platform == "Linux":
        os.system("align_image_stack -m -x -c 100 -a " + str(
            temp_output_folder.joinpath(stack_name))
                  + "OUT" + data)
    else:
        # use additional external files under windows to execute alignment via hugin
        os.system(str(path_to_external) + "\\align_image_stack -m -x -c 100 -a " + str(
            temp_output_folder.joinpath(stack_name))
                  + "OUT" + data)

    image_str_focus = ""
    temp_files = []
    print("\nFocus stacking...")

    num_images_in_stack = len(data.split(" ")) - 1

    # go through list in reverse order (better results of focus stacking)
    for img in range(num_images_in_stack):
        if img < 10:
            path = str(temp_output_folder.joinpath(stack_name)) + "OUT000" + str(img) + ".tif"
        elif img < 100:
            path = str(temp_output_folder.joinpath(stack_name)) + "OUT00" + str(img) + ".tif"
        elif img < 1000:
            path = str(temp_output_folder.joinpath(stack_name)) + "OUT0" + str(img) + ".tif"
        else:
            path = str(temp_output_folder.joinpath(stack_name)) + "OUT" + str(img) + ".tif"

        temp_files.append(path)
        image_str_focus += " " + path

    output_path = str(output_folder.joinpath(stack_name)) + ".tif"
    print(output_path)

    print("generating:", image_str_focus + "\n")

    # --save-masks     to save soft and hard masks
    # --gray-projector=l-star alternative stacking method

    if used_platform == "Linux":
        os.system("enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 " +
                  "--hard-mask --contrast-edge-scale=1 --output=" +
                  output_path + image_str_focus)
    else:
        os.system(str(path_to_external) + "\\enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 " +
                  "--hard-mask --contrast-edge-scale=1 --output=" +
                  output_path + image_str_focus)

    print("Stacked image saved as", output_path)

    stacked = Image.open(output_path)
    if sharpen:
        enhancer = ImageEnhance.Sharpness(stacked)
        sharpened = enhancer.enhance(1.5)
        sharpened.save(output_path)

        print("Sharpened", output_path)

    for temp_img in temp_files:
        if used_platform == "Linux":
            os.system("rm " + str(temp_img))
        else:
            os.system("del " + str(temp_img))

    print("Deleted temporary files of stack", data)

    return output_path


def stack_images(input_paths, threshold=10.0, sharpen=False, stacking_method="Default"):
    images = Path(input_paths[0]).parent

    all_image_paths = []
    for img_path in input_paths:
        all_image_paths.append(Path(img_path))

    usable_images = []
    rejected_images = []

    for path in all_image_paths:
        usable_images, rejected_images = checkFocus(path, threshold, usable_images, rejected_images)

    usable_images.sort()

    if len(usable_images) > 1:
        print("\nThe following images are sharp enough for focus stacking:\n")
        for path in usable_images:
            print(path)
    else:
        print("No images suitable for focus stacking found!")
        exit()

    path_to_external = Path.cwd().joinpath("external")
    output_folder = images.parent.joinpath("stacked")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print("made folder!")

    # revert the order of images to begin with the image furthest away
    # -> maximise field of view during alignment and leads to better blending results with less ghosting
    usable_images.reverse()

    # group images of each stack together
    pics = len(usable_images)
    stacks = []

    print("\nSorting in-focus images into stacks...")
    for i in range(pics):

        image_str_align = ""

        current_stack_name = usable_images[0][:-15]
        print("Created stack:", current_stack_name)

        if not os.path.exists(output_folder.joinpath(current_stack_name)):
            os.makedirs(output_folder.joinpath(current_stack_name))
            print("made corresponding temporary folder!")
        else:
            print("corresponding temporary folder already exists!")

        path_num = 0
        for path in usable_images:
            if current_stack_name == str(path)[:-15]:
                image_str_align += " " + str(images.joinpath(path))
                path_num += 1
            else:
                break

        del usable_images[0:path_num]

        stacks.append(image_str_align)

        if len(usable_images) < 2:
            break

    # sort stacks in ascending order
    stacks.sort()

    """
    ### Alignment and stacking of images ###
    """

    stacked_images_paths = []

    for stack in stacks:
        stacked_images_paths.append(
            process_stack(data=stack, output_folder=output_folder, path_to_external=path_to_external, sharpen=sharpen))

    print("Deleting temporary folders")

    for stack in stacks:
        stack_name = stack.split(" ")[1]
        stack_name = Path(stack_name).name[:-15]
        os.rmdir(output_folder.joinpath(stack_name))
        print("removed  ...", stack_name)

    print("Stacking finalised!")

    return stacked_images_paths


"""
Masking Section
"""


def filterOutSaltPepperNoise(edgeImg):
    # Get rid of salt & pepper noise.
    count = 0
    lastMedian = edgeImg
    median = cv2.medianBlur(edgeImg, 3)
    while not np.array_equal(lastMedian, median):
        # get those pixels that gets zeroed out
        zeroed = np.invert(np.logical_and(median, edgeImg))
        edgeImg[zeroed] = 0

        count = count + 1
        if count > 70:
            break
        lastMedian = median
        median = cv2.medianBlur(edgeImg, 3)


def findSignificantContour(edgeImg):
    try:
        image, contours, hierarchy = cv2.findContours(
            edgeImg,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE)
    except ValueError:
        contours, hierarchy = cv2.findContours(
            edgeImg,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE)
    # Find level 1 contours (i.e. largest contours)
    level1Meta = []
    for contourIndex, tupl in enumerate(hierarchy[0]):
        # Each array is in format (Next, Prev, First child, Parent)
        # Filter the ones without parent
        if tupl[3] == -1:
            tupl = np.insert(tupl.copy(), 0, [contourIndex])
            level1Meta.append(tupl)
            #  # From among them, find the contours with large surface area.
    contoursWithArea = []
    for tupl in level1Meta:
        contourIndex = tupl[0]
        contour = contours[contourIndex]
        area = cv2.contourArea(contour)
        contoursWithArea.append([contour, area, contourIndex])

    contoursWithArea.sort(key=lambda meta: meta[1], reverse=True)
    largestContour = contoursWithArea[0][0]
    return largestContour


def remove_holes(img, min_num_pixel):
    cleaned_img = np.zeros(shape=(img.shape[0], img.shape[1]))

    unique, counts = np.unique(img, return_counts=True)
    print("\nunique values:", unique)
    print("counted:", counts)

    for label in range(len(counts)):
        if counts[label] > min_num_pixel:
            if unique[label] != 0:
                cleaned_img[img == unique[label]] = 1

    return cleaned_img


def apply_local_contrast(img, grid_size=(7, 7)):
    """
    ### CLAHE (Contrast limited Adaptive Histogram Equilisation) ###

    Advanced application of local contrast. Adaptive histogram equalization is used to locally increase the contrast,
    rather than globally, so bright areas are not pushed into over exposed areas of the histogram. The image is tiled
    into a fixed size grid. Noise needs to be removed prior to this process, as it would be greatly amplified otherwise.
    Similar to Adobe's "Clarity" option which also amplifies local contrast and thus pronounces edges, reduces haze.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred_gray = cv2.GaussianBlur(gray, (5, 5), 0)

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=grid_size)
    cl1 = clahe.apply(blurred_gray)

    # convert to PIL format to apply laplacian sharpening
    img_pil = Image.fromarray(cl1)

    enhancer = ImageEnhance.Sharpness(img_pil)
    sharpened = enhancer.enhance(31)

    return cv2.cvtColor(np.array(sharpened), cv2.COLOR_GRAY2RGB)


def createAlphaMask(data, edgeDetector, min_rgb, max_rgb, min_bl, min_wh, create_cutout=True):
    """
    create alpha mask for the image located in path
    :img_path: image location
    :create_cutout: additionally save final image with as the stacked image with the mask as an alpha layer
    :return: writes image to same location as input
    """
    src = cv2.imread(data, 1)

    img_enhanced = apply_local_contrast(src)

    # reduce noise in the image before detecting edges
    blurred = cv2.GaussianBlur(img_enhanced, (5, 5), 0)

    # turn image into float array
    blurred_float = blurred.astype(np.float32) / 255.0
    edges = edgeDetector.detectEdges(blurred_float) * 255.0

    edges_8u = np.asarray(edges, np.uint8)
    filterOutSaltPepperNoise(edges_8u)

    contour = findSignificantContour(edges_8u)
    # Draw the contour on the original image
    contourImg = np.copy(src)
    cv2.drawContours(contourImg, [contour], 0, (0, 255, 0), 2, cv2.LINE_AA, maxLevel=1)
    # cv2.imwrite(data[:-4] + '_contour.png', contourImg)

    mask = np.zeros_like(edges_8u)
    cv2.fillPoly(mask, [contour], 255)

    # calculate sure foreground area by dilating the mask
    mapFg = cv2.erode(mask, np.ones((5, 5), np.uint8), iterations=10)

    # mark inital mask as "probably background"
    # and mapFg as sure foreground
    trimap = np.copy(mask)
    trimap[mask == 0] = cv2.GC_BGD
    trimap[mask == 255] = cv2.GC_PR_BGD
    trimap[mapFg == 255] = cv2.GC_FGD

    # visualize trimap
    trimap_print = np.copy(trimap)
    trimap_print[trimap_print == cv2.GC_PR_BGD] = 128
    trimap_print[trimap_print == cv2.GC_FGD] = 255
    # cv2.imwrite(data[:-4] + '_trimap.png', trimap_print)

    # run grabcut
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (0, 0, mask.shape[0] - 1, mask.shape[1] - 1)
    cv2.grabCut(src, trimap, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_MASK)

    # create mask again
    mask2 = np.where(
        (trimap == cv2.GC_FGD) | (trimap == cv2.GC_PR_FGD),
        255,
        0
    ).astype('uint8')

    contour2 = findSignificantContour(mask2)
    mask3 = np.zeros_like(mask2)
    cv2.fillPoly(mask3, [contour2], 255)

    # blended alpha cut-out
    mask3 = np.repeat(mask3[:, :, np.newaxis], 3, axis=2)
    mask4 = cv2.GaussianBlur(mask3, (3, 3), 0)
    alpha = mask4.astype(float) * 1.1  # making blend stronger
    alpha[mask3 > 0] = 255
    alpha[alpha > 255] = 255
    alpha = alpha.astype(float)

    foreground = np.copy(src).astype(float)
    foreground[mask4 == 0] = 0
    background = np.ones_like(foreground, dtype=float) * 255

    # Normalize the alpha mask to keep intensity between 0 and 1
    alpha = alpha / 255.0
    # Multiply the foreground with the alpha matte
    foreground = cv2.multiply(alpha, foreground)
    # Multiply the background with ( 1 - alpha )
    background = cv2.multiply(1.0 - alpha, background)
    # Add the masked foreground and background.
    cutout = cv2.add(foreground, background)

    cv2.imwrite(data[:-4] + '_contour.png', cutout)
    cutout = cv2.imread(data[:-4] + '_contour.png')

    used_platform = platform.system()

    if used_platform == "Linux":
        os.system("rm " + data[:-4] + '_contour.png')
    else:
        os.system("del " + data[:-4] + '_contour.png')

    # cutout = cv2.imread(source, 1)  # TEMPORARY

    cutout_blurred = cv2.GaussianBlur(cutout, (5, 5), 0)

    gray = cv2.cvtColor(cutout_blurred, cv2.COLOR_BGR2GRAY)
    # threshed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                                  cv2.THRESH_BINARY_INV, blockSize=501,C=2)

    # front and back light
    # lower_gray = np.array([175, 175, 175])  # [R value, G value, B value]
    # upper_gray = np.array([215, 215, 215])
    # front light only
    lower_gray = np.array([min_rgb, min_rgb, min_rgb])  # [R value, G value, B value]
    upper_gray = np.array([max_rgb, max_rgb, max_rgb])

    mask = cv2.bitwise_not(cv2.inRange(cutout_blurred, lower_gray, upper_gray) + cv2.inRange(gray, 254, 255))

    # binarise
    ret, image_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY_INV)
    image_bin[image_bin < 127] = 0
    image_bin[image_bin > 127] = 1

    #cv2.imwrite(data[:-4] + '_threshed.png', 1 - image_bin, [cv2.IMWRITE_PNG_BILEVEL, 1])

    print("cleaning up thresholding result, using connected component labelling of %s"
          % (data.split("\\")[-1]))

    # remove black artifacts
    blobs_labels = measure.label(cv2.GaussianBlur(image_bin, (5, 5), 0), background=0)

    image_cleaned = remove_holes(blobs_labels, min_num_pixel=min_bl)

    image_cleaned_inv = 1 - image_cleaned

    # cv2.imwrite(data[:-4] + "_extracted_black_.png", image_cleaned_inv, [cv2.IMWRITE_PNG_BILEVEL, 1])

    # remove white artifacts
    blobs_labels_white = measure.label(image_cleaned_inv, background=0)

    image_cleaned_white = remove_holes(blobs_labels_white, min_num_pixel=min_wh)

    cv2.imwrite(data[:-4] + "_masked.png", image_cleaned_white, [cv2.IMWRITE_PNG_BILEVEL, 1])

    if create_cutout:
        image_cleaned_white = cv2.imread(data[:-4] + "_masked.png")
        cutout = cv2.imread(data)
        # create the image with an alpha channel
        # smooth masks prevent sharp features along the outlines from being falsely matched
        """
        smooth_mask = cv2.GaussianBlur(image_cleaned_white, (11, 11), 0)
        rgba = cv2.cvtColor(cutout, cv2.COLOR_RGB2RGBA)
        # assign the mask to the last channel of the image
        rgba[:, :, 3] = smooth_mask
        # save as lossless png
        cv2.imwrite(data[:-4] + '_cutout.tif', rgba)
        """

        _, mask = cv2.threshold(cv2.cvtColor(image_cleaned_white, cv2.COLOR_BGR2GRAY), 240, 255, cv2.THRESH_BINARY)
        print(cutout.shape)
        img_jpg = cv2.bitwise_not(cv2.bitwise_not(cutout[:, :, :3], mask=mask))

        print(img_jpg.shape)
        img_jpg[np.where((img_jpg == [255, 255, 255]).all(axis=2))] = [0, 0, 0]
        cv2.imwrite(data[:-4] + '_cutout.jpg', img_jpg)



def mask_images(input_paths, min_rgb, max_rgb, min_bl, min_wh, create_cutout=False):
    # load pre-trained edge detector model
    edgeDetector = cv2.ximgproc.createStructuredEdgeDetection(str(Path.cwd().joinpath("scripts", "model.yml")))
    print("loaded edge detector...")

    for img in input_paths:
        createAlphaMask(img, edgeDetector, min_rgb, max_rgb, min_bl, min_wh, create_cutout)
