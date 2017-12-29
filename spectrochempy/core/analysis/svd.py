# -*- coding: utf-8 -*-
#
# =============================================================================
# Copyright (©) 2015-2018 LCS
# Laboratoire Catalyse et Spectrochimie, Caen, France.
# CeCILL-B FREE SOFTWARE LICENSE AGREEMENT
# See full LICENSE agreement in the root directory
# =============================================================================
"""
This module implement the SVD (Singular Value Decomposition) class.

"""

__all__ = ['SVD']

__dataset_methods__ = ['SVD']

# ----------------------------------------------------------------------------
# third party imports
# ----------------------------------------------------------------------------

from traitlets import HasTraits, Instance
import numpy as np

# ----------------------------------------------------------------------------
# local imports
# ----------------------------------------------------------------------------

from spectrochempy.dataset.ndcoords import Coord, CoordSet
from spectrochempy.dataset.nddataset import NDDataset
from spectrochempy.dataset.ndarray import masked, nomask
from spectrochempy.utils import docstrings

# ----------------------------------------------------------------------------

class SVD(HasTraits):
    """
    Performs a Singular Value Decomposition of a dataset.
    
    The SVD is commonly written as :math:`X = U \Sigma V^{T}`.

    This class has the attributes: U, s = diag(S) and VT=V:math:`^T`.

    If the dataset contains masked values, the corresponding ranges are
    ignored in the calculation.

    """

    U = Instance(NDDataset, allow_none=True)
    """|NDDataset| - Contains the left unitary matrix. Its shape depends on 
    `full_matrices`."""

    s = Instance(NDDataset)
    """|NDDataset| - Vector of singular values"""

    VT = Instance(NDDataset, allow_none=True)
    """ |NDDataset| - Contains a transpose matrix of the Loadings. Its shape 
    depends on `full_matrices` """

    @docstrings.get_sectionsf('SVD')
    @docstrings.dedent
    def __init__(self, dataset, full_matrices=False, compute_uv=True):
        """
        Parameters
        -----------
        dataset : |NDDataset| object
            The `dataset` ``X`` has shape (`M`, `N`). `M` is the number of
            observations (for examples a series of IR spectra) while `N`
            is the number of features (for example the wavenumbers measured
            in each IR spectrum).
        full_matrices : bool, optional, default:`False`.
            If `False` , `U` and `VT` have the shapes (``M``,  ``k``) and
            (``k``, ``N``), respectively, where ``k`` = min(``M``, ``N``).
            Otherwise the shapes will be (``M``, ``M``) and (``N``, ``N``),
            respectively.
        compute_uv : bool, optional, default:True.
            Whether or not to compute `U` and `VT` in addition to `s`.

        Examples
        --------
        >>> dataset = NDDataset.load('mydataset.scp')
        >>> svd = SVD(dataset)
        >>> print(svd.ev.data)
        [11848.225  633.980 ...,    0.001    0.001]
        >>> print(svd.ev_cum.data)
        [11848.225 12482.204 ..., 12532.584 12532.585]
        >>> print(svd.ev_ratio.data)
        [  94.539    5.059 ...,    0.000    0.000]

        """

        # check if we have the correct input
        # ----------------------------------

        X = dataset

        if isinstance(X, NDDataset):
            # As seen below, we cannot performs SVD on the masked array
            # so let's take the ndarray only.
            # Warning: weed need to take the hidden values, to handle the
            # case of dim 1 axis. Of course, svd will work only for real
            # data, not complex or hypercomplex.
            data = X._data
            M, N  = X._data.shape

        else:
            raise TypeError('A dataset of type NDDataset is  '
                               'expected as a dataset of data, but an object'
                               ' of type {} has been provided'.format(
                               type(X).__name__))

        # Retains only valid rows and columns
        # -----------------------------------

        # unfortunately, the present SVD implementation in linalg library
        # doesn't support numpy masked arrays as input. So we will have to
        # remove the masked values ourselves

        # the following however assumes that entire rows or columns are masked,
        # not only some individual data (if this is what you wanted, this
        # will fail)

        masked_columns = np.all(X._mask, axis=-2)
        masked_rows = np.all(X._mask, axis=-1)

        data = data[:, ~ masked_columns]
        data = data[~ masked_rows]

        # Performs the SVD
        # ----------------

        if data.size == 0 and np.product(data.shape[-2:]) == 0:
            raise np.linalg.LinAlgError("Arrays cannot be empty. You may "
                                        "want to check the masked data. ")

        res = np.linalg.svd(data, full_matrices, compute_uv)
        if compute_uv:
            U, s, VT = res
        else:
            s = res

        # Returns the diagonal sigma matrix as a NDDataset object
        # -------------------------------------------------------

        s = NDDataset(s)
        s.title='Singular values of ' + X.name
        s.name = 'sigma'
        s.history = 'created by SVD \n'
        s.description = (
            'Vector of singular values obtained  by SVD '
            'decomposition of ' + X.name)
        self.s = s

        if compute_uv:
            # Put back masked columns in  VT
            # ------------------------------
            # Note that it is very important to use here the ma version of zeros
            # array constructor
            KV = VT.shape[0]
            if np.any(masked_columns):
                Vtemp = np.ma.zeros((KV, N))  # note np.ma, not np.
                Vtemp[ : , ~ masked_columns ] = VT
                Vtemp[ : , masked_columns] = masked
                VT = Vtemp

            # Put back masked rows in U
            # -------------------------
            KU = U.shape[1]
            if np.any(masked_rows):
                Utemp = np.ma.zeros((M, KU))
                Utemp[~ masked_rows ] = U
                Utemp[masked_rows] = masked
                U = Utemp

            # Sign correction to ensure deterministic output from SVD.
            # This doesn't work will full_matrices=True.
            if not full_matrices:
                U, VT = self.svd_flip(U,VT)

            # Returns U as a NDDataset object
            # --------------------------------
            U = NDDataset(U)
            U.name = 'U'
            U.title = 'left singular vectors of ' + X.name
            U.coordset = CoordSet(X.coordset[0],
                                  Coord(None,
                                    labels=['#%d' % (i+1) for i in range(KU)],
                                    title='Components')
                                  )
            U.description = 'left singular vectors of ' + X.name
            U.history = 'created by SVD \n'

            # Returns the loadings (VT) as a NDDataset object
            # ------------------------------------------------

            VT = NDDataset(VT)
            VT.name = 'V.T'
            VT.title = 'Loadings (V.t) of ' + X.name
            VT.coordset = CoordSet(Coord(None,
                                     labels=['#%d' % (i+1) for i in range(KV)],
                                     title='Components'),
                                   X.coordset[1])
            VT.description = (
                'Loadings obtained by singular value decomposition of ' + X.name)
            VT.history = (str(VT.modified) + ': created by SVD \n')

            self.U = U
            self.VT = VT
        else:
            self.U = None
            self.VT = None

    # ------------------------------------------------------------------------
    # special methods
    # ------------------------------------------------------------------------

    def __repr__(self):
        return '<svd: U%s, s(%s), VT%s>' % (
            self.U.shape, self.s.size, self.VT.shape)

    # ------------------------------------------------------------------------
    #  Properties
    # ------------------------------------------------------------------------

    @property
    def ev(self):
        """|NDDataset|,  Explained variance """
        size = self.s.size
        ev = (self.s ** 2) / (size - 1)
        ev.name = 'ev'
        ev.title = 'Explained variance'
        ev.coordset = CoordSet(
                                 Coord(None,
                                 labels=['#%d' % (i+1) for i in range(size)],
                                 title='Components'))
        return ev

    @property
    def ev_cum(self):
        """|NDDataset|,  Cumulative Explained Variance """
        ev_cum = np.cumsum(self.ev_ratio)
        ev_cum.name = 'ev_cum'
        ev_cum.title = 'Cumulative explained variance'
        ev_cum.units = 'percent'
        return ev_cum

    @property
    def ev_ratio(self):
        """|NDDataset|,  Explained Variance per singular values """
        ratio = self.ev *100. / np.sum(self.ev)
        ratio.name = 'ev_ratio'
        ratio.title = 'Explained variance'
        ratio.units = 'percent'
        return ratio

    def svd_flip(self, U, VT, u_based_decision=True):
        """
        Sign correction to ensure deterministic output from SVD.
        Adjusts the columns of u and the rows of v such that the loadings in the
        columns in u that are largest in absolute value are always positive.

        Parameters
        ----------
        u_based_decision : boolean, (default=True)
            If True, use the columns of u as the basis for sign flipping.
            Otherwise, use the rows of v.

        Notes
        -----
        Copied and modified from scikit-learn.utils.extmath (BSD 3 Licence)

        """

        if u_based_decision:
            # columns of U, rows of VT
            max_abs_cols = np.argmax(np.abs(U), axis=0)
            signs = np.sign(U[max_abs_cols, range(U.shape[1])])
            U *= signs
            VT *= signs[:, np.newaxis]
        else:
            # rows of V, columns of U
            max_abs_rows = np.argmax(np.abs(VT), axis=1)
            signs = np.sign(VT[range(VT.shape[0]), max_abs_rows])
            U *= signs
            VT *= signs[:, np.newaxis]

        return U, VT


# ============================================================================
if __name__ == '__main__':
    pass