from pynndescent import NNDescent
import xarray as xa
import numpy as np
import numpy.ma as ma
from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Tile, Block
from hyperclass.umap.manager import UMAPManager
from hyperclass.plot.points import datashade_points, point_cloud_3d
import plotly.graph_objs as go
import os, time

# Fit compute NN graph over block

if __name__ == '__main__':
    image_name = "ang20170720t004130_corr_v2p9"
    n_neighbors = 10
    subsample = 100

    t0 = time.time()
    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr = UMAPManager (tile )
    block: Block = tile.getBlock( 0,0 )
    graph_nodes = block.getPointData( subsample = subsample )
    t1 = time.time()
    print(f"Completed loading data in {(t1 - t0)} sec from tile {tile.name}")

    n_trees = 5 + int(round((graph_nodes.shape[0]) ** 0.5 / 20.0))
    n_iters = max(5, int(round(np.log2(graph_nodes.shape[0]))))
    nnd = NNDescent( graph_nodes, n_trees=n_trees, n_iters=n_iters, n_jobs = -1, n_neighbors=n_neighbors, max_candidates=60, verbose=True )
    I: np.ndarray = nnd.neighbor_graph[0]
    D: np.ndarray = nnd.neighbor_graph[1]
    t2 = time.time()
    print(f"Completed computing graph in {(t2 - t1)} sec, index shape = {I.shape}, dist shape = {D.shape}")

    test_labels = ma.masked_equal( np.full( graph_nodes.shape[:1], -1 ), -1 )
    P: ma.MaskedArray  = ma.masked_invalid( np.full( graph_nodes.shape[:1], float("nan") ) )

    for iL in range(3):
        index = iL*100
        test_labels[index] = iL
        P[index] = 0.0

    PN0: np.ndarray  = P[ I.flatten() ]
    PN: np.ndarray = PN0.reshape( I.shape ) + D
    best_neighbors: ma.MaskedArray = ma.argmin( PN, axis=1 )
# #    I = xa.DataArray( knn_indices, dims=['samples', 'neighbors'], coords = dict( samples = graph_nodes.coords['samples'], neighbors=np.arange(knn_indices.shape[1]) ) )
# #    D = xa.DataArray( knn_dists,   dims=['samples', 'neighbors'], coords = dict( samples = graph_nodes.coords['samples'], neighbors=np.arange(knn_indices.shape[1])))
#     test_labels =  xa.full_like( graph_nodes[:,0], float("nan") )
#     P = xa.full_like( test_labels, float("nan") )
#     for iL in range(3):
#         index = iL*100
#         test_labels[index] = iL
#         P[index] = 0.0
# 
#     PN = P[ knn_indices.flatten() ].res

    print( ". " )




