import matplotlib.widgets
import matplotlib.patches
from pynndescent import NNDescent
from functools import partial
from hyperclass.plot.widgets import ColoredRadioButtons, ButtonBox
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.gridspec import GridSpec, SubplotSpec
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from  matplotlib.transforms import Bbox
from collections import OrderedDict
from hyperclass.umap.manager import UMAPManager
import matplotlib.pyplot as plt
from matplotlib.dates import num2date
from matplotlib.collections import PathCollection
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.graph.flow import ActivationFlow
from hyperclass.gui.tasks import taskRunner
from PyQt5.QtCore import QTimer
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from skimage.transform import ProjectiveTransform
import matplotlib as mpl
import pandas as pd
import xarray as xa
import numpy as np
from typing import List, Union, Dict, Callable, Tuple, Optional
import time, math, atexit, csv
from enum import Enum

def get_color_bounds( color_values: List[float] ) -> List[float]:
    color_bounds = []
    for iC, cval in enumerate( color_values ):
        if iC == 0: color_bounds.append( cval - 0.5 )
        else: color_bounds.append( (cval + color_values[iC-1])/2.0 )
    color_bounds.append( color_values[-1] + 0.5 )
    return color_bounds

class ADirection(Enum):
    BACKWARD = -1
    STOP = 0
    FORWARD = 1

class EventSource:

    def __init__( self, action: Callable, **kwargs ):
        self.timer = QTimer()
        self.timer.timeout.connect( action )
        atexit.register( self.exit )

    def start(self, interval, delay = None ):
        if delay is not None:
            start_action = partial( self.timer.start, interval )
            self.timer = QTimer()
            self.timer.setSingleShot( True )
            self.timer.timeout.connect( start_action )
            self.timer.start( delay )
        else:
            self.timer.start( interval )

    def stop(self):
        self.timer.stop()

    def exit(self):
        self.timer.stop()

