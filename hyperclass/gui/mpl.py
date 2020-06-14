import sys
import xarray as xa
import rioxarray as rio
from hyperclass.plot.console import LabelingConsole
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from hyperclass.plot.spectra import SpectralPlot
from matplotlib.image import AxesImage
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QAction, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy, QPushButton
from hyperclass.data.aviris.manager import DataManager
from hyperclass.data.aviris.tile import Tile, Block
from hyperclass.umap.manager import UMAPManager
from matplotlib.axes import Axes
from typing import List, Union, Dict, Callable, Tuple, Optional, Any
from hyperclass.data.google import GoogleMaps
from hyperclass.gui.tasks import taskRunner, Task
from hyperclass.plot.labels import format_colors
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class MplWidget(QWidget):
    def __init__(self, umgr: UMAPManager, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)
        self.setLayout(QVBoxLayout())
        self.canvas = MplCanvas(self, umgr, **kwargs )
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.canvas)

    def initPlots( self ):
        self.canvas.console.initPlots()

    @property
    def spectral_plot(self):
        return self.canvas.console.spectral_plot

    def setBlock(self, block_coords: Tuple[int], **kwargs    ):
        return self.canvas.setBlock( block_coords, **kwargs  )

    def addNavigationListener(self, listener):
        self.canvas.console.addNavigationListener( listener )

    def getNewImage(self):
        return self.canvas.getNewImage()

    def getTile(self):
        return self.canvas.console.getTile()

    def getBlock(self) -> Block:
        return self.canvas.getBlock()

    def extent(self):
        return self.canvas.extent()

    def keyPressEvent( self, event ):
        event = dict( event="key", type="press", key=event.key() )
        self.process_event(event)

    def keyReleaseEvent(self, event):
        event = dict( event="key", type="release", key=event.key() )
        self.process_event(event)

    def process_event( self, event: Dict ):
        self.canvas.process_event(event )

    @property
    def button_actions(self) -> Dict[str, Callable]:
        return self.canvas.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.canvas.menu_actions

    def mpl_update(self):
        self.canvas.mpl_update()
        self.update()
        self.repaint()

class MplCanvas(FigureCanvas):

    def __init__(self, parent, umgr: UMAPManager, **kwargs ):
        self.figure = Figure()
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding )
        FigureCanvas.updateGeometry(self)
        self.console = LabelingConsole( umgr, figure=self.figure, **kwargs )

    def process_event( self, event: Dict ):
        self.console.process_event(event)

    def setBlock(self, block_coords: Tuple[int], **kwargs   ):
        return self.console.setBlock( block_coords, **kwargs  )

    @property
    def button_actions(self) -> Dict[str,Callable]:
        return self.console.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.console.menu_actions

    def mpl_update(self):
        self.console.update_canvas()
        self.update()
        self.repaint()

    def getNewImage(self):
        return self.console.getNewImage()

    def getBlock(self) -> Block:
        return self.console.block

    def extent(self):
        return self.console.block.extent()



class SpectralPlotCanvas(FigureCanvas):

    def __init__(self, parent, plot: SpectralPlot, **kwargs ):
        self.figure = Figure( constrained_layout=True )
        FigureCanvas.__init__(self, self.figure )
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding )
        FigureCanvas.setContentsMargins( self, 0, 0, 0, 0 )
        plot.init( self.figure )
        self.plot: SpectralPlot = plot
        FigureCanvas.updateGeometry(self)

    def clear(self):
        self.plot.clear()

    def process_event( self, event: Dict ):
        self.plot.process_event(event)

    def setBlock(self, block_coords: Tuple[int]   ):
        self.plot.setBlock( block_coords )

    @property
    def button_actions(self) -> Dict[str,Callable]:
        return self.plot.button_actions

    @property
    def menu_actions(self) -> Dict:
        return self.plot.menu_actions

    def mpl_update(self):
        self.plot.update_canvas()
        self.update()
        self.repaint()


