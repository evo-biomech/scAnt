import cv2

"""
Alternative masking method, based on backlight images, as described by Stroebel et al. 2018
"""


def generate_backlight_mask(orig_file_loc, backlit_file_loc, threshold=250):
    orig = cv2.imread(orig_file_loc)
    backlit = cv2.imread(backlit_file_loc, cv2.IMREAD_GRAYSCALE)

    print("INFO:  Imported images...")

    # binarise
    ret, image_bin = cv2.threshold(backlit, threshold, 255, cv2.THRESH_BINARY)
    image_bin[image_bin < 127] = 0
    image_bin[image_bin > 127] = 1

    mask_name = orig_file_loc[:-4] + '_backlight_masked.png'

    # save as binary png
    cv2.imwrite(mask_name, image_bin, [cv2.IMWRITE_PNG_BILEVEL, 1])

    print("INFO:  Mask saved to:  ", mask_name)

    # create the image with an alpha channel

    rgba = cv2.cvtColor(orig, cv2.COLOR_RGB2RGBA)

    # assign the mask to the last channel of the image
    rgba[:, :, 3] = image_bin * 255
    cutout_name = orig_file_loc[:-4] + '_backlight_cutout.tif'
    cv2.imwrite(cutout_name, rgba)

    print("INFO:  Cutout saved to:", cutout_name)


if __name__ == '__main__':
    orig_file_loc = "I:\\3D_Scanner\\Manuscript\\Revision\\masking_comparison\\_x_00190_y_00000_orig.jpg"
    backlit_file_loc = "I:\\3D_Scanner\\Manuscript\\Revision\\masking_comparison\\ground_truth.png"

    generate_backlight_mask(orig_file_loc=orig_file_loc, backlit_file_loc=backlit_file_loc, threshold=240)
