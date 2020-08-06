from hyperclass.config.inputs import ConfigurationDialog
from PyQt5.QtWidgets import QApplication
from hyperclass.data.manager import dataManager
import sys

default_settings = {}
app = QApplication(sys.argv)
dataManager.initProject( "tessclass", default_settings )
preferences = ConfigurationDialog()
preferences.show()
sys.exit(app.exec_())