class SatellitePlotCanvas(FigureCanvas):

    RIGHT_BUTTON = 3
    MIDDLE_BUTTON = 2
    LEFT_BUTTON = 1

    def __init__(self, parent, toolbar: NavigationToolbar, block: Block = None, **kwargs ):
        self.figure = Figure( constrained_layout=True )
        FigureCanvas.__init__(self, self.figure )
        self.plot = None
        self.image = None
        self.block = None
        self.mouse_listeners = []
        #        self.setParent(parent)
        self.toolbar = toolbar
        FigureCanvas.setSizePolicy(self, QSizePolicy.Ignored, QSizePolicy.Ignored)
        FigureCanvas.setContentsMargins( self, 0, 0, 0, 0 )
        FigureCanvas.updateGeometry(self)
        self.axes: Axes = self.figure.add_subplot(111)
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )
        self.google_maps_zoom_level = 17
        self.google = None
        if block is not None: self.setBlock( block )

    def addEventListener( self, listener ):
        self.mouse_listeners.append( listener )

    def setBlock(self, block: Block, type ='satellite'):
        self.block = block
        self.google = GoogleMaps(block)
        try:
            extent = block.extent(4326)
            self.image = self.google.get_tiled_google_map(type, extent, self.google_maps_zoom_level)
            self.plot: AxesImage = self.axes.imshow(self.image, extent=extent, alpha=1.0, aspect='auto' )
            self.axes.set_xlim(extent[0],extent[1])
            self.axes.set_ylim(extent[2],extent[3])
            self._mousepress = self.plot.figure.canvas.mpl_connect('button_press_event', self.onMouseClick )
        except AttributeError:
            print( "Cant get spatial bounds for satellite image")

    def set_axis_limits( self, xlims, ylims ):
        if self.image is not None:
            xlims, ylims = self.block.project_extent( xlims, ylims, 4326 )
            self.axes.set_xlim(*xlims )
            self.axes.set_ylim(*ylims)
            print( f"Setting satellite image bounds: {xlims} {ylims}")
            self.figure.canvas.draw_idle()

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if event.inaxes ==  self.axes:
                for listener in self.mouse_listeners:
                    event = dict( event="pick", type="image", lat=event.ydata, lon=event.xdata, button=int(event.button) )
                    listener.process_event(event)

    def mpl_update(self):
        self.figure.canvas.draw_idle()
#        self.repaint()

class ReferenceImageCanvas(FigureCanvas):

    RIGHT_BUTTON = 3
    MIDDLE_BUTTON = 2
    LEFT_BUTTON = 1

    def __init__(self, parent, image_spec: Dict[str,Any], **kwargs ):
        self.figure = Figure( constrained_layout=True )
        FigureCanvas.__init__(self, self.figure )
        self.mouse_listeners = []
        self.spec = image_spec
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Ignored, QSizePolicy.Ignored)
        FigureCanvas.setContentsMargins( self, 0, 0, 0, 0 )
        FigureCanvas.updateGeometry(self)
        self.axes: Axes = self.figure.add_subplot(111)
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        self.figure.set_constrained_layout_pads( w_pad=0., h_pad=0. )
        self.image: xa.DataArray = rio.open_rasterio( self.spec['path'] )
        self.xdim = self.image.dims[-1]
        self.ydim = self.image.dims[-2]
        self.classes = format_colors( self.spec.get( 'classes', [] ) )
        if self.classes == None:    cmap = "jet"
        else:                       cmap = ListedColormap( [ item[1] for item in self.classes ] )
        self.plot: AxesImage = self.axes.imshow( self.image.squeeze().values, alpha=1.0, aspect='auto', cmap=cmap  )
        self._mousepress = self.plot.figure.canvas.mpl_connect('button_press_event', self.onMouseClick)

    def addEventListener( self, listener ):
        self.mouse_listeners.append( listener )

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if event.inaxes ==  self.axes:
                coords = { self.xdim: event.xdata, self.ydim: event.ydata  }
                point_data = self.image.sel( **coords, method='nearest' ).values.tolist()
                for listener in self.mouse_listeners:
                    event = dict( event="pick", type="image", lat=event.ydata, lon=event.xdata, button=int(event.button) )
                    listener.process_event(event)


    def mpl_update(self):
        self.figure.canvas.draw_idle()