class PageSlider(matplotlib.widgets.Slider):

    def __init__(self, ax: Axes, numpages = 10, valinit=0, valfmt='%1d', **kwargs ):
        self.facecolor=kwargs.get('facecolor',"yellow")
        self.activecolor = kwargs.pop('activecolor',"blue" )
        self.stepcolor = kwargs.pop('stepcolor', "#ff6f6f" )
        self.animcolor = kwargs.pop('animcolor', "#6fff6f" )
        self.on_animcolor = kwargs.pop('on-animcolor', "#006622")
        self.fontsize = kwargs.pop('fontsize', 10)
        self.animation_controls = kwargs.pop('dynamic', True )
        self.maxIndexedPages = 24
        self.numpages = numpages
        self.init_anim_delay: float = 0.5   # time between timer events in seconds
        self.anim_delay: float = self.init_anim_delay
        self.anim_delay_multiplier = 1.5
        self.anim_state = ADirection.STOP
        self.axes = ax
        self.event_source = EventSource( self.step, delay = self.init_anim_delay )

        super(PageSlider, self).__init__(ax, "", 0, numpages, valinit=valinit, valfmt=valfmt, **kwargs)

        self.poly.set_visible(False)
        self.vline.set_visible(False)
        self.pageRects = []
        indexMod = math.ceil( self.numpages / self.maxIndexedPages )
        for i in range(numpages):
            facecolor = self.activecolor if i==valinit else self.facecolor
            r  = matplotlib.patches.Rectangle((float(i)/numpages, 0), 1./numpages, 1, transform=ax.transAxes, facecolor=facecolor)
            ax.add_artist(r)
            self.pageRects.append(r)
            if i % indexMod == 0:
                ax.text(float(i)/numpages+0.5/numpages, 0.5, str(i+1), ha="center", va="center", transform=ax.transAxes, fontsize=self.fontsize)
        self.valtext.set_visible(False)

        divider = make_axes_locatable(ax)
        bax = divider.append_axes("right", size="5%", pad=0.05)
        fax = divider.append_axes("right", size="5%", pad=0.05)
        self.button_back = matplotlib.widgets.Button(bax, label='$\u25C1$', color=self.stepcolor, hovercolor=self.activecolor)
        self.button_forward = matplotlib.widgets.Button(fax, label='$\u25B7$', color=self.stepcolor, hovercolor=self.activecolor)
        self.button_back.label.set_fontsize(self.fontsize)
        self.button_forward.label.set_fontsize(self.fontsize)
        self.button_back.on_clicked(self.step_backward)
        self.button_forward.on_clicked(self.step_forward)

        if self.animation_controls:
            afax = divider.append_axes("left", size="5%", pad=0.05)
            asax = divider.append_axes("left", size="5%", pad=0.05)
            abax = divider.append_axes("left", size="5%", pad=0.05)
            self.button_aback    = matplotlib.widgets.Button( abax, label='$\u25C0$', color=self.animcolor, hovercolor=self.activecolor)
            self.button_astop = matplotlib.widgets.Button( asax, label='$\u25FE$', color=self.animcolor, hovercolor=self.activecolor)
            self.button_aforward = matplotlib.widgets.Button( afax, label='$\u25B6$', color=self.animcolor, hovercolor=self.activecolor)

            self.button_aback.label.set_fontsize(self.fontsize)
            self.button_astop.label.set_fontsize(self.fontsize)
            self.button_aforward.label.set_fontsize(self.fontsize)
            self.button_aback.on_clicked(self.anim_backward)
            self.button_astop.on_clicked(self.anim_stop)
            self.button_aforward.on_clicked(self.anim_forward)

    def reset_buttons(self):
        if self.animation_controls:
            for button in [ self.button_aback, self.button_astop, self.button_aforward ]:
                button.color = self.animcolor
            self.refesh()

    def refesh(self):
        self.axes.figure.canvas.draw()

    def start(self):
        self.event_source.start()

    def _update(self, event):
        super(PageSlider, self)._update(event)
        i = int(self.val)
        if i >=self.valmax: return
        self._colorize(i)

    def _colorize(self, i):
        for j in range(self.numpages):
            self.pageRects[j].set_facecolor(self.facecolor)
        self.pageRects[i].set_facecolor(self.activecolor)

    def step( self, event=None ):
        if   self.anim_state == ADirection.FORWARD:  self.forward(event)
        elif self.anim_state == ADirection.BACKWARD: self.backward(event)

    def forward(self, event=None):
        current_i = int(self.val)
        i = current_i+1
        if i >= self.valmax: i = self.valmin
        self.set_val(i)
        self._colorize(i)

    def backward(self, event=None):
        current_i = int(self.val)
        i = current_i-1
        if i < self.valmin: i = self.valmax -1
        self.set_val(i)
        self._colorize(i)

    def step_forward(self, event=None):
        self.anim_stop()
        self.forward(event)

    def step_backward(self, event=None):
        self.anim_stop()
        self.backward(event)

    def anim_forward(self, event=None):
        if self.anim_state == ADirection.FORWARD:
            self.anim_delay = self.anim_delay / self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        elif self.anim_state == ADirection.BACKWARD:
            self.anim_delay = self.anim_delay * self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        else:
            self.anim_delay = self.init_anim_delay
            self.anim_state = ADirection.FORWARD
            self.event_source.activate( self.anim_delay )
            self.button_aforward.color = self.on_animcolor
            self.refesh()

    def anim_backward(self, event=None):
        if self.anim_state == ADirection.FORWARD:
            self.anim_delay = self.anim_delay * self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        elif self.anim_state == ADirection.BACKWARD:
            self.anim_delay = self.anim_delay / self.anim_delay_multiplier
            self.event_source.interval = self.anim_delay
        else:
            self.anim_delay = self.init_anim_delay
            self.anim_state = ADirection.BACKWARD
            self.event_source.activate( self.anim_delay )
            self.button_aback.color = self.on_animcolor
            self.refesh()

    def anim_stop(self, event=None):
        if self.anim_state != ADirection.STOP:
            self.anim_delay = self.init_anim_delay
            self.anim_state = ADirection.STOP
            self.event_source.deactivate()
            self.reset_buttons()

