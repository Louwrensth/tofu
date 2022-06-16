# -*- coding: utf-8 -*-


# Built-in
import datetime as dtm


# Common
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors


# specific
from . import _generic_check
from ._mesh_plot import _plot_bsplines_get_dRdZ


# #############################################################################
# #############################################################################
#                           plot matrix
# #############################################################################


def _plot_geometry_matrix_check(
    coll=None,
    key=None,
    indbf=None,
    indchan=None,
    indt=None,
    plot_mesh=None,
    cmap=None,
    vmin=None,
    vmax=None,
    aspect=None,
    dcolorbar=None,
    dleg=None,
    dax=None,
):

    # key
    lk = list(coll.dobj['matrix'].keys())
    key = _generic_check._check_var(
        key, 'key',
        default=None,
        types=str,
        allowed=lk,
    )
    keybs = coll.dobj['matrix'][key]['bsplines']
    refbs = coll.dobj['bsplines'][keybs]['ref']
    keym = coll.dobj['bsplines'][keybs]['mesh']

    # indbf
    if indbf is None:
        indbf = 0
    try:
        assert np.isscalar(indbf)
        indbf = int(indbf)
    except Exception as err:
        msg = (
            f"Arg indbf should be a int!\nProvided: {indt}"
        )
        raise Exception(msg)

    # indchan
    if indchan is None:
        indchan = 0
    try:
        assert np.isscalar(indchan)
        indchan = int(indchan)
    except Exception as err:
        msg = (
            f"Arg indchan should be a int!\nProvided: {indt}"
        )
        raise Exception(msg)

    # indt
    hastime = coll.get_time(key=key)[0]
    if hastime:
        if indt is None:
            indt = 0
        assert np.isscalar(indt), indt
    else:
        indt = None

    # plot_mesh
    plot_mesh = _generic_check._check_var(
        plot_mesh, 'plot_mesh',
        default=coll.dobj[coll._which_mesh][keym]['type'] != 'polar',
        types=bool,
    )

    # cmap
    if cmap is None:
        cmap = 'viridis'

    # vmin, vmax
    if vmax is None:
        vmax = np.nanmax(coll.ddata[key]['data'])
    if vmin is None:
        vmin = 0

    # aspect
    aspect = _generic_check._check_var(
        aspect, 'aspect',
        default='auto',
        types=str,
        allowed=['auto', 'equal'],
    )

    # dcolorbar
    defdcolorbar = {
        # 'location': 'right',
        'fraction': 0.15,
        'orientation': 'vertical',
    }
    dcolorbar = _generic_check._check_var(
        dcolorbar, 'dcolorbar',
        default=defdcolorbar,
        types=dict,
    )

    # dleg
    defdleg = {
        'bbox_to_anchor': (1.1, 1.),
        'loc': 'upper left',
        'frameon': True,
    }
    dleg = _generic_check._check_var(
        dleg, 'dleg',
        default=defdleg,
        types=(bool, dict),
    )

    return (
        key, keybs, keym,
        indbf, indchan, indt,
        plot_mesh,
        cmap, vmin, vmax,
        aspect, dcolorbar, dleg,
    )


