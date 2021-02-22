import cv2
import numpy as np

"""
Script used to compare the masking quality of various methods against a hand annotated "ground truth" binary mask.
The accuracy is defined as (total_px - (FP + FN)) / total_px
* total_px = sum of image pixels
* TN = True Negative (pixels correctly labeled as background)
* FN = False Negative (pixels incorrectly labeled as background)
"""


def binarise(img):
    ret, img_bin = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
    img_bin[img_bin < 127] = 0
    img_bin[img_bin > 127] = 1

    return img_bin


def calculate_masking_accuracy(ground_truth, generated_mask):
    gt = cv2.imread(ground_truth, cv2.IMREAD_GRAYSCALE)
    gm = cv2.imread(generated_mask, cv2.IMREAD_GRAYSCALE)

    print("INFO:  Imported images...")

    # binarise image
    gt_bin = binarise(gt)
    gm_bin = binarise(gm)

    # use type .int16 to avoid overflow when subtracting arrays
    diff = gt_bin.astype(np.int16) - gm_bin.astype(np.int16)
    FP_FN = np.sum(np.abs(diff))

    total_px = gt.shape[0] * gt.shape[1]

    print("INFO:  Total number of pixels:", total_px)
    print("INFO:  Number of incorrect pixels:", FP_FN)

    accuracy = (total_px - FP_FN) / total_px

    return accuracy


if __name__ == '__main__':
    ground_truth_file_loc = "I:\\3D_Scanner\\Manuscript\\Revision\\masking_comparison\\masking_comp\\ground_truth_mask.png"
    generated_mask_file_loc = "I:\\3D_Scanner\\Manuscript\\Revision\\masking_comparison\\masking_comp\\random_forest_masked.png"

    accuracy = calculate_masking_accuracy(ground_truth=ground_truth_file_loc, generated_mask=generated_mask_file_loc)
    print("\nINFO:  Masking accuracy:", accuracy)
