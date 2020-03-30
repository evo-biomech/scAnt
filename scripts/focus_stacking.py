# blur detection approach implemented based on
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
import queue
import threading
import time
import sys
import numpy as np


class myThread(threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q

    def run(self):
        print("Starting " + self.name)
        process_data(self.name, self.q)
        print("Exiting " + self.name)

class myThread_Stacking(threading.Thread):
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
            checkFocus(args["images"] + "\\" + data)
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

    if args["display"]:
        cv2.imshow("Laplacian of Image", lap_image)

        cv2.waitKey(1)
    return lap_var


def checkFocus(image_path):
    image = cv2.imread(image_path)

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
    if fm < args["threshold"]:
        text = "BLURRY"
        color_text = (0, 0, 255)
        rejected_images.append(image_path)
    else:
        text = "NOT Blurry"
        color_text = (255, 0, 0)
        usable_images.append(image_path)

    print(image_path, "is", text)

    if args["display"]:
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

            print(data.split(" ")[1])
            stack_name = data.split(" ")[1].split("\\")[-1][:-15]

            print("%s processing stack %s" % (threadName, stack_name))

            os.system(path_to_external + "align_image_stack -m -x -c 100 -a " + output_folder + "\\"
                      + str(stack_name) + "OUT" + data)

            image_str_focus = ""
            temp_files = []
            print("\nFocus stacking...")
            # go through list in reverse order (better results of focus stacking)
            for img in range(path_num):
                if img < 10:
                    path = output_folder + "\\" + str(stack_name) + "OUT000" + str(img) + ".tif"
                elif img < 100:
                    path = output_folder + "\\" + str(stack_name) + "OUT00" + str(img) + ".tif"
                elif img < 1000:
                    path = output_folder + "\\" + str(stack_name) + "OUT0" + str(img) + ".tif"
                else:
                    path = output_folder + "\\" + str(stack_name) + "OUT" + str(img) + ".tif"

                temp_files.append(path)
                image_str_focus += " " + path

            output_path = output_folder + "\\" + stack_name + ".tif"
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

            print("Deleted temporary files of stack", data)
        else:
            queueLock.release()


"""
### Loading image paths into queue from disk ###
"""

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--images", required=True,
                help="path to input directory of images")
ap.add_argument("-t", "--threshold", type=float, default=10.0,
                help="focus measures that fall below this value will be considered 'blurry'")
ap.add_argument("-s", "--sharpen", type=bool, default=False,
                help="apply sharpening to final result [True / False]")
ap.add_argument("-d", "--display", type=bool, default=True,
                help="show images with displayed focus score [True / False]")
args = vars(ap.parse_args())

# parsing in boolean arguments
if args["display"] == "False":
    args["display"] = False
else:
    args["display"] = True

if args["sharpen"] == "True":
    args["sharpen"] = True
else:
    args["sharpen"] = False

blurry_removed = input("Have you removed blurry images already? [y/n] default n")

# setup as many threads as there are (virtual) CPUs
exitFlag = 0
num_virtual_cores = getThreads()
threadList = createThreadList(num_virtual_cores)
print("Found", num_virtual_cores, "(virtual) cores...")
queueLock = threading.Lock()

# define paths to all images and set the maximum number of items in the queue equivalent to the number of images
all_image_paths = os.listdir(args["images"])  # dir is your directory path
workQueue = queue.Queue(len(all_image_paths))
threads = []
threadID = 1

# create list of image paths classified as in-focus or blurry
usable_images = []
rejected_images = []

"""
### extracting "in-focus" images for further processing ###
"""

if blurry_removed != "y":

    # Create new threads
    for tName in threadList:
        thread = myThread(threadID, tName, workQueue)
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

path_to_external = os.path.dirname(os.getcwd()) + "\\external\\"

output_folder = args["images"] + "_stacked"

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

    path_num = 0
    for path in usable_images:
        if current_stack_name == path[:-15]:
            image_str_align += " " + args["images"] + "\\" + path
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
# only use half the number of CPUs for stacking as the process supports multi core processing in part
threadList_stacking = createThreadList(int(num_virtual_cores / 2))
print("Using", len(threadList_stacking), "threads for stacking...")
queueLock = threading.Lock()

# define paths to all images and set the maximum number of items in the queue equivalent to the number of images
workQueue_stacking = queue.Queue(len(stacks))
threads = []
threadID = 1

# Create new threads
for tName in threadList_stacking:
    thread = myThread_Stacking(threadID, tName, workQueue_stacking)
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
    
    
    os.system(path_to_external + "align_image_stack -m -x -c 100 -a " + output_folder + "\\"
              + str(current_stack_name.split('\\')[-1]) + "OUT" + image_str_align)

    image_str_focus = ""
    temp_files = []
    print("\nFocus stacking...")
    # go through list in reverse order (better results of focus stacking)
    for img in range(path_num):
        if img < 10:
            path = output_folder + "\\" + str(current_stack_name.split('\\')[-1]) + "OUT000" + str(img) + ".tif"
        elif img < 100:
            path = output_folder + "\\" + str(current_stack_name.split('\\')[-1]) + "OUT00" + str(img) + ".tif"
        elif img < 1000:
            path = output_folder + "\\" + str(current_stack_name.split('\\')[-1]) + "OUT0" + str(img) + ".tif"
        else:
            path = output_folder + "\\" + str(current_stack_name.split('\\')[-1]) + "OUT" + str(img) + ".tif"

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
    """

print("Stacking finalised!")
