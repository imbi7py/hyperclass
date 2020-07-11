from hyperclass.config.inputs import PrepareInputsDialog
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings
import sys

app = QApplication(sys.argv)
preferences = PrepareInputsDialog( {}, 1,  QSettings.SystemScope)
preferences.show()
sys.exit(app.exec_())