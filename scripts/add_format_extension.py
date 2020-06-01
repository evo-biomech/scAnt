import os

# Function to rename multiple files
def addFormatExtension(source, extension):
    for count, filename in enumerate(os.listdir(source)):
        # rename() function will
        # rename all the files
        os.rename(source + "\\" + filename,
                  source + "\\" + filename + extension)

    # Driver Code


if __name__ == '__main__':
    # Calling main() function
    addFormatExtension(source="J:\\data\\atta_vollenweideri_0.0044\\_stacked\\mask\\", extension=".png")
