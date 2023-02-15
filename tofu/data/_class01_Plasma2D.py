# -*- coding: utf-8 -*-


# Built-in
import copy


# Common
import numpy as np
import datastock as ds


# tofu
# from tofu import __version__ as __version__
from ._class00_Config import Config as Previous


__all__ = ['Plasma2D']


_WHICH_MESH = 'mesh'
_QUANT_R = 'R'
_QUANT_Z = 'Z'


# #############################################################################
# #############################################################################
#                           Plasma2D
# #############################################################################


class Plasma2D(Previous):

    _ddef = copy.deepcopy(ds.DataStock._ddef)

    # _show_in_summary_core = ['shape', 'ref', 'group']
    _dshow = dict(Previous._dshow)

    # _quant_R = _QUANT_R
    # _quant_Z = _QUANT_Z

    # -------------------
    # units conversione
    # -------------------

    def convert_units_spectral(
        self,
        data=None,
        units=None,
        units_in=None,
    ):

        return _class01_compute.convert_spectral_units(
            coll=self,
            data=data,
            units=units,
            units_in=units_in,
        )


    # -------------------
    # get data time
    # -------------------

    def get_time(
        self,
        key=None,
        t=None,
        indt=None,
        ind_strict=None,
        dim=None,
    ):
        """ Return the time vector or time macthing indices

        hastime, keyt, reft, keyt, val, dind = self.get_time(key='prof0')

        Return
        ------
        hastime:    bool
            flag, True if key has a time dimension
        keyt:       None /  str
            if hastime and a time vector exists, the key to that time vector
        t:          None / np.ndarray
            if hastime
        dind:       dict, with:
            - indt:  None / np.ndarray
                if indt or t was provided, and keyt exists
                int indices of nearest matching times
            - indtu: None / np.ndarray
                if indt is returned, np.unique(indt)
            - indtr: None / np.ndarray
                if indt is returned, a bool (ntu, nt) array
            - indok: None / np.ndarray
                if indt is returned, a bool (nt,) array

        """

        if dim is None:
            dim = 'time'

        return self.get_ref_vector(
            key=key,
            values=t,
            indices=indt,
            ind_strict=ind_strict,
            dim=dim,
        )

    def get_time_common(
        self,
        keys=None,
        t=None,
        indt=None,
        ind_strict=None,
        dim=None,
    ):
        """ Return the time vector or time macthing indices

        hastime, hasvect, t, dind = self.get_time_common(
            keys=['prof0', 'prof1'],
            t=np.linspace(0, 5, 10),
        )

        Return
        ------
        hastime:        bool
            flag, True if key has a time dimension
        keyt:           None /  str
            if hastime and a time vector exists, the key to that time vector
        t:              None / np.ndarray
            if hastime
        indt:           None / np.ndarray
            if indt or t was provided, and keyt exists
            int indices of nearest matching times
        indtu:          None / np.ndarray
            if indt is returned, np.unique(indt)
        indt_reverse:   None / np.ndarray
            if indt is returned, a bool (ntu, nt) array

        """

        if dim is None:
            dim = 'time'

        return self.get_ref_vector_common(
            keys=keys,
            values=t,
            indices=indt,
            ind_strict=ind_strict,
            dim=dim,
        )