def _plot_geometry_matrix_prepare(
    cam=None,
    coll=None,
    key=None,
    keybs=None,
    keym=None,
    indbf=None,
    indchan=None,
    indt=None,
    res=None,
):

    # --------
    # prepare

    # res
    deg = coll.dobj['bsplines'][keybs]['deg']
    km = coll.dobj['bsplines'][keybs]['mesh']
    meshtype = coll.dobj['mesh'][km]['type']

    # if polar => submesh
    km0 = km
    meshtype0 = meshtype
    if meshtype == 'polar':
        km = coll.dobj[coll._which_mesh][km0]['submesh']
        meshtype = coll.dobj[coll._which_mesh][km]['type']
        shape2d = len(coll.dobj['bsplines'][keybs]['shape']) == 2

    # R, Z
    kR, kZ = coll.dobj['mesh'][km]['knots']
    Rk = coll.ddata[kR]['data']
    Zk = coll.ddata[kZ]['data']

    # get dR, dZ
    dR, dZ, _, _ = _plot_bsplines_get_dRdZ(
        coll=coll, km=km, meshtype=meshtype,
    )
    if res is None:
        if meshtype == 'rect':
            res_coef = 0.05
        else:
            res_coef = 0.25
        res = [res_coef*dR, res_coef*dZ]

    # crop
    crop = coll.dobj['matrix'][key]['crop']

    # --------
    # indices

    # indchan => indchan_bf
    if meshtype0 == 'rect':
        ich_bf_tup = coll.select_ind(
            key=keybs,
            returnas='tuple-flat',
            crop=crop,
        )
        nbf = ich_bf_tup[0].size

        # indbf_bool
        indbf_bool = coll.select_ind(
            key=keybs,
            ind=(ich_bf_tup[0][indbf], ich_bf_tup[1][indbf]),
            returnas=bool,
            crop=crop,
        )
        ic = (np.zeros((nbf,), dtype=int), ich_bf_tup[0], ich_bf_tup[1])

    elif meshtype0 == 'tri':
        ich_bf_tup = coll.select_ind(
            key=keybs,
            returnas=int,
            crop=crop,
        )
        nbf = ich_bf_tup.size

        indbf_bool = coll.select_ind(
            key=keybs,
            ind=ich_bf_tup[indbf],
            returnas=bool,
            crop=crop,
        )
        ic = (np.zeros((nbf,), dtype=int), ich_bf_tup)

    else:
        if shape2d:
            ich_bf_tup = coll.select_ind(
                key=keybs,
                returnas='tuple-flat',
                crop=crop,
            )
            nbf = ich_bf_tup[0].size

            # indbf_bool
            indbf_bool = coll.select_ind(
                key=keybs,
                ind=(ich_bf_tup[0][indbf], ich_bf_tup[1][indbf]),
                returnas=bool,
                crop=crop,
            )
            ic = (np.zeros((nbf,), dtype=int), ich_bf_tup[0], ich_bf_tup[1])
        else:
            ich_bf_tup = coll.select_ind(
                key=keybs,
                returnas=int,
                crop=crop,
            )
            nbf = ich_bf_tup.size

            indbf_bool = coll.select_ind(
                key=keybs,
                ind=ich_bf_tup[indbf],
                returnas=bool,
                crop=crop,
            )
            ic = (np.zeros((nbf,), dtype=int), ich_bf_tup)

    # -------------
    # mesh sampling

    # mesh sampling
    km = coll.dobj['bsplines'][keybs]['mesh']
    R, Z = coll.get_sample_mesh(
        key=km, res=res, mode='abs', grid=True, imshow=True,
    )

    # -------------
    # interpolation

    # bsplinetot
    shapebs = coll.dobj['bsplines'][keybs]['shape']
    coefs = np.zeros(tuple(np.r_[1, shapebs]), dtype=float)

    if indt is None:
        coefs[ic] = np.nansum(coll.ddata[key]['data'], axis=0)
    else:
        coefs[ic] = np.nansum(coll.ddata[key]['data'][indt, ...], axis=0)

    bsplinetot = coll.interpolate_profile2d(
        key=keybs,
        R=R,
        Z=Z,
        coefs=coefs,
        indt=indt,
        crop=crop,
        nan0=True,
        details=False,
        return_params=False,
    )[0][0, ...]

    # bspline1
    if indt is None:
        coefs[ic] = coll.ddata[key]['data'][indchan, :]
    else:
        coefs[ic] = coll.ddata[key]['data'][indt, indchan, :]

    bspline1 = coll.interpolate_profile2d(
        key=keybs,
        R=R,
        Z=Z,
        coefs=coefs,
        indt=indt,
        crop=crop,
        nan0=True,
        details=False,
        return_params=False,
    )[0][0, ...]

    # --------
    # LOS

    # los
    ptslos, coefslines, indlosok = None, None, None
    if cam is not None:
        ptslos = cam._get_plotL(return_pts=True, proj='cross', Lplot='tot')
        indsep = np.nonzero(np.isnan(ptslos[0, :]))[0]
        ptslos = np.split(ptslos, indsep, axis=1)
        coefslines = coll.ddata[key]['data'][:, indbf]
        indlosok = np.nonzero(coefslines > 0)[0]
        # normalize for line width
        coefslines = (
            (3. - 0.5) * (coefslines - coefslines.min())
            / (coefslines.max() - coefslines.min()) + 0.5
        )

    # ---------------
    # extent / interp

    # extent and interp
    extent = (
        np.nanmin(Rk) - 0.*dR, np.nanmax(Rk) + 0.*dR,
        np.nanmin(Zk) - 0.*dZ, np.nanmax(Zk) + 0.*dZ,
    )

    if deg == 0:
        interp = 'nearest'
    elif deg == 1:
        interp = 'bilinear'
    elif deg >= 2:
        interp = 'bicubic'

    # matrix refs
    refs = coll.ddata[key]['ref']

    return (
        bsplinetot, bspline1, extent, interp,
        ptslos, coefslines, indlosok, indbf_bool, refs,
    )


