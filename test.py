import cv2
import platform
import numpy as np

# check the number of connected working webcams
check_port = 0
cam_list = []
is_working = True
while is_working:
    test_camera = cv2.VideoCapture(check_port, cv2.CAP_DSHOW)
    if not test_camera.isOpened():
        is_working = False
        print("Camera at port %s is not working/does not exist." %check_port)
    else:
        is_reading, img = test_camera.read()
        if is_reading:
            exp = test_camera.get(15)
            gain = test_camera.get(14)
            fps = test_camera.get(5)
            width = test_camera.get(3)
            height = test_camera.get(4)

            print(exp, gain, fps, width, height)
            cam_list.append(check_port)
            test_camera.release()
            print("Detected camera port", cam_list[-1])
    check_port +=1

# by default, use the first camera in the retrieved list

num_cameras = len(cam_list)

print('Number of cameras detected: %d' % num_cameras)

# Finish if there are no cameras
if num_cameras == 0:

    print('Not enough cameras!')
    input('Done! Press Enter to exit...')
    # return False

print("\nExecute CustomWEBCAM.initialise_camera and pass the number of the listed camera, "
      "in case more than one has been detected!\n")

cam = cv2.VideoCapture(cam_list[0], cv2.CAP_DSHOW)

success, image_result = cam.read()

if not success:
    print('Image incomplete with image status %d...' % success)

else:
    # Print image information
    width = cam.get(3)
    height = cam.get(4)

    ret = cam.set(14,-1.0)
    height = cam.get(14)
    width = ret
    print('Captured Image with width = %d, height = %d' % (width, height))

    # Create a unique filename
    filename = "img_name2.jpg"
    # Save RAW image
    cv2.imwrite(filename,image_result)

    print('Image saved as %s' % filename)

    cam.release()