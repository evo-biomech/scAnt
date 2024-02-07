import sys
import os, os.path
import math
import time
import glob
from generate_Meshroom_input_files import generate_sfm
from pathlib import Path

dirname = os.path.dirname(os.path.abspath(__file__))  # Absolute path of this file

verboseLevel = "\"" + "error" + "\""  # detail of the logs (error, info, etc)


def SilentMkdir(theDir):  # function to create a directory
    try:
        os.mkdir(theDir)
    except:
        pass
    return 0


def run_0_cameraInit(binPath, baseDir, imgDir):
    taskFolder = "/1_CameraInit"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 1/13 CAMERA INITIALIZATION -----------------------")

    imageFolder = "\"" + imgDir + "\""
    sensorDatabase = "\"" + str(Path(
        binPath).parent) + "\\share\\aliceVision\\cameraSensors.db" "\""  # Path to the sensors database, might change in later versions of meshrrom

    output = "\"" + baseDir + taskFolder + "/cameraInit.sfm" + "\""

    cmdLine = binPath + "\\aliceVision_cameraInit.exe"
    cmdLine += " --imageFolder {0} --sensorDatabase {1} --output {2}".format(
        imageFolder, sensorDatabase, output)

    cmdLine += " --defaultFieldOfView 45"
    cmdLine += " --allowSingleView 1"
    cmdLine += " --verboseLevel " + verboseLevel

    print(cmdLine)
    os.system(cmdLine)

    return 0


def run_0_GenerateCameraInitAndKnownPoseSfm(baseDir):
    # for this function, the folders and ouputs are generated from within the "generate_sfm" function
    SilentMkdir(baseDir)
    print("-------- 1/13 GENERATING INITIALISATION AND APPROXIMATED POSES ---------")

    generate_sfm(project_location=os.path.dirname(baseDir),
                 use_cutouts=False,
                 file_ending=".tif")


def run_1_importKnownPoses(binPath, baseDir):
    taskFolder = "/1_CameraInit"
    SilentMkdir(baseDir + taskFolder)

    print("--------------------- 1.5/13 IMPORTING KNOWN POSES ---------------------")

    _input = "\"" + baseDir + "/1_CameraInit/cameraInit.sfm" + "\""
    poses = "\"" + baseDir + "/1_CameraInit/cameras.json" + "\""
    output = "\"" + baseDir + "/1_CameraInit/sfmData.abc" + "\""

    cmdLine = binPath + "\\aliceVision_importKnownPoses"
    cmdLine += " --sfmData {0} --output {1}".format(_input, output)
    cmdLine += " --knownPosesData " + poses
    cmdLine += " --verboseLevel trace"

    print(cmdLine)
    os.system(cmdLine)

    return 0


def run_2_featureExtraction(binPath, baseDir,
                            numberOfImages, imagesPerGroup=400,
                            masksFolder=None):
    taskFolder = "/2_FeatureExtraction"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 2/13 FEATURE EXTRACTION -----------------------")

    _input = "\"" + baseDir + "/1_CameraInit/sfmData.abc" + "\""
    output = "\"" + baseDir + taskFolder + "\""

    cmdLine = binPath + "\\aliceVision_featureExtraction"
    cmdLine += " --input {0} --output {1}".format(_input, output)
    cmdLine += " --forceCpuExtraction 0"
    cmdLine += " --describerTypes dspsift"
    cmdLine += " --describerPreset high"
    cmdLine += " --describerQuality high"

    if masksFolder is not None:
        cmdLine += " --masksFolder " + masksFolder

    # when there are more than 40 images, it is good to send them in groups
    if (numberOfImages > imagesPerGroup):
        numberOfGroups = int(math.ceil(numberOfImages / imagesPerGroup))
        for i in range(numberOfGroups):
            cmd = cmdLine + " --rangeStart {} --rangeSize {} ".format(i * imagesPerGroup, imagesPerGroup)
            print("------- group {} / {} --------".format(i + 1, numberOfGroups))
            print(cmd)
            os.system(cmd)

    else:
        print(cmdLine)
        os.system(cmdLine)


