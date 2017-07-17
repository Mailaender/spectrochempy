# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t; python-indent: 4 -*-
#
# =============================================================================
# Copyright (©) 2015-2017 LCS
# Laboratoire Catalyse et Spectrochimie, Caen, France.
#
# This software is a computer program whose purpose is to [describe
# functionalities and technical features of your software].
#
# This software is governed by the CeCILL license under French law and
# abiding by the rules of distribution of free software. You can use,
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty and the software's author, the holder of the
# economic rights, and the successive licensors have only limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading, using, modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean that it is complicated to manipulate, and that also
# therefore means that it is reserved for developers and experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and, more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.
# =============================================================================

"""Plugin module to extend NDDataset with the import methods method.

"""
import os
import warnings
import numpy as np
from datetime import datetime, timezone, timedelta

from spectrochempy.core.dataset.nddataset import NDDataset
from spectrochempy.api import options
from spectrochempy.gui import gui

__all__ = ['read_omnic']

# utility functions
#-------------------

def readbtext(f, pos):
    """Read some text in binary file, until b\0\ is encountered. \
    Returns utf-8 string """
    f.seek(pos)  # read first byte, ensure entering the while loop
    btext = f.read(1)
    while not (btext[len(btext) - 1] == 0):  # while the last byte of btext differs from zero
        btext = btext + f.read(1)  # append 1 byte

    btext = btext[0:len(btext) - 1]  # cuts the last byte
    text = btext.decode(encoding='utf-8', errors='ignore')  # decode btext to string
    return text


def readfilename(filename):

    if not filename:
        filename = gui.openFileNameDialog(filters='OMNIC file (*.spg);;'
                              'OMNIC file (*.spa)')

        if not filename:
            raise IOError('no filename provided!')

    # filename passed
    _, extension = os.path.splitext(filename)
    return [filename], extension


