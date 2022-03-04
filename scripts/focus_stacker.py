# blur detection approach implemented based on
# pyimagesearch.com/2015/09/07/blur-detection-with-opencv/

# Use in the console with
"""
$ python focus_stacker.py --images "images_folder_path" --threshold "float"
"""

from imutils import paths
import argparse
import cv2
import os
from PIL import Image, ImageEnhance
import queue
import threading
import time
import sys
import numpy as np
from pathlib import Path
import platform


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
        process_stack(self.name, self.q)
        print("Exiting " + self.name)


def process_data(threadName, q):
    while not exitFlag:
        queueLock.acquire()
        if not workQueue.empty():
            data = q.get()
            queueLock.release()
            print("%s processing %s" % (threadName, data))
            checkFocus(images.joinpath(data))
        else:
            queueLock.release()


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

    if display_focus_check:
        cv2.imshow("Laplacian of Image", lap_image)

        cv2.waitKey(1)
    return lap_var


def checkFocus(image_path):
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

    if display_focus_check:
        # show the image
        cv2.putText(resized, "{}: {:.2f}".format(text, fm), (10, 30),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, color_text, 3)
        cv2.imshow("Image", resized)

        cv2.waitKey(1)


def process_stack(threadName, q):
    while not exitFlag_stacking:
        queueLock.acquire()
        if not workQueue_stacking.empty():
            data = q.get()
            queueLock.release()

            stack_name = data.split(" ")[1]
            stack_name = Path(stack_name).name[:-15]

            temp_output_folder = output_folder.joinpath(stack_name)

            print("%s is processing stack %s" % (threadName, stack_name))

            used_plattform = platform.system()

            if used_plattform == "Linux":
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

            if used_plattform == "Linux":
                os.system("enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 " +
                          "--hard-mask --contrast-edge-scale=1 --output=" +
                          output_path + image_str_focus)
            else:
                os.system(
                    str(path_to_external) + "\\enfuse --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 " +
                    "--hard-mask --gray-projector=l-star --contrast-edge-scale=1 --output=" +
                    output_path + image_str_focus)

            print("Stacked image saved as", output_path)

            stacked = Image.open(output_path)
            if additional_sharpening:
                enhancer = ImageEnhance.Sharpness(stacked)
                sharpened = enhancer.enhance(1.5)
                sharpened.save(output_path)

                print("Sharpened", output_path)

            for temp_img in temp_files:
                if used_plattform == "Linux":
                    os.system("rm " + str(temp_img))
                else:
                    os.system("del " + str(temp_img))

            print("Deleted temporary files of stack", data)
        else:
            queueLock.release()


if __name__ == '__main__':

    """
    ### Loading image paths into queue from disk ###
    """

    start = time.time()

    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--images", required=True,
                    help="path to input directory of images, or list of image paths")
    ap.add_argument("-t", "--threshold", type=float, default=10.0,
                    help="focus measures that fall below this value will be considered 'blurry'")
    ap.add_argument("-s", "--sharpen", type=bool, default=False,
                    help="apply sharpening to final result [True / False]")
    ap.add_argument("-d", "--display", type=bool, default=False,
                    help="show images with displayed focus score [True / False]")
    ap.add_argument("-b", "--single_stack", type=bool, default=False,
                    help="process all images in the specified folder [True / False]")
    ap.add_argument("-f", "--focus_check", type=bool, default=True,
                    help="check whether out-of-focus images should be discarded before stacking")
    ap.add_argument("-m", "--method", type=str, default="Default",
                    help="blending method (Default, 1-Star, Masks)")
    args = vars(ap.parse_args())

    print("Using a laplacian variance threshold of", args["threshold"], "for discarding out-of-focus images")

    # parsing in boolean arguments
    if args["display"] == "False" or not args["display"]:
        args["display"] = False
        print("Images will NOT be displayed during out-of-focus check")
    elif args["display"]:
        args["display"] = True
        print("Images will be displayed during out-of-focus check")

    if args["sharpen"] == "True":
        args["sharpen"] = True
        print("Output images will be additionally sharpened")
    else:
        args["sharpen"] = False
        print("Output images will NOT be additionally sharpened")

    if args["single_stack"] == "True" or args["single_stack"]:
        args["single_stack"] = True
        print("processing single stack")
    else:
        args["single_stack"] = False
        print("Processing all stacks found in target directory")

    if args["focus_check"] == True:
        blurry_removed = False
        print("Discarding out-of-focus images enabled")
    else:
        blurry_removed = True
        print("Processing all stacks found in target directory")

    ###############

    if not args["single_stack"]:
        # convert input str of file location into path object
        images = Path(args["images"])

        # define paths to all images and set the maximum number of items in the queue equivalent to the number of images
        all_image_paths = os.listdir(images)  # dir is your directory path

    else:
        # alternatively, image paths can be passed separated by commas. In this case those paths can be used directly
        raw_paths = args["images"].split(",")
        images = Path(raw_paths[0]).parent
        all_image_paths = []
        for img_path in raw_paths:
            all_image_paths.append(Path(img_path))

    stacking_method = args["method"]
    threshold = float(args["threshold"])
    display_focus_check = args["display"]
    additional_sharpening = args["sharpen"]

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

    if args["focus_check"]:

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
    print("Deleting temporary folders")

    for stack in stacks:
        stack_name = stack.split(" ")[1]
        stack_name = Path(stack_name).name[:-15]
        os.rmdir(output_folder.joinpath(stack_name))
        print("removed  ...", stack_name)

    print("Stacking finalised!")
    print("Time elapsed:", time.time() - start)