class LabelingConsole:

    def __init__(self, umgr: UMAPManager, **kwargs ):   # class_labels: [ [label, RGBA] ... ]
        self._debug = False
        self.point_selection = []
        self.label_map: xa.DataArray = None
        self.flow = ActivationFlow(**kwargs)
        self.umgr = umgr
        block_index = umgr.tile.dm.config.getShape( 'block_index' )
        self.setBlock( kwargs.pop( 'block', block_index ) )
        self.global_bounds: Bbox = None
        self.global_crange = None
        self.plot_axes: Axes = None
        self.figure: Figure = kwargs.pop( 'figure', None )
        if self.figure is None:
            self.figure = plt.figure()
        self.image: AxesImage = None
        self.blinker = EventSource( self.blink )
        self.blink_state = True
        self.labels_image: AxesImage = None
        self.flow_iterations = kwargs.get( 'flow_iterations', 5 )
        self.training_points: PathCollection = None
        self.frame_marker: Line2D = None
        self.control_axes = {}
        self.setup_plot(**kwargs)
        self.dataLims = {}
        self.band_axis = kwargs.pop('band', 0)
        self.z_axis_name = self.data.dims[ self.band_axis]
        self.x_axis = kwargs.pop( 'x', 2 )
        self.x_axis_name = self.data.dims[ self.x_axis ]
        self.y_axis = kwargs.pop( 'y', 1 )
        self.y_axis_name = self.data.dims[ self.y_axis ]
        self.nFrames = self.data.shape[0]
        self.training_data = []
        self.currentFrame = 0
        self.currentClass = 0
        self.button_actions =  OrderedDict( submit=self.submit_training_set, undo=self.undo_point_selection, clear=self.clearLabels, remodel=self.remodel )

        self.add_plots( **kwargs )
        self.add_slider( **kwargs )
        self.add_selection_controls( **kwargs )
        atexit.register(self.exit)
        self._update(0)

    @property
    def toolbar(self):
        return self.figure.canvas.toolbar

    @property
    def tile(self):
        return self.umgr.tile

    def setBlock( self, block_coords: Tuple[int], **kwargs ):
        self.block: Block = self.tile.getBlock( *block_coords )
        self.transform = ProjectiveTransform( np.array( list(self.block.data.transform) + [0, 0, 1] ).reshape(3, 3) )
        self.flow.setNodeData( self.block.getPointData() )
        self.read_training_data()
        self.clearLabels()
        labels: xa.DataArray = self.getLabeledPointData()
        use_tasks = kwargs.get( 'use_tasks', False )
        if use_tasks:
            taskRunner.start( self.init_pointcloud, self.flow.nnd, labels, block=self.block, **kwargs )     # This doesn't work so currently disabled
        else:
            from hyperclass.gui.tasks import Task
            self.init_pointcloud( self.flow.nnd, labels, block = self.block, **kwargs )
            Task.mainWindow().update( )

    def init_pointcloud( self, nnd: NNDescent, labels: xa.DataArray = None, **kwargs  ):
        self.umgr.fit( nnd, labels, **kwargs )
        self.umgr.init_pointcloud( self.getLabeledPointData().values )
        self.plot_markers()

    def remodel( self, **kwargs  ):
        print("Rebuilding model")
        labels: xa.DataArray = self.getExtendedLabelPoints()
        self.umgr.fit( self.flow.nnd, labels, block=self.block )
