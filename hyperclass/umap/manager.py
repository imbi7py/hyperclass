import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional, Dict
from hyperclass.plot.points import datashade_points, point_cloud_3d
from hyperclass.data.aviris.manager import DataManager, Tile, Block
import os, math
cfg_str = lambda x:  "-".join( [ str(i) for i in x ] )

class UMAPManager:

    def __init__(self, tile: Tile, **kwargs ):
        self.tile = tile
        self.refresh = kwargs.pop('refresh', False)
        self.conf = kwargs
        self.mapper_file_path = self._mapperFilePath()
        self._getMapper()

    def _getMapper(self):
        if self.refresh and os.path.isfile(self.mapper_file_path):
            print( f"Removing older version of mapper at {self.mapper_file_path}")
            os.remove(self.mapper_file_path)
        self.mapper = self._loadMapper()
        if self.mapper is None:
            parms = self.tile.dm.config.section("umap").toDict()
            self.mapper = umap.UMAP(**parms)
            self._fit()

    def _mapperFilePath( self ) -> str:
        path_cfg = self.tile.dm.config.toStr( ['tiles','umap'] )
        file_name = f"umap.{self.tile.dm.image_name}.{path_cfg}.pkl"
        return os.path.join( self.tile.dm.config['output_dir'], file_name )

    def _loadMapper(self) -> Optional[umap.UMAP]:
        mapper: umap.UMAP = None

        if os.path.isfile( self.mapper_file_path ):
            t0 = time.time()
            mapper = pickle.load( open( self.mapper_file_path, "rb" ) )
            t1 = time.time()
            print( f"Completed loading UMAP in {(t1-t0)} sec from file {self.mapper_file_path}.")
        return mapper

    def iparm(self, key: str ):
        return int( self.tile.dm.config[key] )

    def _fit( self ):
        t0 = time.time()

        training_data: xa.DataArray = self.tile.getPointData(  )
        t1 = time.time()
        print(f"Completed data prep in {(t1 - t0)} sec, Now fitting umap to {self.iparm('n_components')} dims with {training_data.shape[0]} samples")
        self.mapper.fit( training_data.data )
        t2 = time.time()
        print(f"Completed umap fitting in {(t2 - t1)} sec, serializing mapper to file {self.mapper_file_path}")
        if not os.path.isfile( self.mapper_file_path ):
            pickle.dump( self.mapper, open(self.mapper_file_path, 'wb') )

    @property
    def conf_keys(self) -> List[str]:
        key_list = list(self.conf.keys())
        key_list.sort()
        return key_list

    def view_model( self, **kwargs ):
        color_band = kwargs.pop( 'color_band', None )
        reduction_axes =  kwargs.pop( 'reduction_axes', 0 )
        model_data = self.mapper.embedding_
        plot_parms = dict( cmap="jet", **kwargs )
        if color_band is not None:
            plot_parms['values'] = self.tile.getBandPointData( color_band  )
        if model_data.shape[1] == 2:
            datashade_points( model_data, **plot_parms )
        elif model_data.shape[1] == 3:
            point_cloud_3d( model_data, **plot_parms )
        else:
            xmodel_data = xa.DataArray( model_data, dims=["samples","band"], coords=dict(samples=range(model_data.shape[0]),band=range(model_data.shape[1])))
            point_cloud_3d( xmodel_data.drop_sel(band=reduction_axes).values, **plot_parms )


    def transform( self, block: Block, **kwargs ) -> Dict[str,xa.DataArray]:
        t0 = time.time()
        plot = kwargs.get( 'plot', False )
        point_data: xa.DataArray = block.getPointData()
        transformed_data: np.ndarray = self.mapper.transform( point_data )
        t1 = time.time()
        print(f"Completed transform in {(t1 - t0)} sec for {point_data.shape[0]} samples")
        block_model = xa.DataArray( transformed_data, dims=['samples', 'model'], name=self.tile.data.name, attrs=self.tile.data.attrs,
                                    coords=dict( samples=point_data.coords['samples'], model=np.arange(0,transformed_data.shape[1]) ) )
        if plot:
            color_band = kwargs.pop( 'color_band', 200 )
            color_data = point_data[:,color_band]
            self.view_transform( block_model, values=color_data, **kwargs )

        transposed_raster = block.data.stack(samples=block.data.dims[1:]).transpose()
        new_raster = block_model.reindex(samples=transposed_raster.samples).unstack()
        new_raster.attrs['long_name'] = [ f"d-{i}" for i in range( new_raster.shape[0] ) ]
        return   dict( raster=new_raster, points=block_model )

    def view_transform( self, model_data: xa.DataArray,  **kwargs ):
        plot_parms = dict( cmap="jet", **kwargs )
        if model_data.shape[1] == 2:
            datashade_points( model_data, **plot_parms )
        else:
            point_cloud_3d( model_data, **plot_parms )