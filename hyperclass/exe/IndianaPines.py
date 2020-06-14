from PyQt5 import QtWidgets
from hyperclass.gui.application import HyperclassConsole
from typing import List, Union, Tuple, Optional
import sys

ref_file = "/Users/tpmaxwel/Dropbox/Tom/Data/Aviris/IndianPines/documentation/Site3_Project_and_Ground_Reference_Files/19920612_AVIRIS_IndianPine_Site3_gr.tif"

classes = [ ('Background', (255, 255, 255) ),
            ('Alfalfa', (255, 254, 137) ),
            ('Corn-notill', (3,28,241) ),
            ('Corn-mintill', (255, 89, 1) ),
            ('Corn', (5, 255, 133) ),
            ('Grass/Pasture', (255, 2, 251) ),
            ('Grass/Trees',   (89, 1, 255 )),
            ('Grass/pasture-mowed', (3, 171, 255)),
            ('Hay-windrowed', (12, 255, 7 )),
            ('Oats', (172, 175, 84 )),
            ('Soybean-notill',(160, 78,158)),
            ('Soybean-mintill', (101, 173, 255)),
            ('Soybean-cleantill', (60, 91, 112) ),
            ('Wheat', (104, 192,  63)),
            ('Woods', (139,  69,  46)),
            ('Bldg-Grass-Tree-Drives', (119, 255, 172)),
            ('Stone/steel-towers', (119, 255, 172))
            ]

tabs = dict( Reference=dict( type="reference", classes=classes, path=ref_file ) )
app = QtWidgets.QApplication(sys.argv)
hyperclass = HyperclassConsole( classes, tabs=tabs )
hyperclass.show()
sys.exit(app.exec_())





