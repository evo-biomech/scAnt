# image processing utilities to create stacked / blended / masked images while scanning


import cv2
import os

from PIL import Image, ImageEnhance
from skimage import measure
from imutils import paths
import sys
import numpy as np
from pathlib import Path
import platform
import argparse
import queue
import threading
import time

class FocusCheckingThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        process_data(self.name, self.q)
        print("Exiting " + self.name)


class StackingThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        process_stack_threaded(self.name, self.q)
        print("Exiting " + self.name)

def process_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            data = q.get()
            queueLock.release()
            print("%s processing %s" % (threadName, data))
            checkFocus_threaded(images.joinpath(data))
        else:
            queueLock.release()

class AlphaExtractionThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        createAlphaMask_threaded(self.name, self.q, edgeDetector=edgeDetector)
        print("Exiting " + self.name)

def getThreads():
    """ Returns the number of available threads on a posix/win based system """
    if sys.platform == 'win32':
        return int(os.environ['NUMBER_OF_PROCESSORS'])
    else:
        return int(os.popen('grep -c cores /proc/cpuinfo').read())


def createThreadList(num_threads):
    threadNames = []
    for t in range(num_threads):
        threadNames.append("Thread_" + str(t))

    return threadNames

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

def checkFocus_threaded(image_path):
    checkFocus(image_path, focus_threshold, usable_images, rejected_images)

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

def process_stack_threaded(name, q):
    while not exitFlag_stacking:
        queueLock.acquire()
        if not workQueue_stacking.empty():
            data = q.get()
            queueLock.release()

            process_stack(data, output_folder, path_to_external, args)
        else:
            queueLock.release()

