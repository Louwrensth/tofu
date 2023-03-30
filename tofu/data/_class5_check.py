# -*- coding: utf-8 -*-


import copy


import numpy as np
import scipy.integrate as scpinteg
import datastock as ds


from ..spectro import _rockingcurve_def
from ..spectro import _rockingcurve


_DMAT_KEYS = {
    'material': {'types': str},
    'name': {'types': str},
    'symbol': {'types': str},
    'd_hkl': {'types': float, 'sign': '> 0.'},
    'target': {'types': dict},
    'miller': {'dtype': int, 'size': 3, 'sign': '>= 0'},
    'alpha': {'types': float, 'default': 0., 'sign': '>= 0'},
    'beta': {'types': float, 'default': 0.},
    'mesh': {'types': dict},
    'miscut': {'types': bool, 'default': True},
}


# ################################################################
# ################################################################
#                           Crystal
# ################################################################


def _dmat(
    coll=None,
    key=None,
    dmat=None,
    alpha=None,
    beta=None,
    dgeom=None,
):

    # ---------------------
    # Easy cases
    # ---------------------

    # not mat
    if dmat is None:
        return dmat

    # known crystal
    ready_to_compute = False
    if isinstance(dmat, str):
        if dmat not in _rockingcurve_def._DCRYST.keys():
            msg = (
                f"Arg dmat points to an unknown crystal: '{dmat}'"
            )
            raise Exception(msg)
        dmat = _rockingcurve_def._DCRYST[dmat]
        ready_to_compute = True

    # ---------------------
    # check dict integrity
    # ---------------------

    # Check dict typeand content (each key is a valid string)
    dmat = ds._generic_check._check_dict_valid_keys(
        var=dmat,
        varname='dmat',
        has_all_keys=False,
        has_only_keys=False,
        keys_can_be_None=True,
        dkeys=_DMAT_KEYS,
    )

    dmat['ready_to_compute'] = ready_to_compute

    # -------------------------------
    # check parallelism
    # -------------------------------

    alpha = _check_parallelism(
        alpha=alpha,
        beta=beta,
        dmat=dmat,
        dgeom=dgeom,
    )

    # -------------------------------
    # check rocking curve
    # -------------------------------

    dref = None
    if ready_to_compute:
        drock = _rockingcurve.compute_rockingcurve(
            # Type of crystal
            crystal=dmat['name'],
            din=None,
            # Wavelength
            lamb=dmat['target']['lamb'],
            # Lattice modifications
            miscut=dmat['miscut'],
            nn=None,
            alpha_limits=None,
            therm_exp=True,
            temp_limits=None,
            # Plot
            plot_therm_exp=False,
            plot_asf=False,
            plot_power_ratio=False,
            plot_asymmetry=False,
            plot_cmaps=False,
            # Returning dictionnary
            returnas=dict,
        )

        lk0 = [
            'material',
            'name',
            'symbol',
            'miller',
            'd_hkl',
            'target',
            'alpha',
            'beta',
            'miscut',
            'nin',
            'e0',
            'e1',
        ]

        assert np.allclose(dmat['nin'], drock['nin'])
        assert np.allclose(dmat['e0'], drock['e0'])
        dmat = {
            k0: copy.deepcopy(drock[k0])
            for k0 in lk0
        }
        dmat['d_hkl'] *= 1e-10
        dmat['target']['lamb'] *= 1e-10

        dmat['mesh'] = {'type': str(drock['mesh']['type'])}

        # -------------------------------------------
        # interpolate at desired alpha vs T and angle

        dref, ddata, drock2 = _extract_rocking_curve(
            key=key,
            drock=drock,
            alpha=alpha,
        )
        dmat['drock'] = drock2


    elif isinstance(dmat, dict):

        if 'drock' in dmat.keys():
            dref, ddata, drock2 = _extract_rocking_curve_from_array(dmat)
            dmat['drock'] = drock2

    else:
        msg = f"Unknown dmat:\n{dmat}"
        raise Exception(msg)

    # saftey check
    assert ('drock' in dmat.keys()) == (dref is not None)

    # ---------------
    # Get width of rc

    if 'drock' in dmat.keys():
        power_ratio = ddata[dmat['drock']['power_ratio']]['data']
        angle_rel = ddata[dmat['drock']['angle_rel']]['data']
        pmax = np.nanmax(power_ratio)

        # integrated reflectivity
        dmat['drock']['integ_reflect'] = scpinteg.simps(
            power_ratio,
            x=angle_rel,
        )

        # FW
        dmat['drock']['FW'] = dmat['drock']['integ_reflect'] / pmax

    # ---------------
    # add dref, ddata

    if dref is not None:
        coll.update(dref=dref, ddata=ddata)

    return dmat



# ################################################################
# ################################################################
#                   Utilities
# ################################################################


