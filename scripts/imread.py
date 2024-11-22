from cv2 import imread
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("-p", "--path", required=True)
args = vars(ap.parse_args())
imread(args["path"])