def run_3_imageMatching(binPath, baseDir,
                        maxDescriptors=10000,
                        nbMatches=50):
    taskFolder = "/3_ImageMatching"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 3/13 IMAGE MATCHING -----------------------")

    _input = "\"" + baseDir + "/1_CameraInit/cameraInit.sfm" + "\""
    featuresFolders = "\"" + baseDir + "/2_FeatureExtraction" + "\""
    output = "\"" + baseDir + taskFolder + "/imageMatches.txt" + "\""

    cmdLine = binPath + "\\aliceVision_imageMatching.exe"
    cmdLine += " --input {0} --featuresFolders {1} --output {2}".format(
        _input, featuresFolders, output)

    cmdLine += " --tree " + "\"" + str(Path(binPath).parent) + "/share/aliceVision/vlfeat_K80L3.SIFT.tree\""
    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --maxDescriptors " + str(maxDescriptors)
    cmdLine += " --nbMatches " + str(nbMatches)

    print(cmdLine)
    os.system(cmdLine)


def run_4_featureMatching(binPath, baseDir, numberOfImages,
                          imagesPerGroup=400, match_from_known_poses=True):
    taskFolder = "/4_featureMatching"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 4/13 FEATURE MATCHING -----------------------")

    _input = "\"" + baseDir + "/1_CameraInit/cameraInit.sfm" + "\""
    output = "\"" + baseDir + taskFolder + "\""
    featuresFolders = "\"" + baseDir + "/2_FeatureExtraction" + "\""
    imagePairsList = "\"" + baseDir + "/3_ImageMatching/imageMatches.txt" + "\""

    cmdLine = binPath + "\\aliceVision_featureMatching.exe"
    cmdLine += " --input {0} --featuresFolders {1} --output {2} --imagePairsList {3}".format(
        _input, featuresFolders, output, imagePairsList)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --describerTypes dspsift"

    cmdLine += " --photometricMatchingMethod ANN_L2 --geometricEstimator acransac --geometricFilterType fundamental_matrix --distanceRatio 0.8"
    cmdLine += " --maxIteration 2048 --geometricError 0.0 --maxMatches 0"
    cmdLine += " --savePutativeMatches False --guidedMatching False --exportDebugFiles True"

    if match_from_known_poses:
        cmdLine += " --matchFromKnownCameraPoses 1"
        cmdLine += " --knownPosesGeometricErrorMax 0"
    else:
        cmdLine += " --matchFromKnownCameraPoses 0"
        cmdLine += " --knownPosesGeometricErrorMax 5"

    # when there are more than 20 images, it is good to send them in groups
    if (numberOfImages > imagesPerGroup):
        numberOfGroups = math.ceil(numberOfImages / imagesPerGroup)
        for i in range(numberOfGroups):
            cmd = cmdLine + " --rangeStart {} --rangeSize {} ".format(i * imagesPerGroup, imagesPerGroup)
            print("------- group {} / {} --------".format(i, numberOfGroups))
            print(cmd)
            os.system(cmd)

    else:
        print(cmdLine)
        os.system(cmdLine)


def run_5_structureFromMotion(binPath, baseDir):
    taskFolder = "/5_structureFromMotion"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 5/13 STRUCTURE FROM MOTION -----------------------")

    _input = "\"" + baseDir + "/1_CameraInit/cameraInit.sfm" + "\""
    output = "\"" + baseDir + taskFolder + "/sfm.abc" + "\" "
    outputViewsAndPoses = "\"" + baseDir + taskFolder + "/cameras.sfm" + "\""
    extraInfoFolder = "\"" + baseDir + taskFolder + "\""
    featuresFolders = "\"" + baseDir + "/2_FeatureExtraction" + "\""
    matchesFolders = "\"" + baseDir + "/4_featureMatching" + "\""

    cmdLine = binPath + "\\aliceVision_incrementalSfm.exe"
    cmdLine += " --input {0} --output {1} --outputViewsAndPoses {2} --extraInfoFolder {3} --featuresFolders {4} --matchesFolders {5}".format(
        _input, output, outputViewsAndPoses, extraInfoFolder, featuresFolders, matchesFolders)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --describerTypes dspsift"

    print(cmdLine)
    os.system(cmdLine)


def run_6_prepareDenseScene(binPath, baseDir):
    taskFolder = "/6_PrepareDenseScene"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 6/13 PREPARE DENSE SCENE -----------------------")
    _input = "\"" + baseDir + "/5_structureFromMotion/sfm.abc" + "\""
    output = "\"" + baseDir + taskFolder + "\" "

    cmdLine = binPath + "\\aliceVision_prepareDenseScene.exe"
    cmdLine += " --input {0}  --output {1} ".format(_input, output)

    cmdLine += " --verboseLevel " + verboseLevel

    print(cmdLine)
    os.system(cmdLine)


