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

    def fit( self, X: np.ndarray, y: np.ndarray, **kwargs ):
        t0 = time.time()
        print(f"Running SVC fit, X shape: {X.shape}), y shape: {y.shape})")
        self.svc.fit( X, y )
        self._score = self.decision_function(X)
        print(f"Completed SVC fit, in {time.time()-t0} secs")

#        self._support_vector_indices = np.where( (2 * y - 1) * self._score <= 1 )[0]    # For binary classifier
#        self._support_vectors = X[ self.support_vector_indices ]

    def predict( self, X: np.ndarray, **kwargs ) -> np.ndarray:
        return self.svc.predict( X ).astype( int )

    @property
    def decision_function(self) -> Callable:
        return self.svc.decision_function

svcLearningModel = SCVLearningModel()


