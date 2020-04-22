import xarray as xa
import umap, time, pickle
import numpy as np
from typing import List, Union, Tuple, Optional
from hyperclass.plot.points import datashade_points, point_cloud_3d
import os, math

# overlay regions of a UMAP embedding in geographic space

def get_band_data( filepath: str, iband: int ) -> xa.DataArray:
    print( f"Reading data file {filepath}")
    dset: xa.Dataset =  xa.open_dataset(filepath)
    band_data: xa.DataArray = dset['band_data'][iband]
    return band_data

def get_index_data( band_data: np.ndarray, subsampling: int ) -> np.ndarray:
    indices: np.ndarray = np.extract( np.isfinite( band_data.flatten() ), np.arange(0, band_data.size) )
    return indices[::subsampling]

if __name__ == '__main__':
    c0 = (1000,1000)
    c1 = (2000,2000)
    color_band = 200
    subsampling = 5
    ndims = 3

    data_dir = "/Users/tpmaxwel/Dropbox/Tom/Data/Aviris/processed"
    output_dir = "/usr/local/web/ILAB/data/results/umap"
    data_file = os.path.join( data_dir, f"ang20170720t004130.{c0[0]}-{c0[1]}_{c1[0]}-{c1[1]}.nc" )
    mapping_file = os.path.join( output_dir, f"umap-model.ang20170720t004130.{c0[0]}-{c1[1]}_{c1[0]}-{c1[1]}.s-{subsampling}.d-{ndims}.pkl" )

    band_data: xa.DataArray = get_band_data( data_file, color_band )
    index_array = get_index_data( band_data.values,  subsampling )

    t0 = time.time()
    mapper = pickle.load( open( mapping_file, "rb" ) )
    points = np.concatenate( ( index_array.reshape(index_array.size, 1), mapper.embedding_ ),  axis = 1 )
    t1 = time.time()
    print( f"Completed map load in {(t1-t0)} sec, Now transforming data")




