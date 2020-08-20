from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from typing import List, Union, Dict, Callable, Tuple, Optional
from sklearn.svm import LinearSVC
import xarray as xa
import time, traceback
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from hyperclass.gui.events import EventClient, EventMode
from typing import List, Tuple, Optional, Dict
from hyperclass.gui.tasks import taskRunner, Task
import numpy as np
from hyperclass.learn.manager import LearningModel

class SCVLearningModel(LearningModel):

    def __init__(self, **kwargs ):
        LearningModel.__init__(self, "svc",  **kwargs )
        self._score: Optional[np.ndarray] = None
        norm = kwargs.get( 'norm', True )
        tol = kwargs.pop( 'tol', 1e-5 )
        if norm: self.svc = make_pipeline( StandardScaler(), LinearSVC( tol=tol, dual=False, fit_intercept=False, **kwargs ) )
        else:    self.svc = LinearSVC(tol=tol, dual=False, fit_intercept=False, **kwargs)

    def learn_classification( self, data: xa.DataArray, labels: xa.DataArray, **kwargs  ):
        t1 = time.time()
        labels_mask = (labels > 0)
        filtered_labels: np.ndarray = labels.where(labels_mask, drop=True).values
        filtered_point_data: np.ndarray = data.where(labels_mask, drop=True).values
        print(f"Learning mapping with {filtered_labels.shape[0]} labels.")
        score = self.fit( filtered_point_data, filtered_labels, **kwargs )
        if score is not None:
            print(f"Fit SVC model (score shape: {score.shape}) in {time.time() - t1} sec")

    def apply_classification( self, data: xa.DataArray, **kwargs ):
        prediction: np.ndarray = self.predict( data.values, **kwargs )
        return xa.DataArray( prediction, dims=['samples'], coords=dict( samples=data.coords['samples'] ) )

    def fit( self, X: np.ndarray, y: np.ndarray, **kwargs ) -> Optional[np.ndarray]:
        t0 = time.time()
        if np.count_nonzero( y > 0 ) == 0:
            Task.taskNotAvailable( "Workflow violation", "Must spread some labels before learning the classification", **kwargs )
            return None
        print(f"Running SVC fit, X shape: {X.shape}), y shape: {y.shape})")
        self.svc.fit( X, y )
        self._score = self.decision_function(X)
        print(f"Completed SVC fit, in {time.time()-t0} secs")
        return self._score

#        self._support_vector_indices = np.where( (2 * y - 1) * self._score <= 1 )[0]    # For binary classifier
#        self._support_vectors = X[ self.support_vector_indices ]

    def predict( self, X: np.ndarray, **kwargs ) -> np.ndarray:
        print(f"Running SVC predict, X shape: {X.shape})")
        return self.svc.predict( X ).astype( int )

    @property
    def decision_function(self) -> Callable:
        return self.svc.decision_function

svcLearningModel = SCVLearningModel()


