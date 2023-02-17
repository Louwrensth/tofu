# -*- coding: utf-8 -*-


# Built-in
import copy
import warnings


# Common
import numpy as np
import scipy.integrate as scpinteg
import astropy.units as asunits


import datastock as ds


from . import _generic_plot


# #############################################################################
# #############################################################################
#                           Matrix - compute
# #############################################################################


def compute(
    coll=None,
    key=None,
    key_bsplines=None,
    key_diag=None,
    key_cam=None,
    # sampling
    res=None,
    mode=None,
    method=None,
    crop=None,
    # options
    brightness=None,
    # output
    store=None,
    verb=None,
):
    """ Compute the geometry matrix using:
            - a Plasma2DRect instance with a key to a bspline set
            - a cam instance with a resolution
    """

    # -----------
    # check input
    # -----------

    (
        key,
        key_bsplines, key_mesh, key_mesh0, mtype,
        key_diag, key_cam,
        method, res, mode, crop,
        brightness,
        store, verb,
    ) = _compute_check(
        coll=coll,
        key=key,
        key_bsplines=key_bsplines,
        key_diag=key_diag,
        key_cam=key_cam,
        # sampling
        method=method,
        res=res,
        mode=mode,
        crop=crop,
        # options
        brightness=brightness,
        # output
        store=store,
        verb=verb,
    )

    # -----------
    # prepare
    # -----------

    key_kR = coll.dobj['mesh'][key_mesh0]['knots'][0]
    radius_max = np.max(coll.ddata[key_kR]['data'])

    shapebs = coll.dobj['bsplines'][key_bsplines]['shape']

    # prepare indices
    indbs = coll.select_ind(
        key=key_bsplines,
        returnas=bool,
        crop=crop,
    )

    # prepare matrix
    is3d = False
    if mtype == 'polar':
        radius2d = coll.dobj[coll._which_mesh][key_mesh]['radius2d']
        r2d_reft = coll.get_time(key=radius2d)[2]
        if r2d_reft is not None:
            r2d_nt = coll.dref[r2d_reft]['size']
            if r2d_nt > 1:
                shapemat = tuple(np.r_[r2d_nt, None, indbs.sum()])
                is3d = True

    if not is3d:
        shapemat = tuple(np.r_[None, indbs.sum()])

    if verb is True:
        msg = f"Geom matrix for diag '{key_diag}' and bs '{key_bsplines}':"
        print(msg)

    # -----------
    # compute
    # -----------

    if method == 'los':
        dout, axis = _compute_los(
            coll=coll,
            key=key,
            key_bsplines=key_bsplines,
            key_diag=key_diag,
            key_cam=key_cam,
            # sampling
            indbs=indbs,
            res=res,
            mode=mode,
            radius_max=radius_max,
            # groupby=groupby,
            is3d=is3d,
            # other
            shapemat=shapemat,
            brightness=brightness,
            verb=verb,
        )

    else:
        raise NotImplementedError()

    # ---------------
    # check
    # ---------------

    if axis is None:
        _no_interaction(
            coll=coll,
            key=key,
            key_bsplines=key_bsplines,
            key_diag=key_diag,
            key_cam=key_cam,
        )
        store = False
        import pdb; pdb.set_trace() # DB

    # ---------------
    # store / return
    # ---------------

    if store:
        _store(
            coll=coll,
            key=key,
            key_bsplines=key_bsplines,
            key_diag=key_diag,
            key_cam=key_cam,
            method=method,
            res=res,
            crop=crop,
            dout=dout,
            axis=axis,
        )

    else:
        return dout


# ###################
#   checking
# ###################


