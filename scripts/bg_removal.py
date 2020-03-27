import numpy as np
import cv2
import os
from imutils import paths


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
    image, contours, hierarchy = cv2.findContours(
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


def createAlphaMask(source, create_cutout=False):
    """
    create alpha mask for the image located in path
    :param source: image location
    :return: writes image to same location as input
    """

    src = cv2.imread(source, 1)
    # reduce noise in the image before detecting edges
    blurred = cv2.GaussianBlur(src, (5, 5), 0)

    # turn image into float array
    blurred_float = blurred.astype(np.float32) / 255.0
    # load pre-trained edge detector model
    edgeDetector = cv2.ximgproc.createStructuredEdgeDetection("model.yml")
    edges = edgeDetector.detectEdges(blurred_float) * 255.0

    # required as the contour finding step is susceptible to noise
    edges_8u = np.asarray(edges, np.uint8)
    filterOutSaltPepperNoise(edges_8u)

    contour = findSignificantContour(edges_8u)
    # Draw the contour on the original image
    contourImg = np.copy(src)
    cv2.drawContours(contourImg, [contour], 0, (0, 255, 0), 2, cv2.LINE_AA, maxLevel=1)

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
    # cv2.imwrite('trimap.png', trimap_print)

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

    cv2.imwrite(source[:-4] + '_cutout.jpg', cutout)
    cutout = cv2.imread(source[:-4] + '_cutout.jpg')
    os.system("del " + source[:-4] + '_cutout.jpg')

    gray = cv2.cvtColor(cutout, cv2.COLOR_BGR2GRAY)
    th, threshed = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

    threshed = cv2.GaussianBlur(threshed, (5, 5), 0)

    cv2.imwrite(source[:-4] + '_alpha.jpg', threshed)

    if create_cutout:
        # create the image with an alpha channel
        rgba = cv2.cvtColor(cutout, cv2.COLOR_RGB2RGBA)

        # assign the mask to the last channel of the image
        rgba[:, :, 3] = threshed
        cv2.imwrite(source[:-4] + '_cutout.png', rgba)


if __name__ == '__main__':
    # pip install opencv-contrib-python==3.4.5.20
    source ='I:\\3D_Scanner\\images\\Leaffooted_scanner_single_stack_stacked' #'I:\\3D_Scanner\\images'

    for imagePath in sorted(paths.list_images(source)):
        # create an alpha mask for all TIF images in the source folder
        if imagePath[-3::] == "tif":
            createAlphaMask(imagePath)
    exit()
