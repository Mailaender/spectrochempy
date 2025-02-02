# -*- coding: utf-8 -*-
# flake8: noqa
# ======================================================================================================================
#  Copyright (©) 2015-2020 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.                                  =
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory                         =
# ======================================================================================================================

"""
NDDataset baseline correction
==============================

In this example, we perform a baseline correction of a 2D NDDataset
interactively, using the ``multivariate`` method and a ``pchip`` interpolation.

"""

###############################################################################
# As usual we start by importing the useful library, and at least  the
# spectrochempy library.

import spectrochempy as scp

###############################################################################
# Load data:

nd = scp.NDDataset.read_omnic("irdata/nh4y-activation.spg")

###############################################################################
# Do some slicing to keep only the interesting region:

ndp = (nd - nd[-1])[:, 1291.0:5999.0]
# Important:  notice that we use floating point number
# integer would mean points, not wavenumbers!

###############################################################################
# Define the BaselineCorrection object:

ibc = scp.BaselineCorrection(ndp)

###############################################################################
# Launch the interactive view, using the `BaselineCorrection.run` method:

ranges = [
    [1556.30, 1568.26],
    [1795.00, 1956.75],
    [3766.03, 3915.81],
    [4574.26, 4616.04],
    [4980.10, 4998.01],
    [5437.52, 5994.70],
]  # predefined ranges
span = ibc.run(
    *ranges, method="multivariate", interpolation="pchip", npc=5, zoompreview=3
)

###############################################################################
# Print the corrected dataset:

print(ibc.corrected)
_ = ibc.corrected.plot()
# scp.show()  # uncomment to show plot if needed (not necessary in jupyter notebook)

""