def run_7_depthMap(binPath, baseDir, numberOfImages, groupSize=6, downscale=1):
    taskFolder = "/7_DepthMap"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 7/13 DEPTH MAP -----------------------")
    _input = "\"" + baseDir + "/5_structureFromMotion/sfm.abc" + "\""
    output = "\"" + baseDir + taskFolder + "\""
    imagesFolder = "\"" + baseDir + "/6_PrepareDenseScene" + "\""

    cmdLine = binPath + "\\aliceVision_depthMapEstimation.exe"
    cmdLine += " --input {0}  --output {1} --imagesFolder {2}".format(
        _input, output, imagesFolder)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --downscale " + str(downscale)
    cmdLine += " --minViewAngle 1"
    cmdLine += " --sgmMaxDepths 3000"

    numberOfBatches = int(math.ceil(numberOfImages / groupSize))

    for i in range(numberOfBatches):
        groupStart = groupSize * i
        currentGroupSize = min(groupSize, numberOfImages - groupStart)
        if groupSize > 1:
            print("DepthMap Group {} of {} : {} to {}".format(i, numberOfBatches, groupStart, currentGroupSize))
            cmd = cmdLine + (" --rangeStart {} --rangeSize {}".format(str(groupStart), str(groupSize)))
            print(cmd)
            os.system(cmd)


def run_8_depthMapFilter(binPath, baseDir):
    taskFolder = "/8_DepthMapFilter"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 8/13 DEPTH MAP FILTER-----------------------")
    _input = "\"" + baseDir + "/5_structureFromMotion/sfm.abc" + "\""
    output = "\"" + baseDir + taskFolder + "\""
    depthMapsFolder = "\"" + baseDir + "/7_DepthMap" + "\""

    cmdLine = binPath + "\\aliceVision_depthMapFiltering.exe"
    cmdLine += " --input {0}  --output {1} --depthMapsFolder {2}".format(
        _input, output, depthMapsFolder)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --minViewAngle 1"

    print(cmdLine)
    os.system(cmdLine)


def run_9_meshing(binPath, baseDir,
                  maxInputPoints=50000000,
                  maxPoints=1000000):
    taskFolder = "/9_Meshing"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 9/13 MESHING -----------------------")
    _input = "\"" + baseDir + "/5_structureFromMotion/sfm.abc" + "\""
    output = "\"" + baseDir + taskFolder + "/densePointCloud.abc" "\""
    outputMesh = "\"" + baseDir + taskFolder + "/mesh.obj" + "\""
    depthMapsFolder = "\"" + baseDir + "/8_DepthMapFilter" + "\""

    cmdLine = binPath + "\\aliceVision_meshing.exe"
    cmdLine += " --input {0}  --output {1} --outputMesh {2} --depthMapsFolder {3} ".format(
        _input, output, outputMesh, depthMapsFolder)

    cmdLine += " --maxInputPoints " + str(maxInputPoints)
    cmdLine += " --maxPoints " + str(maxPoints)
    cmdLine += " --addLandmarksToTheDensePointCloud 1"
    cmdLine += " --estimateSpaceFromSfM 0"
    cmdLine += " --simGaussianSizeInit 5"
    cmdLine += " --simGaussianSize 5"

    cmdLine += " --verboseLevel " + verboseLevel

    print(cmdLine)
    os.system(cmdLine)


def run_10_meshFiltering(binPath, baseDir, keepLargestMeshOnly="True"):
    taskFolder = "/10_MeshFiltering"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 10/13 MESH FILTERING -----------------------")
    inputMesh = "\"" + baseDir + "/9_Meshing/mesh.obj" + "\""
    outputMesh = "\"" + baseDir + taskFolder + "/mesh.obj" + "\""

    cmdLine = binPath + "\\aliceVision_meshFiltering.exe"
    cmdLine += " --inputMesh {0}  --outputMesh {1}".format(
        inputMesh, outputMesh)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --keepLargestMeshOnly " + keepLargestMeshOnly

    print(cmdLine)
    os.system(cmdLine)