def _compute_check(
    coll=None,
    key=None,
    key_bsplines=None,
    key_diag=None,
    key_cam=None,
    # sampling
    method=None,
    res=None,
    mode=None,
    crop=None,
    # options
    brightness=None,
    # output
    store=None,
    verb=None,
):

    wm = coll._which_mesh
    wbs = coll._which_bsplines

    # key
    key = ds._generic_check._obj_key(
        d0=coll.dobj.get('geom matrix', {}),
        short='gmat',
        key=key,
    )

    # key_bsplines
    lk = list(coll.dobj.get(wbs, {}).keys())
    key_bsplines = ds._generic_check._check_var(
        key_bsplines, 'key_bsplines',
        types=str,
        allowed=lk,
    )

    # key_mesh0
    key_mesh = coll.dobj[wbs][key_bsplines][wm]
    mtype = coll.dobj[wm][key_mesh]['type']
    submesh = coll.dobj[wm][key_mesh]['submesh']
    if submesh is not None:
        key_mesh0 = submesh
    else:
        key_mesh0 = key_mesh

    # key_diag, key_cam
    key_diag, key_cam = coll.get_diagnostic_cam(
        key=key_diag,
        key_cam=key_cam,
    )

    # method
    method = ds._generic_check._check_var(
        method, 'method',
        default='los',
        types=str,
        allowed=['los'],
    )

    # res
    res = ds._generic_check._check_var(
        res, 'res',
        default=0.01,
        types=float,
        sign='> 0.',
    )

    # mode
    mode = ds._generic_check._check_var(
        mode, 'mode',
        default='abs',
        types=str,
        allowed=['abs', 'rel'],
    )

    # crop
    crop = ds._generic_check._check_var(
        crop, 'crop',
        default=True,
        types=bool,
    )
    crop = (
        crop
        and coll.dobj[wbs][key_bsplines]['crop'] not in [None, False]
    )

    # brightness
    brightness = ds._generic_check._check_var(
        brightness, 'brightness',
        types=bool,
        default=False,
    )

    # store
    store = ds._generic_check._check_var(
        store, 'store',
        default=True,
        types=bool,
    )

    # verb
    if verb is None:
        verb = True
    if not isinstance(verb, bool):
        msg = (
            f"Arg verb must be a bool!\n"
            f"\t- provided: {verb}"
        )
        raise Exception(msg)

    return (
        key,
        key_bsplines, key_mesh, key_mesh0, mtype,
        key_diag, key_cam,
        method, res, mode, crop,
        brightness,
        store, verb,
    )


# ###################
#   compute_los
# ###################


def _compute_los(
    coll=None,
    key=None,
    key_bsplines=None,
    key_diag=None,
    key_cam=None,
    # sampling
    indbs=None,
    res=None,
    mode=None,
    key_integrand=None,
    radius_max=None,
    is3d=None,
    # other
    shapemat=None,
    brightness=None,
    verb=None,
):

    # -----
    # units

    units = asunits.m
    units_coefs = asunits.Unit()

    # ----------------
    # loop on cameras

    dout = {}
    doptics = coll.dobj['diagnostic'][key_diag]['doptics']
    for k0 in key_cam:

        npix = coll.dobj['camera'][k0]['dgeom']['pix_nb']
        key_los = doptics[k0]['los']
        key_mat = f'{key}_{k0}'

        sh = tuple([npix if ss is None else ss for ss in shapemat])
        mat = np.zeros(sh, dtype=float)

        # -----------------------
        # loop on group of pixels (to limit memory footprint)

        anyok = False
        for ii in range(npix):

            # verb
            if verb is True:
                msg = f"\t- '{key_mat}': pixel {ii + 1} / {npix}"
                msg += f"\t{(mat > 0).sum()} / {mat.size}"
                end = '\n' if ii == npix - 1 else '\r'
                print(msg, flush=True, end=end)

            # sample los
            out_sample = coll.sample_rays(
                key=key_los,
                res=res,
                mode=mode,
                segment=None,
                ind_flat=ii,
                radius_max=radius_max,
                concatenate=False,
                return_coords=['R', 'z', 'ltot'],
            )

            if out_sample is None:
                continue

            R, Z, length = out_sample

            # -------------
            # interpolate

            # datai, units, refi = coll.interpolate(
            douti = coll.interpolate(
                keys=None,
                ref_key=key_bsplines,
                x0=R[0],
                x1=Z[0],
                submesh=True,
                grid=False,
                # azone=None,
                indbs_tf=indbs,
                details=True,
                crop=None,
                nan0=True,
                val_out=np.nan,
                return_params=False,
                store=False,
            )[f'{key_bsplines}_details']

            datai, refi = douti['data'], douti['ref']
            axis = refi.index(None)
            iok = np.isfinite(datai)

            if not np.any(iok):
                continue

            datai[~iok] = 0.

            # ------------
            # integrate

            assert datai.ndim in [2, 3], datai.shape

            # integrate
            if is3d:
                mat[:, ii, :] = scpinteg.simpson(
                    datai,
                    x=length[0],
                    axis=axis,
                )
            elif datai.ndim == 3 and datai.shape[0] == 1:
                mat[ii, :] = scpinteg.simpson(
                    datai[0, ...],
                    x=length[0],
                    axis=axis,
                )
                # mat[ii, :] = np.nansum(mati[0, ...], axis=0) * reseff[ii]
            else:
                mat[ii, :] = scpinteg.simpson(
                    datai,
                    x=length[0],
                    axis=axis,
                )
            anyok = True

        # --------------
        # post-treatment

        if anyok:
            # brightness
            if brightness is False:
                ketend = doptics[k0]['etendue']
                units_coefs = coll.ddata[ketend]['units']
                etend = coll.ddata[ketend]['data']
                sh_etend = [-1 if aa == axis else 1 for aa in range(len(refi))]
                mat *= etend.reshape(sh_etend)

            # set ref
            refi = list(refi)
            refi[axis] = coll.dobj['camera'][k0]['dgeom']['ref_flat']
            refi = tuple(np.r_[refi[:axis], refi[axis], refi[axis+1:]])

        else:
            refi = None
            axis = None

        # fill dout
        dout[key_mat] = {
            'data': mat,
            'ref': refi,
            'units': units * units_coefs,
        }

    return dout, axis


