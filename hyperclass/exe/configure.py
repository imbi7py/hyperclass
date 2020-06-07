from hyperclass.gui.config import PreferencesDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
from hyperclass.data.aviris.manager import DataManager
import sys

app = QApplication(sys.argv)
preferences = PreferencesDialog( None, QSettings.SystemScope )
preferences.show()
sys.exit(app.exec_())