def _extract_rocking_curve(key=None, drock=None, alpha=None):

    # 'Power ratio', (2, 1, 41, 201)
    # shape = (polar, nT, nalpha, ny = nangles)

    # ----------------
    # extract key data

    # ind_alpha
    ind_alpha = np.argmin(np.abs(drock['alpha'] - alpha))

    # temperature
    _, nT, nc, na = drock['Power ratio'].shape
    temp = drock['Temperature ref'] + drock['Temperature changes (°C)']
    indtref = np.argmin(np.abs(drock['Temperature changes (°C)']))
    Tref = temp[indtref]

    # bragg angle of reference
    braggref = drock['Bragg angle of reference (rad)']

    # differential glacing angles
    ang_rel = drock['Glancing angles'][0, indtref, ind_alpha, :] - braggref[indtref]
    # amin, amax = np.nanmin(ang_rel), np.nanmax(ang_rel)
    # angles = np.linspace(amin, amax, na)

    # power_ratio
    power_ratio = np.nanmean(
        drock['Power ratio'][:, indtref, ind_alpha, :],
        axis=0,
    )

    # ---------------
    # interpolate

    # power_ratio = np.full((2, na, nT), np.nan)
    # for ii in range(2):
        # for jj in range(nT):
            # power_ratio[ii, :, jj] = scpinterp.interp1d(
                # ang_rel[ii, jj, ind_alpha, :],
                # drock['Power ratio'][ii, jj, ind_alpha, :],
                # kind='linear',
                # axis=0,
                # bounds_error=False,
                # fill_value=0,
            # )(angles)

    # ------------
    # fill dict

    # dref
    knang = f'{key}_rc_angn'
    kntemp = f'{key}_rc_tempn'

    dref = {
        knang: {'size': na},
        kntemp: {'size': nT},
    }

    # ddata
    kang = f'{key}_rc_ang'
    ktemp = f'{key}_rc_T'
    kbragg = f'{key}_rc_bragg'
    krc = f'{key}_rc'

    ddata = {
        kang: {
            'data': ang_rel,
            'ref': knang,
            'units': 'rad',
            'dim': 'angle',
        },
        ktemp: {
            'data': temp,
            'ref': kntemp,
            'units': 'C',
            'dim': 'temperature',
        },
        kbragg: {
            'data': braggref,
            'ref': kntemp,
            'units': 'rad',
            'dim': 'angle',
        },
        krc: {
            'data': power_ratio,
            'ref': knang,
            'units': '',
            'dim': 'ratio',
        },
    }

    # drock2
    drock2 = {
        'T': ktemp,
        'braggT': kbragg,
        'angle_rel': kang,
        'power_ratio': krc,
        'Tref': Tref,
    }

    return dref, ddata, drock2


def _extract_rocking_curve_from_array(dmat=None):

    # -------------
    # check inputs

    # extract
    angle_rel = dmat['drock'].get('angle_rel')
    power_ratio = dmat['drock'].get('power_ratio')

    # safety check
    c0 = (
        angle_rel is not None
        and power_ratio is not None
        and np.array(angle_rel).size == np.array(power_ratio).size
    )
    if not c0:
        msg = (
            "Rocking curve must be provided as a subdict dmat['drock'] with:\n"
            "\t- 'angle_rel': relative incidence angle vector\n"
            "\t- 'power_ratio': power ratio vector, same size as 'angle_rel'\n"
            f"Provided:\n{dmat['drock']}"
        )
        raise Exception(msg)

    # format
    angle_rel = ds._generic_check._check_flat1darray(
        angle_rel, 'angle_rel',
        dtype=float,
        unique=True,
    )

    power_ratio = ds._generic_check._check_flat1darray(
        power_ratio, 'power_ratio',
        dtype=float,
        size=angle_rel.size,
    )

    # -----------
    # fill dict

    # dref
    knang = f'{key}_rc_angn'
    dref = {
        knang: {'size': angle_rel.size},
    }

    # ddata
    kang = f'{key}_rc_ang'
    krc = f'{key}_rc'

    ddata = {
        kang: {
            'data': angle_rel,
            'ref': knang,
            'units': 'rad',
            'dim': 'angle',
        },
        krc: {
            'data': power_ratio,
            'ref': knang,
            'units': '',
            'dim': 'ratio',
        },
    }

    # drock2
    drock2 = {
        'angle_rel': kang,
        'power_ratio': krc,
    }

    return dref, ddata, drock2


# ################################################################
# ################################################################
#                           Parallelism
# ################################################################


def _check_parallelism(
    alpha=None,
    beta=None,
    dmat=None,
    dgeom=None,
):

    # ------------
    # check inputs

    # alpha
    alpha = float(ds._generic_check._check_var(
        alpha, 'alpha',
        types=(float, int),
        default=0.,
        sign='>=0',
    )) % (np.pi/2.)

    # beta
    beta = float(ds._generic_check._check_var(
        beta, 'beta',
        types=(float, int),
        default=0.,
        sign='>=0',
    )) % (2.*np.pi)

    # ------------
    # set in dict

    # alpha
    if dmat.get('alpha') is None:
        dmat['alpha'] = alpha
    dmat['alpha'] = np.abs(np.arctan2(
        np.sin(dmat['alpha']),
        np.cos(dmat['alpha']),
    ))

    # beta
    if dmat.get('beta') is None:
        dmat['beta'] = beta
    dmat['beta'] = np.arctan2(
        np.sin(dmat['beta']),
        np.cos(dmat['beta']),
    )

    # ---------------------------------
    # vector basis with non-paralellism

    # nin
    nin = (
        np.cos(dmat['alpha'])*(dgeom['nin'])
        + np.sin(dmat['alpha']) * (
            np.cos(dmat['beta'])*dgeom['e0']
            + np.sin(dmat['beta'])*dgeom['e1']
        )
    )

    # e0
    e0 = (
        - np.sin(dmat['alpha'])*(dgeom['nin'])
        + np.cos(dmat['alpha']) * (
            np.cos(dmat['beta'])*dgeom['e0']
            + np.sin(dmat['beta'])*dgeom['e1']
        )
    )

    # e1 + check
    nin, e0, e1 = ds._generic_check._check_vectbasis(
        e0=nin,
        e1=e0,
        e2=None,
        dim=3,
    )

    # store
    dmat['nin'] = nin
    dmat['e0'] = e0
    dmat['e1'] = e1

    return alpha