# ###################
#   compute_vos
# ###################


def _compute_vos(
    coll=None,
    is2d=None,
    key_diag=None,
    key_cam=None,
    res=None,
    mode=None,
    key_integrand=None,
    radius_max=None,
    groupby=None,
    val_init=None,
    brightness=None,
):



    return None, None


# ###################
#   storing
# ###################


def _store(
    coll=None,
    key=None,
    key_bsplines=None,
    key_diag=None,
    key_cam=None,
    method=None,
    res=None,
    crop=None,
    dout=None,
    axis=None,
):

    # shapes
    shapes = [v0['data'].shape for v0 in dout.values()]
    assert all([len(ss) == len(shapes[0]) for ss in shapes[1:]])
    shapes = np.array(shapes)
    assert np.allclose(shapes[1:, :axis], shapes[0:1, :axis])
    assert np.allclose(shapes[1:, axis+1:], shapes[0:1, axis+1:])

    # add matrix obj
    dobj = {
        'geom matrix': {
            key: {
                'data': list(dout.keys()),
                'bsplines': key_bsplines,
                'diagnostic': key_diag,
                'camera': key_cam,
                'method': method,
                'res': res,
                'crop': crop,
                'shape': tuple(shapes[0, :]),
                'axis_chan': axis,
            },
        },
    }

    coll.update(ddata=dout, dobj=dobj)


# ##################################################################
# ##################################################################
#               retrofit
# ##################################################################


def _concatenate(
    coll=None,
    key=None,
):

    # ------------
    # check inputs

    lok = list(coll.dobj.get('geom matrix', {}).keys())
    key = ds._generic_check._check_var(
        key, 'key',
        types=str,
        allowed=lok,
    )

    # -----------
    # concatenate

    key_data = coll.dobj['geom matrix'][key]['data']
    key_cam = coll.dobj['geom matrix'][key]['camera']
    axis = coll.dobj['geom matrix'][key]['axis_chan']

    ref = list(coll.ddata[key_data[0]]['ref'])
    ref[axis] = None

    ind = 0
    dind = {}
    ldata = []
    for ii, k0 in enumerate(key_cam):
        datai = coll.ddata[key_data[ii]]['data']
        dind[k0] = ind + np.arange(0, datai.shape[axis])
        ldata.append(datai)
        ind += datai.shape[axis]

    data = np.concatenate(ldata, axis=axis)

    return data, ref, dind


# ###################
#   no interaction
# ###################


def _no_interaction(
    coll=None,
    key=None,
    key_bsplines=None,
    key_diag=None,
    key_cam=None,
):

    # ----------
    # plot

    wm = coll._which_mesh
    wbs = coll._which_bsplines
    keym = coll.dobj[wbs][key_bsplines][wm]
    submesh = coll.dobj[wm][keym]['submesh']

    is2d = coll.dobj['diagnostic'][key_diag]['is2d']

    # repare dax
    dax0 = _generic_plot.get_dax_diag(
        proj=['cross', 'hor', '3d', 'camera'],
        dmargin=None,
        fs=None,
        wintit=None,
        tit='debug',
        is2d=is2d,
        key_cam=key_cam,
    )

    # mesh
    if submesh is None:
        dax = coll.plot_mesh(
            key=keym,
            dax={'cross': dax0['cross']},
            crop=True,
        )

    else:
        dax = coll.plot_mesh(
            key=submesh,
            dax={'cross': dax0['cross']},
            crop=True,
        )

        dax = coll.plot_mesh(keym)

    # cam
    dax = coll.plot_diagnostic(
        key=key_diag,
        key_cam=key_cam,
        elements='o',
        dax=dax0,
    )

    # -----
    # msg

    msg = (
        "No interaction detected between:\n"
        f"\t- camera: {key_cam}\n"
        f"\t- bsplines: {key_bsplines}\n"
        f"\t- submesh: {submesh}\n"
    )
    warnings.warn(msg)
