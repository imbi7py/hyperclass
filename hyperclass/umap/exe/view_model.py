from typing import List, Union, Tuple, Optional
from hyperclass.data.aviris.manager import DataManager, Block, Tile
from hyperclass.umap.manager import UMAPManager
import os, math

# Fit UMAP-transform a block of data and view the embedding

if __name__ == '__main__':
    image_name = "ang20170720t004130_corr_v2p9"
    block_index = [0,0]
    color_band = 35

    dm = DataManager( image_name )
    tile: Tile = dm.getTile()
    umgr =  UMAPManager( tile )
    block: Block = tile.getBlock(*block_index)
    umgr.view_model( block = block, color_band=color_band )



