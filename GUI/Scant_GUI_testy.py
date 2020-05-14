"""
Locations of required executables and how to use them:
"""

# qt designer located at:
# C:\Users\PlumStation\Anaconda3\envs\tf-gpu\Lib\site-packages\pyqt5_tools\Qt\bin\designer.exe
# pyuic5 to convert UI to executable python code is located at:
# C:\Users\PlumStation\Anaconda3\envs\tf-gpu\Scripts\pyuic5.exe
# to convert the UI into the required .py file run:
# -x = input     -o = output
# pyuic5.exe -x "I:\3D_Scanner\scAnt\GUI\test.ui" -o "I:\3D_Scanner\scAnt\GUI\test.py"

"""
imports
"""
from PyQt5 import QtWidgets, QtGui
from testy import Ui_MainWindow  # importing our generated file
import sys

pressed = 0


class scAnt_mainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(scAnt_mainWindow, self).__init__()

        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)

        self.setWindowTitle("scAnt V 1.0")

        self.ui.pushButton_01.setFont(QtGui.QFont("Helvetica", 9))  # change font type and size

        self.ui.pushButton_01.clicked.connect(self.print_message)

    def print_message(self):
        global pressed
        pressed += 1
        if pressed == 1:
            times = "time!"
        else:
            times = "times!"

        print("What up, my Glib Globs! The button has been pressed", pressed, times)


app = QtWidgets.QApplication([])

application = scAnt_mainWindow()

application.show()

sys.exit(app.exec())
