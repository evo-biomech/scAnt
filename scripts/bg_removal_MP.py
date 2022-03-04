import numpy as np
import cv2
import os
from PIL import Image, ImageEnhance
import queue
import threading
import time
import sys
from imutils import paths
from skimage import measure

import platform

used_platform = platform.system()


class AlphaExtractionThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        createAlphaMask(self.name, self.q, edgeDetector=edgeDetector, create_cutout=True)
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
    blurred_gray = cv2.GaussianBlur(gray, (3, 3), 0)

    clahe = cv2.createCLAHE(clipLimit=4.2, tileGridSize=grid_size)
    cl1 = clahe.apply(blurred_gray)

    # convert to PIL format to apply laplacian sharpening
    img_pil = Image.fromarray(cl1)

    enhancer = ImageEnhance.Sharpness(img_pil)
    sharpened = enhancer.enhance(25)

    # sharpened.save(source + "\\enhanced.png")

    return cv2.cvtColor(np.array(sharpened), cv2.COLOR_GRAY2RGB)


def createAlphaMask(threadName, q, edgeDetector, create_cutout=False):
    """
    create alpha mask for the image located in path
    :param source: image location
    :return: writes image to same location as input
    """
    while not exitFlag_alpha:
        queueLock_alpha.acquire()
        if not workQueue_alpha.empty():
            data = q.get()
            queueLock_alpha.release()
            print("%s : extracting alpha of %s" % (threadName, data.split("\\")[-1]))

            src = cv2.imread(data, 1)

            img_enhanced = apply_local_contrast(src)

            # reduce noise in the image before detecting edges
            blurred = cv2.GaussianBlur(img_enhanced, (5, 5), 0)

            # turn image into float array
            blurred_float = blurred.astype(np.float32) / 255.0
            edges = edgeDetector.detectEdges(blurred_float) * 255.0

            # required as the contour finding step is susceptible to noise
            print("%s : Filtering out salt & pepper grain of %s" % (threadName, data.split("\\")[-1]))
            edges_8u = np.asarray(edges, np.uint8)
            filterOutSaltPepperNoise(edges_8u)

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

            # run grabcut
            print("%s : Creating mask from contour of %s" % (threadName, data.split("\\")[-1]))
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

            if used_platform == "Linux":
                os.system("rm " + data[:-4] + '_contour.png')
            else:
                os.system("del " + data[:-4] + '_contour.png')

            # cutout = cv2.imread(source, 1)  # TEMPORARY

            print("%s : adaptive thresholding to remove elements included in the contour of %s"
                  % (threadName, data.split("\\")[-1]))
            cutout_blurred = cv2.GaussianBlur(cutout, (7, 7), 0)

            gray = cv2.cvtColor(cutout_blurred, cv2.COLOR_BGR2GRAY)
            # threshed = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            #                                  cv2.THRESH_BINARY_INV, blockSize=501,C=2)

            # front and back light
            # lower_gray = np.array([175, 175, 175])  # [R value, G value, B value]
            # upper_gray = np.array([215, 215, 215])
            # front light only
            lower_gray = np.array([108, 108, 108])  # [R value, G value, B value]
            upper_gray = np.array([144, 144, 144])

            mask = cv2.bitwise_not(cv2.inRange(cutout_blurred, lower_gray, upper_gray) + cv2.inRange(gray, 254, 255))

            # binarise
            ret, image_bin = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY_INV)
            image_bin[image_bin < 127] = 0
            image_bin[image_bin > 127] = 1

            # cv2.imwrite(data[:-4] + '_threshed.png', 1 - image_bin, [cv2.IMWRITE_PNG_BILEVEL, 1])

            print("%s : cleaning up thresholding result, using connected component labelling of %s"
                  % (threadName, data.split("\\")[-1]))

            # remove black artifacts
            blobs_labels = measure.label(cv2.GaussianBlur(image_bin, (5, 5), 0), background=0)

            # retain holes bigger than X pixels
            image_cleaned = remove_holes(blobs_labels, min_num_pixel=500)

            image_cleaned_inv = 1 - image_cleaned

            # cv2.imwrite(data[:-4] + "_extracted_black_.png", image_cleaned_inv, [cv2.IMWRITE_PNG_BILEVEL, 1])

            # remove white artifacts
            blobs_labels_white = measure.label(image_cleaned_inv, background=0)

            # retain added patches, bigger than Y pixels
            image_cleaned_white = remove_holes(blobs_labels_white, min_num_pixel=500)

            cv2.imwrite(data[:-4] + "_masked.png", image_cleaned_white, [cv2.IMWRITE_PNG_BILEVEL, 1])

            if create_cutout:
                image_cleaned_white = cv2.imread(data[:-4] + "_masked.png", cv2.IMREAD_GRAYSCALE)
                cutout = cv2.imread(data)
                # create the image with an alpha channel
                # smooth masks prevent sharp features along the outlines from being falsely matched
                smooth_mask = cv2.GaussianBlur(image_cleaned_white, (5, 5), 0)
                rgba = cv2.cvtColor(cutout, cv2.COLOR_RGB2RGBA)

                # assign the mask to the last channel of the image
                rgba[:, :, 3] = smooth_mask
                # save as lossless png
                cv2.imwrite(data[:-4] + '_cutout.tif', rgba)
        else:
            queueLock_alpha.release()


if __name__ == '__main__':
    # pip install opencv-contrib-python==3.4.5.20
    start = time.time()
    source = "C:\\Users\\Legos\\Desktop\\3D_scans\\leptoglossus_phyloppus\\stacked"

    print("Using images from", source)

    # load pre-trained edge detector model
    edgeDetector = cv2.ximgproc.createStructuredEdgeDetection("model.yml")
    print("loaded edge detector...")

    # setup half as many threads as there are (virtual) CPUs
    exitFlag_alpha = 0
    num_virtual_cores = getThreads()
    threadList = createThreadList(int(num_virtual_cores / 2))
    print("Found", num_virtual_cores, "(virtual) cores...")
    queueLock_alpha = threading.Lock()

    # define paths to all images and set the maximum number of items in the queue equivalent to the number of images
    file_type = "tif"
    all_image_paths = []
    for imagePath in sorted(paths.list_images(source)):
        # create an alpha mask for all TIF images in the source folder
        if imagePath[-3::] == file_type:
            all_image_paths.append(imagePath)
            print("added", imagePath, "to queue")

    workQueue_alpha = queue.Queue(len(all_image_paths))

    # Create new threads
    threads = []
    threadID = 1
    for tName in threadList:
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
    print("All images processed!\nExiting Main Thread")
    print("Time elapsed:", time.time() - start)