#        self.umgr.color_pointcloud( labels )
        time.sleep(0.2)
        self.plot_markers()

    def clearLabels( self, event = None ):
        nodata_value = -2
        template = self.block.data[0].squeeze( drop=True )
        self.labels: xa.DataArray = xa.full_like( template, -1, dtype=np.int16 ).where( template.notnull(), nodata_value )
        self.labels.attrs['_FillValue'] = nodata_value
        self.labels.name = self.block.data.name + "_labels"
        self.labels.attrs[ 'long_name' ] = [ "labels" ]

    def updateLabels(self):
        print( f"Updating {len(self.point_selection)} labels")
        for ( cy, cx, c ) in self.point_selection:
            iy, ix = self.block.coord2index(cy, cx)
            try:
                self.labels[ iy, ix ] = c
            except:
                print( f"Skipping out of bounds label at local row/col coords {iy} {ix}")

    def getLabeledPointData( self, update = True ) -> xa.DataArray:
        if update: self.updateLabels()
        labeledPointData = self.tile.dm.raster2points( self.labels )
        return labeledPointData

    def getExtendedLabelPoints( self ) -> xa.DataArray:
        if self.label_map is None: return self.getLabeledPointData( True )
        return self.tile.dm.raster2points( self.label_map )

    @property
    def data(self):
        return self.block.data

    @property
    def class_labels(self):
        return self.umgr.class_labels

    @property
    def class_colors(self):
        return self.umgr.class_colors

    @property
    def toolbarMode(self) -> str:
        return self.toolbar.mode

    @classmethod
    def time_merge( cls, data_arrays: List[xa.DataArray], **kwargs ) -> xa.DataArray:
        time_axis = kwargs.get('time',None)
        frame_indices = range( len(data_arrays) )
        merge_coord = pd.Index( frame_indices, name=kwargs.get("dim","time") ) if time_axis is None else time_axis
        result: xa.DataArray =  xa.concat( data_arrays, dim=merge_coord )
        return result

    def setup_plot(self, **kwargs):
        self.plot_grid: GridSpec = self.figure.add_gridspec( 4, 4 )
        self.plot_axes = self.figure.add_subplot( self.plot_grid[:, 0:-1] )
        for iC in range(4):
            self.control_axes[iC] = self.figure.add_subplot( self.plot_grid[iC, -1] )
            self.control_axes[iC].xaxis.set_major_locator(plt.NullLocator())
            self.control_axes[iC].yaxis.set_major_locator(plt.NullLocator())
        self.slider_axes: Axes = self.figure.add_axes([0.1, 0.01, 0.8, 0.04])  # [left, bottom, width, height]
        self.plot_grid.update( left = 0.05, bottom = 0.1, top = 0.95, right = 0.95 )

    def invert_yaxis(self):
        self.plot_axes.invert_yaxis()

    def get_xy_coords(self,  ) -> Tuple[ np.ndarray, np.ndarray ]:
        return self.get_coord(self.x_axis ), self.get_coord( self.y_axis )

    def get_anim_coord(self ) -> np.ndarray:
        return self.get_coord( 0 )

    def get_coord(self,   iCoord: int ) -> np.ndarray:
        return self.data.coords[  self.data.dims[iCoord] ].values

    def create_image(self, **kwargs ) -> AxesImage:
        z: xa.DataArray =  self.data[ 0, :, : ]
        colorbar = kwargs.pop( 'colorbar', False )
        image: AxesImage =  self.tile.dm.plotRaster( z, ax=self.plot_axes, colorbar=colorbar, alpha=0.5, colorstretch=1.0, **kwargs )
        self._cidpress = image.figure.canvas.mpl_connect('button_press_event', self.onMouseClick)
        self._cidrelease = image.figure.canvas.mpl_connect('button_release_event', self.onMouseRelease )
        self.plot_axes.callbacks.connect('ylim_changed', self.on_lims_change)
        overlays = kwargs.get( "overlays", {} )
        for color, overlay in overlays.items():
            overlay.plot( ax=self.plot_axes, color=color, linewidth=2 )
        return image

    def on_lims_change(self, ax ):
         if ax == self.plot_axes:
             (x0, x1) = ax.get_xlim()
             (y0, y1) = ax.get_ylim()
             print(f"ZOOM Event: Updated bounds: ({x0},{x1}), ({y0},{y1})")

    def update_plots(self ):
        frame_data = self.data[ self.currentFrame]
        self.image.set_data( frame_data  )
        self.plot_axes.title.set_text(f"{self.data.name}: Band {self.currentFrame+1}" )
        self.plot_axes.title.set_fontsize( 8 )

    def onMouseRelease(self, event):
        pass
        # if event.inaxes ==  self.plot_axes:
        #     for action in self.toolbar._actions.values():
        #         action.setChecked( False )

    def onMouseClick(self, event):
        if event.xdata != None and event.ydata != None:
            if not self.toolbarMode:
                if event.inaxes ==  self.plot_axes:
                    self.add_point_selection( event )
                    self.dataLims = event.inaxes.dataLim

    def add_point_selection(self, event ):
        point = [ event.ydata, event.xdata, self.selectedClass ]
        self.point_selection.append( point )
        self.plot_points()
        taskRunner.start( self.plot_marker, *point )

    def plot_marker(self, y: float, x: float, c: int = None, **kwargs ):
        try:
            self.umgr.plot_marker( y, x, self.get_color(c), **kwargs )
        except IndexError:
            print( f"Skipping out-of-bounds label: [ {x} {y} ]")

    def undo_point_selection(self, event ):
        self.point_selection.pop()
        self.plot_points()

    def submit_training_set(self, event ):
        print( "Submitting training set" )
        self.blinker.stop()
        self.show_labels()
        labels: xa.DataArray = self.getLabeledPointData()
        new_labels: xa.DataArray = self.flow.spread( labels, self.flow_iterations  )
        self.plot_label_map( new_labels )
        self.show_labels()
        self.blinker.start(1.0,6.0)

    def plot_label_map(self, sample_labels: xa.DataArray, **kwargs ):
        self.label_map: xa.DataArray =  sample_labels.unstack().transpose().astype(np.int16)
        self.label_map = self.label_map.where( self.label_map >= 0, 0 )
        print( f" plot_label_map: label bincounts = {np.bincount( self.label_map.values.flatten() )}")
        class_alpha = kwargs.get( 'alpha', 0.5 )
        if self.labels_image is None:
            label_map_colors: List = [ [ ic, label, color[0:3] + [class_alpha] ] for ic, (label, color) in enumerate(self.class_colors.items()) ]
            self.labels_image = self.tile.dm.plotRaster( self.label_map, colors=label_map_colors, ax=self.plot_axes, colorbar=False )
        else:
            self.labels_image.set_data( self.label_map.values  )
        taskRunner.start(self.color_pointcloud, sample_labels )

    def show_labels(self):
        if self.labels_image is not None:
            self.labels_image.set_alpha(1.0)
            self.update_canvas()

    def color_pointcloud(self, sample_labels: xa.DataArray, **kwargs ):
        self.umgr.color_pointcloud( sample_labels, **kwargs )

    def blink( self ):
        self.blink_state = not self.blink_state
        self.labels_image.set_alpha( float(self.blink_state) )
        self.figure.canvas.draw_idle()

    def toggle_blinking_layer(self, blinking_on: bool ):
        if blinking_on:
            self.blinker.start(1.0)
        else:
            self.blinker.stop()
            if self.labels_image is not None:
                self.labels_image.set_alpha( 1.0 )

    def get_color(self, class_index: int = None ):
        if class_index is None: class_index = self.selectedClass
        return self.class_colors[self.class_labels[ class_index ]]

    def plot_points(self ):
        if self.point_selection:
            xcoords = [ ps[1] for ps in self.point_selection ]
            ycoords = [ ps[0] for ps in self.point_selection ]
            cvals   = [ ps[2] for ps in self.point_selection ]
            colors = [ self.get_color(ic) for ic in cvals ]
            self.training_points.set_offsets(np.c_[ xcoords, ycoords ] )
            self.training_points.set_facecolor( colors )
            self.update_canvas()

    def plot_markers(self):
        for psel in self.point_selection:
