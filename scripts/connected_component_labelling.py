import numpy as np
import cv2
from skimage import measure
from skimage import filters
import matplotlib.pyplot as plt


def connected_component_labelling(img):
    """
    connected component labelling is used to find all sub_regions of an image
    :img: np array of binary input image
    :return: np array, size of img, with no_object = 0, and labels of sub_regions in ascending order
    """
    label = 1
    root_list = []

    labelled_img = img.copy()

    for row in range(labelled_img.shape[0]):
        # print("Row", row, "out of", labelled_img.shape[0])
        for column in range(labelled_img.shape[1]):
            pixel = labelled_img[row, column]
            # print("Column", column, "out of", labelled_img.shape[1], "with the value", pixel)
            if pixel != 0:
                # if A or B lie out of bounds the pixel is assigned
                # max operation used to avoid return of "NoneType" when out of bounds
                A = max(labelled_img[row - 1, column], 0)
                B = max(labelled_img[row, column - 1], 0)
                # print("A is", A)
                # print("B is", B)
                if A != 0 or B != 0:
                    # set the label of the pixel to the lower one of A or B if they are not zero
                    pixel_label = min(max(A, 1), max(B, 1))
                    # print("pixel_label set to", pixel_label)
                    if A != 0 and B != 0 and A != B:
                        # Now if p connects A and B but they have different labels that implies that they are in fact
                        # part of the same object so the higher value label is set as a child of the lower value label
                        relationship = [A, B]
                        relationship.sort()
                        # print(relationship[0], "is the parent of", relationship[1])
                        root_found = False

                        # if the root_list is not empty, check relationship, else simply add it
                        if len(root_list) != 0:
                            for r in range(len(root_list)):
                                if relationship[0] in root_list[r][1:]:  # if the parent is the child of any other label
                                    root_found = True
                                    print(relationship[0], "is the child of", root_list[r][0])
                                    if relationship[1] not in root_list[r][1:]:
                                        # add child to the root of the parent only if it is not yet part of the root_list
                                        root_list[r].append(relationship[1])
                                    break
                                if relationship[0] == root_list[r][0]:  # if the parent is a root
                                    root_found = True
                                    if relationship[1] not in root_list[r][1:]:
                                        # add child to the root of the parent only if it is not yet part of the root_list
                                        root_list[r].append(relationship[1])
                                    break
                            """
                            if not root_found:  # search if the parent is already a root
                                for r in range(len(root_list)):
                                    if relationship[0] == root_list[r][
                                        0]:  # if the parent is the child of any other label
                                        root_found = True
                                        if relationship[1] not in root_list[r][1:]:
                                            # add child to the root of the parent only if it is not yet part of the root_list
                                            root_list[r].append(relationship[1])
                                        break
                            """
                            if not root_found:
                                print("new root found:", relationship)
                                root_list.append(relationship)
                        else:
                            root_list.append(relationship)

                else:
                    pixel_label = label
                    label += 1

                labelled_img[row, column] = pixel_label

    print("Areas found:", len(root_list), "\nmerging areas...")
    root_list.sort(key=len)

    final_label = 1
    final_img = np.zeros(shape=(img.shape[0], img.shape[1]))

    for root in root_list:
        print(root)
        print(len(root))
        for child in range(len(root) - 1):
            final_img[labelled_img.astype(int) == root[child + 1]] = final_label
        final_label += 1

    return final_img, len(root_list)


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


if __name__ == '__main__':
    source = 'J:\\data\\leaffooted_stacked\\y_00200_z_00240__alpha.jpg'  # "J:\\test_bit.png"  #

    # import image of raw alpha
    image = cv2.imread(source, cv2.IMREAD_GRAYSCALE)
    # binarise image
    ret, image_bin = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY_INV)
    image_bin[image_bin < 127] = 0
    image_bin[image_bin > 127] = 1

    """
    open cv solution (NOT IDEAL)
    https://stackoverflow.com/questions/10262600/how-to-detect-region-of-large-of-white-pixels-using-opencv
    extract contour
    https://stackoverflow.com/questions/19222343/filling-contours-with-opencv-python
    fill contours
    
    ALSO, have a look at
    http://scipy-lectures.org/packages/scikit-image/auto_examples/plot_labels.html !!!
    """

    blobs_labels = measure.label(image_bin, background=0)

    image_cleaned = remove_holes(blobs_labels, min_num_pixel=500)

    image_cleaned_inv = 1 - image_cleaned

    cv2.imwrite(source[:-4] + "_extracted_.png", image_cleaned_inv, [cv2.IMWRITE_PNG_BILEVEL, 1])

    """

    ret, image_bin = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY_INV)
    image_bin[image_bin < 127] = 0
    image_bin[image_bin > 127] = 1

    cv2.imwrite(source[:-4] + "_bin_.png", image_bin, [cv2.IMWRITE_PNG_BILEVEL, 1])

    image_labeled, num_labels = connected_component_labelling(image_bin.astype(int))

    image_cleaned = remove_holes(image_labeled, min_num_pixel=50)

    # cv2.imshow("output labels", image_labeled * (255 / num_labels))
    # cv2.waitKey(0)
    cv2.imwrite(source[:-4] + "_labeled_.png", image_cleaned, [cv2.IMWRITE_PNG_BILEVEL, 1])
    """

    exit()