def run_11_meshDecimate(binPath, baseDir, simplificationFactor=0.8, maxVertices=15000):
    taskFolder = "/11_MeshDecimate"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 11/13 MESH DECIMATE -----------------------")
    inputMesh = "\"" + baseDir + "/10_MeshFiltering/mesh.obj" + "\""
    outputMesh = "\"" + baseDir + taskFolder + "/mesh.obj" + "\""

    cmdLine = binPath + "\\aliceVision_meshDecimate.exe"
    cmdLine += " --input {0}  --output {1}".format(
        inputMesh, outputMesh)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --simplificationFactor " + str(simplificationFactor)
    cmdLine += " --maxVertices " + str(maxVertices)

    print(cmdLine)
    os.system(cmdLine)


def run_12_meshResampling(binPath, baseDir, simplificationFactor=0.8, maxVertices=15000):
    taskFolder = "/12_MeshResampling"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 12/13 MESH RESAMPLING -----------------------")
    inputMesh = "\"" + baseDir + "/11_MeshDecimate/mesh.obj" + "\""
    outputMesh = "\"" + baseDir + taskFolder + "/mesh.obj" + "\""

    cmdLine = binPath + "\\aliceVision_meshResampling.exe"
    cmdLine += " --input {0}  --output {1}".format(inputMesh, outputMesh)

    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --simplificationFactor " + str(simplificationFactor)
    cmdLine += " --maxVertices " + str(maxVertices)

    print(cmdLine)
    os.system(cmdLine)


def run_13_texturing(binPath, baseDir, textureSide=8192, downscale=2,
                     unwrapMethod="Basic",
                     colorMappingFileType="png"):
    taskFolder = "/13_Texturing"
    SilentMkdir(baseDir + taskFolder)

    print("----------------------- 13/13 TEXTURING  -----------------------")
    _input = "\"" + baseDir + "/9_Meshing/densePointCloud.abc" + "\""
    imagesFolder = "\"" + baseDir + "/6_PrepareDenseScene" "\""
    inputMesh = "\"" + baseDir + "/12_MeshResampling/mesh.obj" + "\""
    output = "\"" + baseDir + taskFolder + "\""

    cmdLine = binPath + "\\aliceVision_texturing.exe"
    cmdLine += " --input {0} --inputMesh {1} --output {2} --imagesFolder {3}".format(
        _input, inputMesh, output, imagesFolder)

    cmdLine += " --textureSide " + str(textureSide)
    cmdLine += " --downscale " + str(downscale)
    cmdLine += " --verboseLevel " + verboseLevel
    cmdLine += " --unwrapMethod " + unwrapMethod
    cmdLine += " --colorMappingFileType " + colorMappingFileType
    cmdLine += " --fillHoles " + "1"

    print(cmdLine)
    os.system(cmdLine)


def main():
    # Pass the arguments of the function as parameters in the command line code
    binPath = sys.argv[1]  # --> path of the binary files from Meshroom
    baseDir = os.path.join(sys.argv[2], "reconstruction")  # --> name of the Folder containing the process
    imgDir = os.path.join(sys.argv[2], "stacked")
    maskDir = os.path.join(sys.argv[2], "stacked")

    numberOfImages = len(glob.glob1(imgDir, "*.tif"))

    SilentMkdir(baseDir)

    startTime = time.time()

    # run_0_cameraInit(binPath, baseDir, imgDir)
    run_0_GenerateCameraInitAndKnownPoseSfm(baseDir)
    run_1_importKnownPoses(binPath, baseDir)
    run_2_featureExtraction(binPath, baseDir, numberOfImages, masksFolder=maskDir)
    run_3_imageMatching(binPath, baseDir)
    run_4_featureMatching(binPath, baseDir, numberOfImages, match_from_known_poses=True)
    run_5_structureFromMotion(binPath, baseDir)
    run_6_prepareDenseScene(binPath, baseDir)
    run_7_depthMap(binPath, baseDir, numberOfImages)
    run_8_depthMapFilter(binPath, baseDir)
    run_9_meshing(binPath, baseDir)
    run_10_meshFiltering(binPath, baseDir)
    run_11_meshDecimate(binPath, baseDir)
    run_12_meshResampling(binPath, baseDir)
    run_13_texturing(binPath, baseDir)

    print("-------------------------------- DONE ----------------------")
    endTime = time.time()
    hours, rem = divmod(endTime - startTime, 3600)
    minutes, seconds = divmod(rem, 60)
    print("time elapsed: " + "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds))


main()
