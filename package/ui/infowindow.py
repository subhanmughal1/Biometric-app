import os
from PyQt6 import uic,QtCore
from PyQt6.QtWidgets import QMainWindow
from package import config
from package.utils.paths import resource_path
from pathlib import Path



# Subclass QMainWindow to customize the application's main window
class InfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(os.path.join(Path(__file__).parent.resolve(),'src','infowindow.ui'), self)
        self.setWindowTitle(config.appName)
        # disable resizing
        self.setWindowFlags(QtCore.Qt.WindowType.CustomizeWindowHint | QtCore.Qt.WindowType.WindowCloseButtonHint | QtCore.Qt.WindowType.WindowMinimizeButtonHint) 
        self.appConfig = config.loadConfig()

        # bind signals to actions
        # self.actionStartDevice.triggered.connect(self.restartDevice)