# function for loading spa or spg file
#--------------------------------------
def read_omnic(source, filename='', sortbydate=True, **kwargs):
    """Open a Thermo Nicolet .spg or list of .spa files and set data/metadata in the current dataset

    Parameters
    ----------

    source : NDDataset

        The dataset to store the data and the metadata read from the spg file

    filename: str

        filename of the file to load

    directory: `str` [optional, default=""].
        From where to read the specified filename. If not sperfied, read i the current directory.

    Example
    --------
        >>> from spectrochempy.api import NDDataset, data_dir
        >>> A = NDDataset.read_omnic('irdata/NH4Y-activation.SPG', directory=data_dir)
        >>> A.print()
           name: Ex_spectra.spg
         author: Username
           date: Wed., 26-Nov-14, 08:30:35
           data: 10x1350  [float64]
           (...)

    """

    # check if the first parameter is a dataset
    # because we allow not to pass it
    if not isinstance(source, NDDataset):
        # probably did not specify a dataset
        # so the first parameters must be the filename
        if isinstance(source, str):
            filename = source
            source = NDDataset() # create a NDDataset
        else:
            #TODO: GENERATE A WARNING
            return None

    directory = kwargs.get("directory", options.data_dir)
    if not os.path.exists(directory):
        raise IOError("directory doesn't exists!")

    if os.path.isdir(directory):
        filename = os.path.expanduser(os.path.join(directory, filename))
    else:
        warnings.warn('Provided directory is a file, '
                      'so we use its parent directory')
        filename = os.path.join(os.path.dirname(directory), filename)

    # open file dialog box if necessary
    res = readfilename(filename)

    if res is None:
        return None

    filename, extension = res
    nspec = len(filename)

    if extension.lower() == '.spg':
        filename = filename[0]

        # read spg file
        with open(filename, 'rb') as f:

            # Read title:
            # The file title starts at position hex 1e = decimal 30.
            # Its max length is 256 bytes and it is followed by at least
            # one \0. It is the original filename under which the group has
            # been saved: it won't match with the actual filename if a subsequent
            # renaming has been done in e.g. Windows.

            spg_title = readbtext(f, 30)

            # The acquisition date (GMT) of 1st spectrum at hex 128 = decimal 296.
            # The format is HFS+ 32 bit hex value, little endian

            f.seek(296)

            # Count the number of spectra
            # From hex 120 = decimal 304, individual spectra are described
            # by blocks of lines starting with "key values",
            # for instance hex[02 6a 6b 69 1b 03 82] -> dec[02 106  107 105 27 03 130]
            # Each of theses lines provides positions of data and metadata in the file:
            #
            #     key: hex 02, dec  02 : position of spectral header (=> nx,
            #                                 firstx, lastx, nscans, nbkgscans)
            #     key: hex 03, dec  03 : intensity position
            #     key: hex 04, dec  04 : user text position
            #     key: hex 1B, dec  27 : position of History text
            #     key: hex 69, dec 105 : ?
            #     key: hex 6a, dec 106 : ?
            #     key: hex 6b, dec 107 : position of spectrum title, the acquisition
            #                                 date follows at +256(dec)
            #     key: hex 80, dec 128 : ?
            #     key: hex 82, dec 130 : ?
            #
            # the number of line per block may change from one omnic version to another,
            # but the total number of lines is given at hex 294, hence allowing counting
            # nummber of spectra:

            # np.nonzero((code == 2)) ; np.count_nonzero((a==2))

            # read total number of lines
            f.seek(294)
            nlines = np.fromfile(f, 'uint16', count=1)

            # read "key values"
            pos = 304
            keys = np.zeros((nlines))
            for i in range(nlines[0]):
                f.seek(pos)
                keys[i] = np.fromfile(f, dtype='uint8', count=1)[0]
                pos = pos + 16

            # count the number of occurences of the key '02' == number of spectra
            nspec = np.count_nonzero((keys == 2))

            if nspec == 0:
                print('Error: File format not recognized - information markers not found')
                return

            ##Get xaxis (e.g. wavenumbers)

            # container to hold values
            nx, firstx, lastx = np.zeros(nspec, 'int'), np.zeros(nspec, 'float'), np.zeros(nspec, 'float')

            # Extracts positions of '02' keys
            key_is_02 = (keys == 2)  # ex: [T F F F F T F (...) F T ....]'
            indices02 = np.nonzero(key_is_02)  # ex: [1 9 ...]
            position02 = 304 * np.ones(len(indices02[0]), dtype='int') + 16 * indices02[0]

            # ex: [304 432 ...]
            for i in range(nspec):
                f.seek(position02[i] + 2)  # go to line and skip 2 bytes
                info_pos = np.fromfile(f, dtype='uint32', count=1)[0]
                nx_pos = info_pos + 4
                firstx_pos = info_pos + 16
                lastx_pos = info_pos + 20
                # other positions of potential interest:
                #   nscan_pos = info_pos + 36;
                #   nbkgscan_pos = info_pos + 52;

                f.seek(nx_pos)
                nx[i] = np.fromfile(f, 'uint32', 1)
                f.seek(firstx_pos)
                firstx[i] = np.fromfile(f, 'float32', 1)
                f.seek(lastx_pos)
                lastx[i] = np.fromfile(f, 'float32', 1)

            # check the consistency of xaxis
            if np.ptp(nx) != 0:
                print('Error: Inconsistant data set - number of wavenumber per spectrum should be identical')
                return
            elif (np.ptp(firstx) != 0):
                print('Error: Inconsistant data set - the x axis should start at same value')
                return
            elif (np.ptp(lastx) != 0):
                print('Error: Inconsistant data set - the x axis should end at same value')
                return

            xaxis = np.around(np.linspace(firstx[0], lastx[0], nx[0]), 3)

            ##now the intensity data

            # container to hold values
            intensity_pos, intensity_size = np.zeros(nspec, 'int'), np.zeros(nspec, 'int')

            # Extracts positions of '02' keys
            key_is_03 = (keys == 3)
            indices03 = np.nonzero(key_is_03)
            position03 = 304 * np.ones(len(indices03[0]), dtype='int') + 16 * indices03[0]

            # Read number of spectral intensities
            for i in range(nspec):
                # determines the position of informatioon
                f.seek(position03[i] + 2)  # go to line and skip 2 bytes
                intensity_pos[i] = np.fromfile(f, 'uint32', 1)
                f.seek(position03[i] + 6)
                intensity_size[i] = np.fromfile(f, 'uint32', 1)

            # check the consistency of intensities (probably redundent w/ xaxis check above)
            if np.ptp(intensity_size) != 0:
                print('Error: Inconsistent data set - number of data per spectrum should be identical')

            nintensities = int(intensity_size[0] / 4)  # 4 = size of uint32

            if nintensities != nx[0]:
                print(
                    'Error: Inconsistent file - number of wavenumber per spectrum should be equal to number of intensities')

            # Read spectral intensities
            data = np.zeros((nspec, nintensities), dtype='float32')
            for i in range(nspec):
                f.seek(intensity_pos[i])
                data[i, :] = np.fromfile(f, 'float32', int(nintensities))

            ## Get spectra titles & acquisition dates & history text
            # container to hold values
            alltitles, allacquisitiondates, alltimestamps, allhistories = [], [], [], []

            # extract positions of '6B' keys (spectra titles & acquisition dates)
            key_is_6B = (keys == 107)
            indices6B = np.nonzero(key_is_6B)
            position6B = 304 * np.ones(len(indices6B[0]), dtype='int') + 16 * indices6B[0]

            # read spectra titles and acquisition date
            for i in range(nspec):
                # determines the position of informatioon
                f.seek(position6B[i] + 2)  # go to line and skip 2 bytes
                spa_title_pos = np.fromfile(f, 'uint32', 1)

                # read filename
                spa_title = readbtext(f, spa_title_pos[0])
                alltitles.append(spa_title)

                # and the acquisition date
                f.seek(spa_title_pos[0] + 256)
                timestamp = np.fromfile(f, dtype=np.uint32, count=1)[0]   # days since 31/12/1899, 00:00
                acqdate = datetime(1899, 12, 31, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=int(timestamp))
                allacquisitiondates.append(acqdate)
                timestamp = acqdate.timestamp()  # Transform back to timestamp for storage in the Axis object
                                                    #  use datetime.fromtimestamp(d, timezone.utc))
                                                    # to transform back to datetime obkct

                alltimestamps.append(timestamp)


                # extract positions of '1B' codes (history text -- sometimes absent, e.g. peakresolve)
                key_is_1B = (keys == 27)
                indices1B = np.nonzero(key_is_1B)
                position1B = 304 * np.ones(len(indices1B[0]), dtype='int') + 16 * indices6B[0]

                if len(position1B) != 0:
                    # read history texts
                    for i in range(nspec):
                        # determine the position of information
                        f.seek(position1B[i] + 2)
                        history_pos = np.fromfile(f, 'uint32', 1)

                        # read history
                        history = readbtext(f, history_pos[0])
                        allhistories.append(history)


        # Create Dataset Object of spectral content
        source.data = data
        source.units = 'absorbance'
        source.title = 'Absorbance'
        source.name = spg_title
        source.axes = (np.array(alltimestamps), xaxis)
        source.axes.titles = ('Acquisition date (GMT)', 'Wavenumbers')
        source.axes[1].units = 'cm^-1'
        source.axes[0].labels = (allacquisitiondates, alltitles)
        source.axes[0].units = 's'

        # Set description and history
        source.description = (
        'Dataset from spg file : ' + spg_title + ' \n'
        + 'History of the 1st spectrum: ' + allhistories[0])

        source.history = str(datetime.now()) + ':read from spg file \n'

        if kwargs.get('sortbydate','True'):
            source.sort(axis=0, inplace=True)
            source.history = 'sorted'

        # Set the NDDataset date
        source._date = datetime.now()
        source._modified = source.date

    else: # list of spa

        # containers to hold values
        nx, firstx, lastx = np.zeros(nspec, 'int'), np.zeros(nspec, 'float'), np.zeros(nspec, 'float')
        allintensities, alltitles, allacquisitiondates, alltimestamps, allhistories = [], [], [], [], []

        for i, _filename in enumerate(filename):

            with open(_filename, 'rb') as f:

                # Read title:
                # The file title  starts at position hex 1e = decimal 30.
                # Its max length is 256 bytes and it is followed by at least
                # one \0. It is the original filename under which the group has
                # been saved: it won't match with the actual filename if a subsequent
                # renaming has been done in e.g. Windows.

                alltitles.append(readbtext(f, 30))

                # The acquisition date (GMT) is at hex 128 = decimal 296.
                # The format is HFS+ 32 bit hex value, little endian

                f.seek(296)

                timestamp = np.fromfile(f, dtype=np.uint32, count=1)[0]  # days since 31/12/1899, 00:00
                acqdate = datetime(1899, 12, 31, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=int(timestamp))
                allacquisitiondates.append(acqdate)
                timestamp = acqdate.timestamp() # Transform back to timestamp for storage in the Axis object
                                                # use datetime.fromtimestamp(d, timezone.utc))
                                                # to transform back to datetime obkct

                alltimestamps.append(timestamp)

                # From hex 120 = decimal 304, the spectrum is described
                # by blocks of lines starting with "key values",
                # for instance hex[02 6a 6b 69 1b 03 82] -> dec[02 106  107 105 27 03 130]
                # Each of theses lines provides positions of data and metadata in the file:
                #
                #     key: hex 02, dec  02 : position of spectral header (=> nx,
                #                                 firstx, lastx, nscans, nbkgscans)
                #     key: hex 03, dec  03 : intensity position
                #     key: hex 04, dec  04 : user text position
                #     key: hex 1B, dec  27 : position of History text
                #     key: hex 69, dec 105 : ?
                #     key: hex 6a, dec 106 : ?
                #     key: hex 80, dec 128 : ?
                #     key: hex 82, dec 130 : ?
                #


                gotinfos = [False, False, False]  # spectral header, intensity, history
                # scan "key values"
                pos = 304
                #        keys = np.zeros((nlines))
                #        for i in range(nlines):
                #            f.seek(pos)
                #            keys[i] = np.fromfile(f, dtype = 'uint8', count = 1)[0]
                #        pos = pos + 16

                while not (all(gotinfos)):
                    f.seek(pos)
                    key = np.fromfile(f, dtype='uint8', count=1)[0]
                    if (key == 2):
                        f.seek(pos + 2)  # skip 2 bytes
                        info_pos = np.fromfile(f, dtype='uint32', count=1)[0]
                        nx_pos = info_pos + 4
                        firstx_pos = info_pos + 16
                        lastx_pos = info_pos + 20
                        # other positions of potential interest:
                        #   nscan_pos = info_pos + 36;
                        #   nbkgscan_pos = info_pos + 52;

                        f.seek(nx_pos)
                        nx[i] = np.fromfile(f, 'uint32', 1)[0]
                        f.seek(firstx_pos)
                        firstx[i] = np.fromfile(f, 'float32', 1)[0]
                        f.seek(lastx_pos)
                        lastx[i] = np.fromfile(f, 'float32', 1)[0]

                        xaxis = np.around(np.linspace(firstx[0], lastx[0], nx[0]), 3)
                        gotinfos[0] = True


                    elif (key == 3):
                        f.seek(pos + 2)  # skip 2 bytes
                        intensity_pos = np.fromfile(f, 'uint32', 1)[0]
                        f.seek(pos + 6)
                        intensity_size = np.fromfile(f, 'uint32', 1)[0]

                        nintensities = int(intensity_size / 4)
                        # Read spectral intensities
                        f.seek(intensity_pos)
                        allintensities.append(np.fromfile(f, 'float32', int(nintensities)))
                        gotinfos[1] = True


                        # todo: extract positions of '1B' code (history text -- sometimes absent, e.g. peakresolve)
                    elif (key == 27):
                        f.seek(pos + 2)
                        history_pos = np.fromfile(f, 'uint32', 1)[0]
                        # read history
                        history = readbtext(f, history_pos)
                        allhistories.append(history)
                        gotinfos[2] = True

                    elif (key == False):
                        break

                    pos = pos + 16

        # check the consistency of xaxis
        if np.ptp(nx) != 0:
            print('Error: Inconsistant data set - number of wavenumber per spectrum should be identical')
            return
        elif (np.ptp(firstx) != 0):
            print('Error: Inconsistant data set - the x axis should start at same value')
            return
        elif (np.ptp(lastx) != 0):
            print('Error: Inconsistant data set - the x axis should end at same value')
            return

        # load into the  Dataset Object of spectral content
        source.data = np.array(allintensities)
        #nd.title = alltitles[0] + ' ... ' + alltitles[-1]
        source.units = 'absorbance'
        source.title = 'Absorbance'
        source.name = alltitles[0] + ' ... ' + alltitles[-1]
        source._date = datetime.datetime.now()
        source._modified = source._date

        #TODO: Finish the conversion
        raise NotImplementedError('implementation not finished')

        out.appendlabels(Labels(alltitles, 'Title'))
        out.appendlabels(Labels(allacquisitiondates, 'Acquisition date (GMT)'))
        out.appendaxis(Axis(xaxis, 'Wavenumbers (cm-1)'), dim=1)
        indexFirstSpectrum = 0
        if sortbydate:
            out.addtimeaxis()
            firstTime = min(out.dims[0].axes[0].values)
            indexFirstSpectrum = out.idx(firstTime, dim=0)
            out = out.sort(0, 0)
            out.dims[0].deleteaxis(0)
        out.description = (
        'dataset from spa files : ' + out.name + ' \n' + 'History of 1st spectrum: ' + allhistories[indexFirstSpectrum])
        out.history = (str(datetime.datetime.now()) + ':created by sa.loadspa() \n')

    # return the dataset
    return source