def process_stack(data, output_folder, path_to_external, params):
    stack_name = data.split(" ")[1]
    stack_name = Path(stack_name).name[:-15]

    temp_output_folder = output_folder.joinpath(stack_name)

    used_platform = platform.system()

    output_path = str(output_folder.joinpath(stack_name)) + ".tif"
    print(output_path)

    # stack_params = ""
    # if params["nocrop"]:
    #     stack_params += " --nocrop"
    # if params["full_resolution_align"]:
    #     stack_params += " --full-resolution-align"
    # if params["jpgquality"]:
    #     stack_params += " --jpgquality=" + params["jpgquality"]
    

    if used_platform != "Linux" and params["use_experimental_stacking"]:
        os.system(
            str(path_to_external) + "\\focus-stack\\focus-stack " +
            data + " --output=" + output_path
        )
    else:
        if used_platform == "Linux":
            os.system("align_image_stack -m -x -c 200 -a " + str(
                temp_output_folder.joinpath(stack_name))
                      + "OUT" + data)
        else:
            # use additional external files under windows to execute alignment via hugin
            os.system(str(path_to_external) + "\\align_image_stack -m -x -c 200 -a " + str(
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

        for temp_img in temp_files:
            if used_platform == "Linux":
                os.system("rm " + str(temp_img))
            else:
                os.system("del " + str(temp_img))

        print("Deleted temporary files of stack", data)

    if params["sharpen"]:
        stacked = Image.open(output_path)
        enhancer = ImageEnhance.Sharpness(stacked)
        sharpened = enhancer.enhance(1.5)
        sharpened.save(output_path)

        print("Sharpened", output_path)


    return output_path


def stack_images(input_paths, check_focus, threshold=10.0, sharpen=False):
    images = Path(input_paths[0]).parent

    all_image_paths = []
    for img_path in input_paths:
        all_image_paths.append(Path(img_path))

    usable_images = []
    rejected_images = []

    for path in all_image_paths:
        if check_focus:
            usable_images, rejected_images = checkFocus(path, threshold, usable_images, rejected_images)
        else:
            usable_images.append(path.name)

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

    parameters = {"sharpen": False,
                  "use_experimental_stacking": True}

    for stack in stacks:
        stacked_images_paths.append(
            process_stack(data=stack, output_folder=output_folder, path_to_external=path_to_external, params=parameters))

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


def apply_local_contrast(img, grid_size=(7, 7), clip_limit=1.0):
    """
    ### CLAHE (Contrast limited Adaptive Histogram Equilisation) ###

    Advanced application of local contrast. Adaptive histogram equalization is used to locally increase the contrast,
    rather than globally, so bright areas are not pushed into over exposed areas of the histogram. The image is tiled
    into a fixed size grid. Noise needs to be removed prior to this process, as it would be greatly amplified otherwise.
    Similar to Adobe's "Clarity" option which also amplifies local contrast and thus pronounces edges, reduces haze.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred_gray = cv2.GaussianBlur(gray, (5, 5), 0)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=grid_size)
    cl1 = clahe.apply(blurred_gray)

    # convert to PIL format to apply laplacian sharpening
    img_pil = Image.fromarray(cl1)

    enhancer = ImageEnhance.Sharpness(img_pil)
    sharpened = enhancer.enhance(31)

    return cv2.cvtColor(np.array(sharpened), cv2.COLOR_GRAY2RGB)

def createAlphaMask_threaded(threadName, q, edgeDetector):
    while not exitFlag_alpha:
        queueLock_alpha.acquire()
        if not workQueue_alpha.empty():
            data = q.get()
            queueLock_alpha.release()
            print("%s : extracting alpha of %s" % (threadName, data.split("\\")[-1]))

            createAlphaMask(data, edgeDetector, threadName=threadName, params=args)

        else:
            queueLock_alpha.release()


def createAlphaMask(data, edgeDetector, threadName=None, params = {
    "create_cutout":True,
    "full_resolution":False,
    "mask_thresh_min": 80,
    "mask_thresh_max": 100,
    "min_artifact_size_black": 1000,
    "min_artifact_size_white": 2000,
    "CLAHE":1.0
}):
    """
    create alpha mask for the image located in path
    :img_path: image location
    :create_cutout: additionally save final image with as the stacked image with the mask as an alpha layer
    :return: writes image to same location as input
    """
    src = cv2.imread(data, 1)

    if not params["full_resolution"]:
        print("Using downscaled image for mask generation at 1500 px x 1500 px...")
        orig_res = src.shape
        kernel_gauss = (5, 5)
        print("Original resolution:", orig_res)
        src = cv2.resize(src, (1500, 1500), interpolation=cv2.INTER_AREA)
    else:
        print("Using full resolution input image for mask generation [potentially significantly slower]")
        orig_res = src.shape
        kernel_gauss = (5, 5)
        print("Original resolution:", orig_res)

    img_enhanced = apply_local_contrast(src, clip_limit=params["CLAHE"])

    # reduce noise in the image before detecting edges
    blurred = cv2.GaussianBlur(img_enhanced, kernel_gauss, 0)

    # turn image into float array
    blurred_float = blurred.astype(np.float32) / 255.0
    edges = edgeDetector.detectEdges(blurred_float) * 255.0
    if threadName:
        print("%s : Filtering out salt & pepper grain of %s" % (threadName, data.split("\\")[-1]))
    edges_8u = np.asarray(edges, np.uint8)
    filterOutSaltPepperNoise(edges_8u)

    if threadName:
        print("%s : Extracting largest coherent contour of %s" % (threadName, data.split("\\")[-1]))
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

    if threadName:
        print("%s : Creating mask from contour of %s" % (threadName, data.split("\\")[-1]))
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
    min_rgb = float(params["mask_thresh_min"])
    max_rgb = float(params["mask_thresh_max"])
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

    image_cleaned = remove_holes(blobs_labels, min_num_pixel=params["min_artifact_size_black"])

    image_cleaned_inv = 1 - image_cleaned

    # cv2.imwrite(data[:-4] + "_extracted_black_.png", image_cleaned_inv, [cv2.IMWRITE_PNG_BILEVEL, 1])

    # remove white artifacts
    blobs_labels_white = measure.label(image_cleaned_inv, background=0)

    image_cleaned_white = remove_holes(blobs_labels_white, min_num_pixel=params["min_artifact_size_white"])

    if not params["full_resolution"]:
        # up-scaling masks to original resolution
        image_cleaned_white = cv2.resize(image_cleaned_white,
                                            (orig_res[1], orig_res[0]),
                                            interpolation=cv2.INTER_AREA)

    cv2.imwrite(data[:-4] + "_masked.png", image_cleaned_white, [cv2.IMWRITE_PNG_BILEVEL, 1])

    if params["create_cutout"]:
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



def mask_images(input_paths, min_rgb, max_rgb, min_bl, min_wh, create_cutout):
    # load pre-trained edge detector model
    edgeDetector = cv2.ximgproc.createStructuredEdgeDetection(str(Path.cwd().joinpath("scripts", "model.yml")))
    print("loaded edge detector...")

    params = {"create_cutout": create_cutout,
              "mask_thresh_min": min_rgb,
              "mask_thresh_max": max_rgb,
              "min_artifact_size_black": min_bl,
              "min_artifact_size_white": min_wh,
              "full_resolution":False,
              "CLAHE": 1.0}

    for img in input_paths:
        createAlphaMask(img, edgeDetector, params=params)

if __name__ == "__main__":

    start = time.time()

    from scripts.write_meta_data import write_exif_to_img
    import scripts.project_manager as ymlRW

    # edgeDetector = cv2.ximgproc.createStructuredEdgeDetection(Path("scripts").joinpath("model.yml"))

    #TODO Add threading
    
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--path", required=True, help="Path to scAnt project")
    ap.add_argument("-s", "--stacking", default=True, help="stack RAW images [True / False] (True by default)")
    ap.add_argument("-m", "--masking", default=True, help="mask stacked images [True / False] (True by default)")
    ap.add_argument("-f", "--focus_check", default=False,
                    help="check whether out-of-focus images should be discarded before stacking [True / False] (False by default)")
    ap.add_argument("-t", "--threshold", type=float,
                    help="focus measures that fall below this value will be considered 'blurry'")
    ap.add_argument("-sh","--sharpen", default=False, help="help=apply sharpening to final result [True / False] (False by default)")
    ap.add_argument("-c", "--create_cutout", default=False, 
                    help="create aditional cutout image that uses generated mask")
    ap.add_argument("-min", "--mask_thresh_min", type=float,
                    help="minimum RGB value of background for exclusion")
    ap.add_argument("-max", "--mask_thresh_max", type=float,
                    help="maximum RGB value of background for exclusion")
    ap.add_argument("-meta", "--addmetadata", default=True, help="add camera metadata to images in stacked folder [True/ Fasle]")
    ap.add_argument("-fr", "--full_resolution", type=bool, default=False,
                    help="enable to run masking on the full resolution image. By default all images are downscaled " +
                         "to 1024 x 1024 and the generated masks are up-scaled to the original image resolution.")
    ap.add_argument("-cl", "--CLAHE", type=float, default=1.0,
                    help="set the clip-limit for Contrast Limited Adaptive Histogram Equilisation")
    ap.add_argument("-nc", "--nocrop", type=bool, default=False, help="save full image, including extapolated border data (False by default)")
    ap.add_argument("-ex", "--use_experimental_stacking", type=bool, default=True, help="Use new stacking method")
    ap.add_argument("-fr_align", "--full_resolution_align", type=bool, default=False, help="Use full resolution images in alignment (default max 2048 px)")
    ap.add_argument("-jpg", "--jpgquality", help="Quality for saving in JPG format (0-100, default 95)")

    args = vars(ap.parse_args())
    project_dir = Path(args["path"])
    stacked_dir = Path(project_dir.joinpath("stacked")) 
    images = Path(project_dir.joinpath("RAW"))


    #check if config in project dir
    config_present = False
    for file in os.listdir(project_dir):
        if file.endswith(".yaml"):
            config_present = True
            config_file = file
    

    if config_present:
        config_location = project_dir.joinpath(config_file)

        config = ymlRW.read_config_file(config_location)

        #Read important post processing parameters - if not defined from cmd
        if args["threshold"] is not None:
            focus_threshold = float(args["threshold"])
        else:
            focus_threshold = float(config["stacking"]["threshold"])

        #parse boolean args
        if str(args["stacking"]).lower() == "false" or not args["stacking"]:
            stack_check=False
        else:
            stack_check=True
        if str(args["masking"]).lower() == "false" or not args["masking"]:
            mask_check=False
        else:
            mask_check=True
        if str(args["focus_check"]).lower() == "false" or not args["focus_check"]:
            focus_check=False
        else:
            focus_check=True
        if str(args["addmetadata"]).lower() == "false" or not args["addmetadata"]:
            metadata_check = False
        else:
            metadata_check = True
        # if str(args["create_cutout"]).lower() == "true" or args["create_cutout"]:
        #     cutout_check=True
        # else:
        #     cutout_check=False
        # if str(args["sharpen"]).lower() == "true" or args["sharpen"]:
        #     sharpen = True
        # elif str(args["sharpen"]).lower() == "false" or not args["sharpen"]:
        #     sharpen = False
        # else:
        #     sharpen = config["stacking"]["additional_sharpening"]

        # stack_method = config["stacking"]["stacking_method"]
        exif = config["exif_data"]
        
        if args["mask_thresh_min"]:
            pass
        else:
            args["mask_thresh_min"] = config["masking"]["mask_thresh_min"]
        if args["mask_thresh_max"]:
            pass
        else:
            args["mask_thresh_max"] = config["masking"]["mask_thresh_max"]

        args["min_artifact_size_black"] = config["masking"]["min_artifact_size_black"]
        args["min_artifact_size_white"] = config["masking"]["min_artifact_size_white"]

        if stack_check:

            all_image_paths = os.listdir(images)

            # setup as many threads as there are (virtual) CPUs
            exitFlag = 0
            num_virtual_cores = getThreads()
            threadList = createThreadList(num_virtual_cores)
            print("Found", num_virtual_cores, "(virtual) cores...")
            queueLock = threading.Lock()

            workQueue = queue.Queue(len(all_image_paths))
            threads = []
            threadID = 1

            # create list of image paths classified as in-focus or blurry
            usable_images = []
            rejected_images = []

            """
            ### extracting "in-focus" images for further processing ###
            """

            if focus_check:
                
                # Create new threads
                for tName in threadList:
                    thread = FocusCheckingThread(threadID, tName, workQueue)
                    thread.start()
                    threads.append(thread)
                    threadID += 1

                cv2.ocl.setUseOpenCL(True)

                # Fill the queue
                queueLock.acquire()
                for path in all_image_paths:
                    workQueue.put(path)
                queueLock.release()

                # Wait for queue to empty
                while not workQueue.empty():
                    pass

                # Notify threads it's time to exit
                exitFlag = 1

                # Wait for all threads to complete
                for t in threads:
                    t.join()
                print("Exiting Main Thread")

                cv2.destroyAllWindows()
            else:
                # if blurry images have been discarded already add all paths to "usable_images"
                for image_path in all_image_paths:
                    usable_images.append(image_path)

            # as threads may terminate at different times the file list needs to be sorted
            usable_images.sort()

            if len(usable_images) > 1:
                print("\nThe following images are sharp enough for focus stacking:\n")
                for path in usable_images:
                    print(path)
            else:
                print("No images suitable for focus stacking found!")
                exit()

            # as the script can be executed from the parent or "scripts" directory check where the external files are located
            path_to_external = Path.cwd().joinpath("external")
            print(path_to_external)
            if not os.path.exists(path_to_external):
                path_to_external = Path.cwd().parent.joinpath("external")

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

                """
                # only needed when using hugin-enfuse
                
                if not os.path.exists(output_folder.joinpath(current_stack_name)):
                    os.makedirs(output_folder.joinpath(current_stack_name))
                    print("made corresponding temporary folder!")
                else:
                    print("corresponding temporary folder already exists!")
                """

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

            # setup as many threads as there are (virtual) CPUs
            exitFlag_stacking = 0
            # only use a fourth of the number of CPUs for stacking as hugin and enfuse utilise multi core processing in part
            threadList_stacking = createThreadList(int(min([num_virtual_cores / 4, 3])))
            print("Using", len(threadList_stacking), "threads for stacking...")
            queueLock = threading.Lock()

            # define paths to all images and set the maximum number of items in the queue equivalent to the number of images
            workQueue_stacking = queue.Queue(len(stacks))
            threads = []
            threadID = 1

            # Create new threads
            for tName in threadList_stacking:
                thread = StackingThread(threadID, tName, workQueue_stacking)
                thread.start()
                threads.append(thread)
                threadID += 1

            # Fill the queue with stacks
            queueLock.acquire()
            for stack in stacks:
                workQueue_stacking.put(stack)
            queueLock.release()

            # Wait for queue to empty
            while not workQueue_stacking.empty():
                pass

            # Notify threads it's time to exit
            exitFlag_stacking = 1

            # Wait for all threads to complete
            for t in threads:
                t.join()
            print("Exiting Main Stacking Thread")

            """
            # only needed with hugin-enfuse, so disabled for new experimental stacking
            print("Deleting temporary folders")

            for stack in stacks:
                stack_name = stack.split(" ")[1]
                stack_name = Path(stack_name).name[:-15]
                os.rmdir(output_folder.joinpath(stack_name))
                print("removed  ...", stack_name)
            
            """

            print("Stacking finalised!")
            print("Time elapsed:", time.time() - start)

        if mask_check:

            print("Using images from", stacked_dir)
            # define paths to all images and set the maximum number of items in the queue equivalent to the number of images
            file_type = "tif"
            all_image_paths = []
            for imagePath in sorted(paths.list_images(stacked_dir)):
                # create an alpha mask for all TIF images in the source folder
                if imagePath[-3::] == file_type:
                    all_image_paths.append(imagePath)
                    print("added", imagePath, "to queue")

            # load pre-trained edge detector model
            edgeDetector = cv2.ximgproc.createStructuredEdgeDetection(str(Path("scripts").joinpath("model.yml")))
            print("loaded edge detector...")

            # setup half as many threads as there are (virtual) CPUs
            exitFlag_alpha = 0
            num_virtual_cores = getThreads()
            threadList_alpha = createThreadList(int(num_virtual_cores/4))
            print("Found", num_virtual_cores, "(virtual) cores...")
            queueLock_alpha = threading.Lock()

            workQueue_alpha = queue.Queue(len(all_image_paths))

            # Create new threads
            threads = []
            threadID = 1
            for tName in threadList_alpha:
                thread = AlphaExtractionThread(threadID, tName, workQueue_alpha)
                thread.start()
                threads.append(thread)
                threadID += 1

            # Fill the queue
            queueLock_alpha.acquire()
            for path in all_image_paths:
                workQueue_alpha.put(path)
            queueLock_alpha.release()

            # Wait for queue to empty
            while not workQueue_alpha.empty():
                pass

            # Notify threads it's time to exit
            exitFlag_alpha = 1

            # Wait for all threads to complete
            for t in threads:
                t.join()

            print("Masking Done")

        if metadata_check:

            for img in os.listdir(str(stacked_dir)):
                print(img)
                if img[-4:] == ".tif" or img[-4:] == ".jpg":
                    img_tif = cv2.imread(str(stacked_dir.joinpath(img)), cv2.IMREAD_UNCHANGED)

                    cv2.imwrite(str(stacked_dir.joinpath(img)), img_tif)
                    write_exif_to_img(img_path=str(stacked_dir.joinpath(img)), custom_exif_dict=exif)
        print("All images processed!\nExiting Main Thread")
        exit()
        

                        
    else:
        print("No config file found in folder!")
