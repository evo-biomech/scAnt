# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'scAnt_projectSettings_dlg.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(453, 327)
        self.gridLayout = QtWidgets.QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)
        self.frame_outputSettings = QtWidgets.QFrame(Dialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_outputSettings.sizePolicy().hasHeightForWidth())
        self.frame_outputSettings.setSizePolicy(sizePolicy)
        self.frame_outputSettings.setMinimumSize(QtCore.QSize(271, 0))
        self.frame_outputSettings.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_outputSettings.setFrameShape(QtWidgets.QFrame.Box)
        self.frame_outputSettings.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_outputSettings.setObjectName("frame_outputSettings")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.frame_outputSettings)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label_projectName = QtWidgets.QLabel(self.frame_outputSettings)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_projectName.sizePolicy().hasHeightForWidth())
        self.label_projectName.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        self.label_projectName.setFont(font)
        self.label_projectName.setAlignment(QtCore.Qt.AlignCenter)
        self.label_projectName.setObjectName("label_projectName")
        self.gridLayout_2.addWidget(self.label_projectName, 4, 0, 1, 1)
        self.lineEdit_projectName = QtWidgets.QLineEdit(self.frame_outputSettings)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_projectName.sizePolicy().hasHeightForWidth())
        self.lineEdit_projectName.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        self.lineEdit_projectName.setFont(font)
        self.lineEdit_projectName.setObjectName("lineEdit_projectName")
        self.gridLayout_2.addWidget(self.lineEdit_projectName, 4, 1, 1, 2)
        self.lineEdit_outputLocation = QtWidgets.QLineEdit(self.frame_outputSettings)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_outputLocation.sizePolicy().hasHeightForWidth())
        self.lineEdit_outputLocation.setSizePolicy(sizePolicy)
        self.lineEdit_outputLocation.setMinimumSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setItalic(True)
        self.lineEdit_outputLocation.setFont(font)
        self.lineEdit_outputLocation.setObjectName("lineEdit_outputLocation")
        self.gridLayout_2.addWidget(self.lineEdit_outputLocation, 1, 1, 1, 2)
        self.pushButton_browseOutput = QtWidgets.QPushButton(self.frame_outputSettings)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_browseOutput.sizePolicy().hasHeightForWidth())
        self.pushButton_browseOutput.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        self.pushButton_browseOutput.setFont(font)
        self.pushButton_browseOutput.setObjectName("pushButton_browseOutput")
        self.gridLayout_2.addWidget(self.pushButton_browseOutput, 1, 0, 1, 1)
        self.lineEdit_chosenConfig = QtWidgets.QLineEdit(self.frame_outputSettings)
        self.lineEdit_chosenConfig.setEnabled(False)
        self.lineEdit_chosenConfig.setObjectName("lineEdit_chosenConfig")
        self.gridLayout_2.addWidget(self.lineEdit_chosenConfig, 6, 2, 1, 1)
        self.label_outputSettings = QtWidgets.QLabel(self.frame_outputSettings)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_outputSettings.sizePolicy().hasHeightForWidth())
        self.label_outputSettings.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.label_outputSettings.setFont(font)
        self.label_outputSettings.setObjectName("label_outputSettings")
        self.gridLayout_2.addWidget(self.label_outputSettings, 0, 0, 1, 2)
        self.pushButton_chooseConfig = QtWidgets.QPushButton(self.frame_outputSettings)
        self.pushButton_chooseConfig.setEnabled(False)
        self.pushButton_chooseConfig.setObjectName("pushButton_chooseConfig")
        self.gridLayout_2.addWidget(self.pushButton_chooseConfig, 6, 1, 1, 1)
        self.checkBox_includePresets = QtWidgets.QCheckBox(self.frame_outputSettings)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.checkBox_includePresets.setFont(font)
        self.checkBox_includePresets.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.checkBox_includePresets.setObjectName("checkBox_includePresets")
        self.gridLayout_2.addWidget(self.checkBox_includePresets, 6, 0, 1, 1)
        self.gridLayout.addWidget(self.frame_outputSettings, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept) # type: ignore
        self.buttonBox.rejected.connect(Dialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.label_projectName.setText(_translate("Dialog", "Project name"))
        self.lineEdit_projectName.setText(_translate("Dialog", "test_project"))
        self.lineEdit_outputLocation.setText(_translate("Dialog", "current_folder"))
        self.pushButton_browseOutput.setText(_translate("Dialog", "Choose Output Folder"))
        self.lineEdit_chosenConfig.setText(_translate("Dialog", "path/to/preset.yaml"))
        self.label_outputSettings.setText(_translate("Dialog", "Project Settings"))
        self.pushButton_chooseConfig.setText(_translate("Dialog", "Choose Config"))
        self.checkBox_includePresets.setText(_translate("Dialog", "Load Presets"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
