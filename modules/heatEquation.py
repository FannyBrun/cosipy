import numpy as np
from numpy.distutils.command.install_clib import install_clib
import logging

from scipy import sparse
from scipy.sparse.linalg import spsolve

from constants import *
from config import *

import sys

def solveHeatEquation(GRID, t):
    """ Solves the heat equation on a non-uniform grid using

    dt  ::  integration time
    
    """
    # start module logging
    logger = logging.getLogger(__name__)

    nl = GRID.get_number_layers()

    # Calculate thermal conductivity [W m-1 K-1] from mean density
    #lam = 0.021 + 2.5 * (np.asarray(GRID.get_density())/1000.0)**2.0

    # Calculate thermal diffusivity [m2 s-1]
    K = np.asarray(GRID.get_thermal_diffusivity()) 
    #hm = np.asarray(GRID.get_height()[0:nl-2])+np.asarray(GRID.get_height()[1:nl-1])+np.asarray(GRID.get_height()[2:nl])
    #Km = (GRID.get_height()[0:nl-2]*K[0:nl-2]+GRID.get_height()[1:nl-1]*K[1:nl-1]+GRID.get_height()[2:nl]*K[2:nl])/hm
    
    # Get snow layer heights    
    hlayers = np.asarray(GRID.get_height())

    # Get grid spacing
    diff = ((hlayers[0:nl-1]/2.0)+(hlayers[1:nl]/2.0))
    hk = diff[0:nl-2] 
    hk1 = diff[1:nl-1]

    # Introduce C for matrix
    C1 = np.zeros(nl-1)
    C2 = np.ones(nl)
    C3 = np.zeros(nl-1)

    # Derive diagonals 
    C1[0:nl-2] = -(2*K[1:nl-1]*t)/(hk*(hk+hk1))
    C2[1:nl-1] = 1+(2*K[1:nl-1]*t)/(hk*hk1)
    C3[1:nl-1] = -(2*K[1:nl-1]*t)/(hk1*(hk+hk1))
    
    # Create tridiagonal matrix
    A = sparse.diags([C1, C2, C3], [-1,0,1], format='csc')
   
    # Initial vector
    b = np.asarray(GRID.get_temperature())

    # Solve equation
    x = spsolve(A,b)



    
