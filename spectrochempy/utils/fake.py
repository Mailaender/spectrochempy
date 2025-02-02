# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.                                  =
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory                         =
# ======================================================================================================================
"""
Fake data for testing

This module implements routines to generate fake data that can be used for
testing our various |scpy| analysis methods
"""
__all__ = ["generate_fake"]

import numpy as np


def _make_spectra_matrix(pos, width, ampl):
    from spectrochempy.core.dataset.coord import Coord
    from spectrochempy.core.dataset.nddataset import NDDataset
    from spectrochempy.core.fitting.models import gaussianmodel

    x = Coord(np.linspace(6000.0, 1000.0, 4000), units="cm^-1", title="wavenumbers")
    s = []
    for args in zip(ampl, width, pos):
        s.append(gaussianmodel().f(x.data, *args))

    st = np.vstack(s)
    st = NDDataset(
        data=st, units="absorbance", title="absorbance", coordset=[range(len(st)), x]
    )

    return st


def _make_concentrations_matrix(*profiles):
    from spectrochempy.core.dataset.coord import Coord
    from spectrochempy.core.dataset.nddataset import NDDataset

    t = Coord(np.linspace(0, 10, 50), units="hour", title="time")
    c = []
    for p in profiles:
        c.append(p(t.data))
    ct = np.vstack(c)
    ct = ct - ct.min()
    ct = ct / np.sum(ct, axis=0)
    ct = NDDataset(data=ct, title="concentration", coordset=[range(len(ct)), t])

    return ct


def _generate_2D_spectra(concentrations, spectra):
    """
    Generate a fake 2D experimental spectra

    Parameters
    ----------
    concentrations : |NDDataset|
    spectra : |NDDataset|

    Returns
    -------
    |NDDataset|
    """
    from spectrochempy.core.dataset.npy import dot

    return dot(concentrations.T, spectra)


def generate_fake():
    from spectrochempy.utils import show

    # define properties of the spectra and concentration profiles
    # ----------------------------------------------------------------------------------------------------------------------

    POS = (6000.0, 4000.0, 2000.0, 2500.0)
    WIDTH = (6000.0, 1000.0, 600.0, 800.0)
    AMPL = (100.0, 100.0, 20.0, 50.0)

    def C1(t):
        return t * 0.05 + 0.01  # linear evolution of the baseline

    def C2(t):
        return np.exp(-t / 0.5) * 0.3 + 0.1

    def C3(t):
        return np.exp(-t / 3.0) * 0.7

    def C4(t):
        return 1.0 - C2(t) - C3(t)

    spec = _make_spectra_matrix(POS, WIDTH, AMPL)
    spec.plot_stack(colorbar=False)

    conc = _make_concentrations_matrix(C1, C2, C3, C4)
    conc.plot_stack(colorbar=False)

    d = _generate_2D_spectra(conc, spec)
    # add some noise
    d.data = np.random.normal(d.data, 0.007 * d.data.max())

    d.plot_stack()

    show()

    d.save("test_full2D")
    spec.save("test_spectra")
    conc.save("test_concentration")


# ======================================================================================================================
if __name__ == "__main__":
    pass
