# -*- coding: utf-8 -*-
#
# ======================================================================================================================
# Copyright (©) 2015-2019 LCS
# Laboratoire Catalyse et Spectrochimie, Caen, France.
# CeCILL-B FREE SOFTWARE LICENSE AGREEMENT
# See full LICENSE agreement in the root directory
# ======================================================================================================================

import os
import numpy as np

from spectrochempy.core.dataset.nddataset import NDDataset
from spectrochempy.core.analysis.efa import EFA
from spectrochempy.core.analysis.mcrals import MCRALS
from spectrochempy.utils import show, info_

def test_MCRALS_no_coords():
    print('')
    data = NDDataset.read_matlab(os.path.join('matlabdata','als2004dataset.MAT'))
    print('Dataset (Jaumot et al., Chemometr. Intell. Lab. 76 (2005) 101-110)):')
    print('')
    for mat in data:
        print('    ' + mat.name, str(mat.shape))

    print('\n test on single experiment (m1) with given estimate of pure species (spure)...\n')

    X = data[0]
    guess = data[1]
    mcr  = MCRALS(X, guess, verbose=True)
    [C, St] = mcr.transform()


    C.T.plot()
    St.plot()
    mcr.plot()

    print('\n test on single experiment (m1) with EFA estimate of pure species (verbose off)...\n')
    guess = EFA(X).get_conc(4, plot=False)

    param = {'normSpec':'euclid', 'maxit':100}
    mcr2 = MCRALS(X, guess, param=param, verbose=False)
    mcr2.plot()

    assert 'converged !' in mcr2._log[-15:]


def test_MCRALS():

    data = NDDataset.read_matlab(os.path.join('matlabdata','als2004dataset.MAT'), transposed=True)
    info_('\nDataset (Jaumot et al., Chemometr. Intell. Lab. 76 (2005) 101-110)):\n')

    for mat in data:
        info_('    ',mat.name, mat.shape)

    info_('\n test on single experiment (m1) with estimate of pure species (spure)...\n')

    X = data[0]  # m1
    X.coords = [np.arange(51), np.arange(96)]
    X.title = 'concentration'
    X.coords.titles = ['spec coord.', 'elution time']
    info_(X)
    X.plot(title='M1')

    guess = data[1] # spure
    guess.coords = [np.arange(4), np.arange(96)]
    guess.title = 'concentration'
    guess.coords.titles = ['#components', 'elution time']
    guess.plot(title='spure')

    mcr  = MCRALS(X, guess, verbose=True)
    [C, St] = mcr.transform()

    C.T.plot(title= 'Concentration')

    St.plot(title='spectra')

    mcr.plot()

    info_('\n test on single experiment (m1) with EFA estimate of pure species (verbose off)...\n')
    guess = EFA(X).get_conc(4, plot=False)
    guess.plot(title='EFA guess')

    param = {'normSpec':'euclid', 'maxit':100}
    mcr2 = MCRALS(X, guess, param=param, verbose=False)
    mcr2.plot()

    assert 'converged !' in mcr2._log[-15:]

    show()

# =============================================================================
if __name__ == '__main__':
    pass