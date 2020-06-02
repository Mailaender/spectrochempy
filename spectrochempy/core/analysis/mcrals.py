# -*- coding: utf-8 -*-
#
# ======================================================================================================================
# Copyright (©) 2015-2020 LCS
# Laboratoire Catalyse et Spectrochimie, Caen, France.
# CeCILL-B FREE SOFTWARE LICENSE AGREEMENT
# See full LICENSE agreement in the root directory
# ======================================================================================================================
"""
This module implements the MCRALS class.

"""

__all__ = ['MCRALS']

__dataset_methods__ = []

import numpy as np
from traitlets import HasTraits, Instance
# from collections.abc import Iterable

from spectrochempy.core.dataset.nddataset import NDDataset
from spectrochempy.core.analysis.pca import PCA
from spectrochempy.core.dataset.npy import dot
from spectrochempy.core import info_, set_loglevel, INFO


class MCRALS(HasTraits):
    """
    Performs MCR-ALS of a dataset knowing the initial C or St matrix

    """

    C = Instance(NDDataset)
    """|NDDataset| - Concentration profile of pure species"""
    St = Instance(NDDataset)
    """|NDDataset| - Spectra profile of pure species"""
    param = Instance(dict)
    """dict - Parameters of the MCS-ALS optimization"""
    log = Instance(str)
    """str - Log of the MCS-ALS iterations"""

    def __init__(self, X, guess, **kwargs):
        """
        Parameters
        ----------
        X : |NDDataset|
            The dataset on which to perform the MCR-ALS analysis
        guess : |NDDataset|
            Initial concentration or spectra
        param : dict
            Dict of optimization parameters with the following keys :

            * tol : float, optional,  default=0.1
                convergence criterion on the change of resisuals.
                (percent change of standard deviation of residuals).
            * maxit : int, optional, default=50
                maximum number of ALS minimizations.
            * maxdiv : int, optional, default=5.
                maximum number of successive non-converging iterations.
            * nonnegConc : list or tuple, default=Default [0, 1, ...] (only non-negative concentrations)
                index of species having non-negative concentration profiles. For instance [0, 2] indicates that species
                #0 and #2 have non-negative conc profiles while species #1 can have negative concentrations.
            * unimodConc : list or tuple, Default=[0, 1, ...] (only unimodal concentration profiles)
                index of species having unimodal concentrationsprofiles.
            * closureConc : list or tuple, Default=None  (no closure)
                index of species subjected to a closure constraint.
            * extConc: list or tuple, Default None (no external concentration).
                index of species for which a concentration profile is provided by an external function.
            *  getExtlConc : callable
                an external function that will provide `n_ext` concentration profiles:
                    getExtConc(C, extConc, ext_to_C_idx, *args) -> extC

                or
                    getExtConc(C, extConc, ext_to_C_idx, *args) -> (extC, out2, out3, ...)

                where C is the current concentration matrix, *args are the parameters needed to completely
                specify the function, extC is a  nadarray or NDDataset of shape (C.y, n_ext), and out1, out2, ... are
                supplementary outputs returned by the function (e.g. optimized rate parameters)
            * args : tuple, optional.
                Extra arguments passed to the external function
            * external_to_C_idx : array or tuple, Default=np.arange(next)
                indicates the correspondence between the indexes of external chemical
                profiles and the columns of the C matrix. [1, None, 0] indicates that the first external profile is the
                second pure species (index 1).
            * nonnegSpec : list or tuple, Default [1, ..., 1]  (only non-negative spectra)
                indicates species having non-negative spectra
            * unimodSpec : list or tuple, Default [0, ..., 0]  (no unimodal concentration profiles)
                indicates species having unimodal spectra
        verbose : bool
            If set to True, prints a summary of residuals and residuals change at each iteration. default = False.
            In any case, the same information is returned in self._log

        Attributes
        ----------
        self.X :
            the original dataset
        self.param :
            the parameters used to perform the MCR als
        self.extC :
            the last concentration profiles including external profiles
        self.extOutput :
            the last output of the external function used to get
        self.C :
            the final concentration profiles
        self.St :
            the final spectral profiles
        self.log :
            logs

        """

        verbose = kwargs.get('verbose', False)
        if verbose:
            set_loglevel(INFO)

        # Check initial data
        # ------------------------------------------------------------------------

        initConc, initSpec = False, False

        if type(guess) is np.ndarray:
            guess = NDDataset(guess)

        if X.shape[0] == guess.shape[0]:
            initConc = True
            C = guess.copy()
            C.name = 'Pure conc. profile, mcs-als of ' + X.name
            nspecies = C.shape[1]

        elif X.shape[1] == guess.shape[1]:
            initSpec = True
            St = guess.copy()
            St.name = 'Pure spectra profile, mcs-als of ' + X.name
            nspecies = St.shape[0]

        else:
            raise ValueError('the dimensions of initial concentration '
                             'or spectra dataset do not match the data')

        ny, nx = X.shape

        # makes a PCA with same number of species
        Xpca = PCA(X).reconstruct(n_pc=nspecies)

        # Get optional parameters in kwargs or set them to their default
        # ------------------------------------------------------------------------

        # TODO: make a preference  file to set this kwargs
        param = kwargs.get('param', dict())

        # optimization

        tol = param.get('tol', 0.1)
        maxit = param.get('maxit', 50)
        maxdiv = param.get('maxdiv', 5)

        # constraints on concentrations
        nonnegConc = param.get('nonnegConc', np.arange(nspecies))
        unimodConc = param.get('unimodConc', np.arange(nspecies))
        unimodTol = param.get('unimodTol', 1.1)
        unimodMod = param.get('unimodMod', 'strict')
        closureConc = param.get('closureConc', None)
        if closureConc is not None:
            closureTarget = param.get('closureTarget', np.ones(ny))
            closureMethod = param.get('closureMethod', 'scaling')
        monoDecConc = param.get('monoDecConc', None)
        monoDecTol = param.get('monoDecTol', 1.1)
        monoIncConc = param.get('monoIncConc', None)
        monoIncTol = param.get('monoIncTol', 1.1)
        externalConc = param.get('externalConc', None)
        if externalConc is not None:
            external_to_C_idx = param.get('external_to_C_idx', np.arange(nspecies))
        if externalConc is not None:
            try:
                getExternalConc = param.get('getExternalConc')
            except Exception:
                raise ValueError('A function must be given to get the external concentration profile(s)')
            external_to_C_idx = param.get('external_to_C_idx', externalConc)
            args = param.get('args', ())

        # constraints on spectra
        nonnegSpec = param.get('nonnegSpec', np.arange(nspecies))
        normSpec = param.get('normSpec', None)

        # TODO: add unimodal constraint on spectra

        # Compute initial spectra or concentrations   (first iteration...)
        # ------------------------------------------------------------------------

        if initConc:
            if C.coords is None:
                C.set_coords(y=X.y, x=C.x)
            St = NDDataset(np.linalg.lstsq(C.data, X.data, rcond=None)[0])
            St.name = 'Pure spectra profile, mcs-als of ' + X.name
            St.title = X.title
            cy = C.x.copy() if C.x else None
            cx = X.x.copy() if X.x else None
            St.set_coords(y=cy, x=cx)

        if initSpec:
            if St.coords is None:
                St.set_coords(y=St.y, x=X.x)
            Ct = np.linalg.lstsq(St.data.T, X.data.T, rcond=None)[0]
            C = NDDataset(Ct.T)
            C.name = 'Pure conc. profile, mcs-als of ' + X.name
            C.title = 'Concentration'
            cx = St.y.copy() if St.y else None
            cy = X.y.copy() if X.y else None
            C.set_coords(y=cy, x=cx)

        change = tol + 1
        stdev = X.std()  # .data[0]
        niter = 0
        ndiv = 0

        logs = '*** ALS optimisation log***\n'
        logs += '#iter     Error/PCA        Error/Exp      %change\n'
        logs += '---------------------------------------------------'
        info_(logs)

        while change >= tol and niter < maxit and ndiv < maxdiv:

            C.data = np.linalg.lstsq(St.data.T, X.data.T, rcond=None)[0].T
            niter += 1

            # Force non-negative concentration
            # --------------------------------
            if nonnegConc is not None:
                for s in nonnegConc:
                    C.data[:, s] = C.data[:, s].clip(min=0)

            # Force unimodal concentration
            # ----------------------------
            if unimodConc is not None:
                for s in unimodConc:
                    maxid = np.argmax(C.data[:, s])
                    curmax = C.data[maxid, s]
                    curid = maxid

                    while curid > 0:
                        curid -= 1
                        if C.data[curid, s] > curmax * unimodTol:
                            if unimodMod == 'strict':
                                C.data[curid, s] = C.data[curid + 1, s]
                            if unimodMod == 'smooth':
                                C.data[curid, s] = (C.data[curid, s] + C.data[
                                    curid + 1, s]) / 2
                                C.data[curid + 1, s] = C.data[curid, s]
                                curid = curid + 2
                        curmax = C.data[curid, s]

                    curid = maxid
                    while curid < ny - 1:
                        curid += 1
                        if C.data[curid, s] > curmax * unimodTol:
                            if unimodMod == 'strict':
                                C.data[curid, s] = C.data[curid - 1, s]
                            if unimodMod == 'smooth':
                                C.data[curid, s] = (C.data[curid, s] + C.data[
                                    curid - 1, s]) / 2
                                C.data[curid - 1, s] = C.data[curid, s]
                                curid = curid - 2
                        curmax = C.data[curid, s]

            # Force monotonic increase
            # ------------------------
            if monoIncConc is not None:
                for s in monoIncConc:
                    for curid in np.arange(ny - 1):
                        if C.data[curid + 1, s] < C.data[curid, s] / monoIncTol:
                            C.data[curid + 1, s] = C.data[curid, s]

            # Force monotonic decrease
            # ----------------------------------------------
            if monoDecConc is not None:
                for s in monoDecConc:
                    for curid in np.arange(ny - 1):
                        if C.data[curid + 1, s] > C.data[curid, s] * monoDecTol:
                            C.data[curid + 1, s] = C.data[curid, s]

            # Closure
            # ------------------------------------------
            if closureConc is not None:
                if closureMethod == 'scaling':
                    Q = np.linalg.lstsq(C.data[:, closureConc], closureTarget.T, rcond=None)[0]
                    C.data[:, closureConc] = np.dot(C.data[:, closureConc], np.diag(Q))
                elif closureMethod == 'constantSum':
                    totalConc = np.sum(C.data[:, closureConc], axis=1)
                    C.data[:, closureConc] = C.data[:, closureConc] * closureTarget[:, None] / totalConc[:, None]

            # external concentration profiles
            # ------------------------------------------
            if externalConc is not None:
                extOutput = getExternalConc(*((C, externalConc, external_to_C_idx,) + args))
                if isinstance(extOutput, dict):
                    extC = extOutput['concentrations']
                    args = extOutput['new_args']
                else:
                    extC = extOutput
                if type(extC) is NDDataset:
                    extC = extC.data
                C.data[:, externalConc] = extC[:, external_to_C_idx]

            # stores C in C_hard and recompute C for consistency (soft modeling)
            Chard = C.copy()
            C.data = np.linalg.lstsq(St.data.T, X.data.T, rcond=None)[0].T

            St.data = np.linalg.lstsq(C.data, X.data, rcond=None)[0]
            # stores St in Stsoft
            Stsoft = St.copy()

            # Force non-negative spectra
            # --------------------------
            if nonnegSpec is not None:
                St.data[nonnegSpec, :] = St.data[nonnegSpec, :].clip(min=0)

            # rescale spectra & concentrations
            if normSpec == 'max':
                alpha = np.max(St.data, axis=1).reshape(nspecies, 1)
                St.data = St.data / alpha
                C.data = C.data * alpha.T
            elif normSpec == 'euclid':
                alpha = np.linalg.norm(St.data, axis=1).reshape(nspecies, 1)
                St.data = St.data / alpha
                C.data = C.data * alpha.T

            # compute residuals
            # -----------------
            X_hat = dot(C, St)
            stdev2 = (X_hat - X.data).std()
            change = 100 * (stdev2 - stdev) / stdev

            stdev_PCA = (X_hat - Xpca.data).std()  # TODO: Check PCA : values are different from the Arnaud version ?

            logentry = '{:3d}      {:10f}      {:10f}      {:10f}'.format(niter, stdev_PCA, stdev2, change)
            logs += logentry + '\n'
            info_(logentry)
            stdev = stdev2

            if change > 0:
                ndiv += 1
            else:
                ndiv = 0
                change = -change

            if change < tol:
                logentry = 'converged !'
                logs += logentry + '\n'
                info_(logentry)

            if ndiv == maxdiv:
                logline = f"Optimization not improved since {maxdiv} iterations... unconverged " \
                          f"or 'tol' set too small ?\n"
                logline += 'Stop ALS optimization'
                logs += logline + '\n'
                info_(logline)

            if niter == maxit:
                logline = 'Convergence criterion (\'tol\') not reached after {:d} iterations.'.format(maxit)
                logline += 'Stop ALS optimization'
                logs += logline + '\n'
                info_(logline)

        self.X = X
        self.param = param
        self.Chard = Chard
        self.C = C
        if externalConc is not None:
            self.extC = extC
            self.extOutput = extOutput
        else:
            self.extC = None
            self.extOutput = None
        self.Stsoft = Stsoft
        self.St = St
        self.log = logs

    def reconstruct(self):
        """
        Transform data back to the original space.

        The following matrice operation is performed : :math:`X'_{hat} = C'.S'^t`

        Returns
        -------
        X_hat : |NDDataset|
            The reconstructed dataset based on the MCS-ALS optimization.

        """

        # reconstruct from concentration and spectra profiles
        C = self.C
        St = self.St

        X_hat = dot(C, St)

        X_hat.history = 'Dataset reconstructed by MCS ALS optimization'
        X_hat.title = 'X_hat: ' + self.X.title
        return X_hat

    def plotmerit(self, **kwargs):
        """
        Plots the input dataset, reconstructed dataset and residuals

        Returns
        -------
        axes

        """
        colX, colXhat, colRes = kwargs.get('colors', ['blue', 'green', 'red'])

        X_hat = self.reconstruct()
        res = self.X - X_hat
        ax = self.X.plot()
        if self.X.x is not None:
            ax.plot(self.X.x.data, X_hat.T.data, color=colXhat)
            ax.plot(self.X.x.data, res.T.data, color=colRes)
        else:
            ax.plot(X_hat.T.data, color=colXhat)
            ax.plot(res.T.data, color=colRes)
        ax.autoscale(enable=True)
        ax.set_title('MCR ALS merit plot')
        return ax
