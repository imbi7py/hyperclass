import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional
from hyperclass.plot.points import datashade_points, point_cloud_3d
from hyperclass.umap.manager import UMAPManager
import os, math

# plot a UMAP embedding


if __name__ == '__main__':
    c0 = (1000,1000)
    c1 = (2000,2000)
    subsampling = 10
    ndims = 3
    color_band = 200
    n_neighbors = 30
    file_name = "ang20170720t004130_corr_v2p9"

    mgr = UMAPManager()
    map_file = os.path.join( mgr.dm.config['output_dir'], f"umap-model.ang20170720t004130.{c0[0]}-{c1[1]}_{c1[0]}-{c1[1]}.s-{subsampling}.d-{ndims}.nn-{n_neighbors}.pkl" )
    raster: xa.DataArray = mgr.dm.read_subtile( file_name, c0, c1 )
    color_data: np.ndarray = mgr.dm.restructure_band( raster[color_band] ).values

    t0 = time.time()
    mapper: umap.UMAP = pickle.load( open( map_file, "rb" ) )
    t1 = time.time()
    print( f"Completed map load in {(t1-t0)} sec, Now transforming data")

    restructured_data = mgr.dm.restructure_for_training( raster )

    t2 = time.time()
    mapped_data: np.ndarray = mapper.transform( restructured_data.values )
    t3 = time.time()
    print(f"Completed umap transform of {restructured_data.shape[0]} samples in {(t3 - t2)} sec")

    t4 = time.time()
    print(f"Plotting model data with shape  {mapped_data.shape}, color data shape = {color_data.shape}")
    mgr.view_model( mapped_data, color_data, [-4,10] )
    t5 = time.time()
    print(f"Completed plot in {(t3 - t2)} sec")