def plot_geometry_matrix(
    # resources
    cam=None,
    coll=None,
    # parameters
    key=None,
    indbf=None,
    indchan=None,
    indt=None,
    plot_mesh=None,
    # plotting
    vmin=None,
    vmax=None,
    res=None,
    cmap=None,
    aspect=None,
    dax=None,
    dmargin=None,
    fs=None,
    dcolorbar=None,
    dleg=None,
):

    # --------------
    # check input

    (
        key, keybs, keym,
        indbf, indchan, indt,
        plot_mesh,
        cmap, vmin, vmax,
        aspect, dcolorbar, dleg,
    ) = _plot_geometry_matrix_check(
        coll=coll,
        key=key,
        indbf=indbf,
        indchan=indchan,
        indt=indt,
        plot_mesh=plot_mesh,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        aspect=aspect,
        dcolorbar=dcolorbar,
        dleg=dleg,
        dax=dax,
    )

    # --------------
    #  Prepare data

    (
        bsplinetot, bspline1,
        extent, interp,
        ptslos, coefslines, indlosok,
        ich_bf, refs,
    ) = _plot_geometry_matrix_prepare(
        cam=cam,
        coll=coll,
        key=key,
        keybs=keybs,
        keym=keym,
        indbf=indbf,
        indchan=indchan,
        indt=indt,
        res=res,
    )
    nchan, nbs = coll.ddata[key]['data'].shape[-2:]

    # --------------
    # plot - prepare

    if dax is None:

        if fs is None:
            fs = (16, 9)

        if dmargin is None:
            dmargin = {
                'left': 0.05, 'right': 0.98,
                'bottom': 0.05, 'top': 0.95,
                'hspace': 0.20, 'wspace': 0.25,
            }

        fig = plt.figure(figsize=fs)
        ncols = 4 + (indt is not None)
        gs = gridspec.GridSpec(ncols=ncols, nrows=2, **dmargin)

        # ax01 = matrix
        ax01 = fig.add_subplot(gs[0, 1])
        ax01.set_ylabel(f'channels')
        ax01.set_xlabel(f'basis functions')
        ax01.set_title(key, size=14)
        ax01.tick_params(
            axis="x",
            bottom=False, top=True,
            labelbottom=False, labeltop=True,
        )
        ax01.xaxis.set_label_position('top')

        # ax00 = horizontal
        ax00 = fig.add_subplot(gs[0, 0], sharex=ax01)
        ax00.set_xlabel(f'basis functions')
        ax00.set_ylabel(f'data')
        ax00.set_ylim(vmin, vmax)

        # ax02 = vertical
        ax02 = fig.add_subplot(gs[0, 2], sharey=ax01)
        ax02.set_xlabel(f'channels')
        ax02.set_ylabel(f'data')
        ax02.tick_params(
            axis="x",
            bottom=False, top=True,
            labelbottom=False, labeltop=True,
        )
        ax02.xaxis.set_label_position('top')
        ax02.tick_params(
            axis="y",
            left=False, right=True,
            labelleft=False, labelright=True,
        )
        ax02.yaxis.set_label_position('right')
        ax02.set_xlim(vmin, vmax)

        if indt is not None:
            axt = fig.add_subplot(gs[0, 3], sharey=ax00)
            axt.set_xlabel(f'time')
            axt.set_ylabel(f'data')


        # ax10 = cross1
        ax10 = fig.add_subplot(gs[1, 0], aspect='equal')
        ax10.set_xlabel(f'R (m)')
        ax10.set_ylabel(f'Z (m)')

        # ax11 = crosstot
        ax11 = fig.add_subplot(
            gs[1, 1],
            aspect='equal',
            sharex=ax10,
            sharey=ax10,
        )
        ax11.set_xlabel(f'R (m)')
        ax11.set_ylabel(f'Z (m)')

        # ax12 = cross2
        ax12 = fig.add_subplot(
            gs[1, 2],
            aspect='equal',
            sharex=ax10,
            sharey=ax10,
        )
        ax12.set_xlabel(f'R (m)')
        ax12.set_ylabel(f'Z (m)')

        # text
        axt0 = fig.add_subplot(gs[0, -1], frameon=False)
        axt0.set_xticks([])
        axt0.set_yticks([])
        axt1 = fig.add_subplot(gs[1, -1], frameon=False)
        axt1.set_xticks([])
        axt1.set_yticks([])

        # define dax
        dax = {
            # matrix
            'matrix': {'handle': ax01, 'inverty': True},
            'vertical': {'handle': ax02, 'type': 'misc'},
            'horizontal': {'handle': ax00, 'type': 'misc'},
            # cross-section
            'cross1': {'handle': ax10, 'type': 'cross'},
            'cross2': {'handle': ax12, 'type': 'cross'},
            'crosstot': {'handle': ax11, 'type': 'cross'},
            # text
            'text0': {'handle': axt0, 'type': 'text'},
            'text1': {'handle': axt1, 'type': 'text'},
        }
        if indt is not None:
            dax['traces'] = {'handle': axt, 'type': 'misc'}

    dax = _generic_check._check_dax(dax=dax, main='matrix')

    # --------------
    # plot mesh

    if plot_mesh is True:
        _ = coll.plot_mesh(
            key=keym, dax=dax, crop=True, dleg=False,
        )

    # --------------
    # plot matrix

    if indt is None:
        ind = [indbf, indchan]
        keyX = refs[1]
        keyY = refs[0]
        keyZ = None
    else:
        ind = [indbf, indchan, indt]
        keyX = refs[2]
        keyY = refs[1]
        keyZ = refs[0]

    coll2, dgroup = coll.plot_as_array(
        key=key,
        keyX=keyX,
        keyY=keyY,
        keyZ=keyZ,
        dax=dax,
        ind=ind,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        aspect=aspect,
        connect=False,
    )

    kax = 'cross1'
    if dax.get(kax) is not None:
        ax = dax[kax]['handle']

        im = ax.imshow(
            bspline1,
            extent=extent,
            interpolation=interp,
            origin='lower',
            aspect='equal',
            cmap=cmap,
            vmin=0,
            vmax=None,
        )

        if ptslos is not None:
            ax.plot(
                ptslos[indchan][0, :],
                ptslos[indchan][1, :],
                ls='-',
                lw=1.,
                color='k',
            )

    kax = 'cross2'
    if dax.get(kax) is not None:
        ax = dax[kax]['handle']

        coll.plot_bsplines(
            key=keybs,
            indbs=ich_bf,
            indt=indt,
            knots=False,
            cents=False,
            plot_mesh=False,
            dax={'cross': dax[kax]},
            dleg=False,
        )

        if ptslos is not None:
            for ii in indlosok:
                ax.plot(
                    ptslos[ii][0, :],
                    ptslos[ii][1, :],
                    ls='-',
                    lw=coefslines[ii],
                    color='k',
                )

    kax = 'crosstot'
    if dax.get(kax) is not None:
        ax = dax[kax]['handle']

        im = ax.imshow(
            bsplinetot,
            extent=extent,
            interpolation=interp,
            origin='lower',
            aspect='equal',
            cmap=cmap,
            vmin=0,
            vmax=None,
        )

    # --------------
    # dleg

    # if dleg is not False:
        # dax['cross'].legend(**dleg)

    # -------
    # connect

    coll2.setup_interactivity(kinter='inter0', dgroup=dgroup)
    coll2.disconnect_old()
    coll2.connect()
    coll2.show_commands()

    return coll2