#            taskRunner.start(self.plot_marker, *psel)
            self.plot_marker( *psel )

    def update_canvas(self):
        self.figure.canvas.draw_idle()
        plt.pause(0.01)

    def read_training_data(self):
        self.tile.dm.tdio.readLabelData()
        if self.tile.dm.tdio.hasData:
            self.point_selection = self.tile.dm.tdio.values
            self.umgr.class_labels: List[str] = self.tile.dm.tdio.names
            self.umgr.class_colors: OrderedDict[str,Tuple[float]] = self.tile.dm.tdio.colors
            print( f"Reading {len(self.point_selection)} point labels from file { self.tile.dm.tdio.file_path}")

    def write_training_data(self):
        print( f"Writing {len(self.point_selection)} point labels ot file {self.tile.dm.tdio.file_path}")
        self.tile.dm.tdio.writeLabelData( self.class_labels, self.class_colors, self.point_selection )

    def datalims_changed(self ) -> bool:
        previous_datalims: Bbox = self.dataLims
        new_datalims: Bbox = self.plot_axes.dataLim
        return previous_datalims.bounds != new_datalims.bounds

    def add_plots(self, **kwargs ):
        self.image = self.create_image(**kwargs)
        self.training_points = self.plot_axes.scatter( [],[], s=50, zorder=2, alpha=1 )
        self.training_points.set_edgecolor( [0,0,0] )
        self.training_points.set_linewidth( 2 )
        self.plot_points()

    def add_slider(self,  **kwargs ):
        self.slider = PageSlider( self.slider_axes, self.nFrames )
        self.slider_cid = self.slider.on_changed(self._update)

    def add_selection_controls( self, controls_window=0 ):
        cax = self.control_axes[controls_window]
        cax.title.set_text('Class Selection')
        self.class_selector = ColoredRadioButtons( cax, self.class_labels, list(self.class_colors.values()), active=self.currentClass )

    def add_button_box( self, buttons_window=1, **kwargs ):
        cax = self.control_axes[ buttons_window ]
        cax.title.set_text('Actions')
        actions = [ "Submit", "Undo", "Clear" ]
        self.button_box = ButtonBox( cax, [3,3], actions )
        self.button_box.addCallback( actions[0], self.submit_training_set )
        self.button_box.addCallback( actions[1], self.undo_point_selection )
        self.button_box.addCallback( actions[2], self.clearLabels )


    def wait_for_key_press(self):
        keyboardClick = False
        while keyboardClick != True:
            keyboardClick = plt.waitforbuttonpress()

    @property
    def selectedClass(self) -> int:
        return self.class_labels.index( self.class_selector.value_selected )

    @property
    def selectedClassLabel(self) -> str:
        return self.class_selector.value_selected

    def _update( self, val ):
        tval = self.slider.val
        self.currentFrame = int( tval )
        self.update_plots()

    def show(self):
        self.slider.start()
        plt.show()

    def start(self):
        self.slider.start()

    def __del__(self):
        self.exit()

    def exit(self):
        self.blinker.exit()
        self.write_training_data()

