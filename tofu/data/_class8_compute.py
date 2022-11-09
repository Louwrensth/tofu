# -*- coding: utf-8 -*-


import copy
import itertools as itt

import numpy as np
import scipy.interpolate as scpinterp
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors


import datastock as ds


from. import _utils_surface3d


# ##################################################################
# ##################################################################
#                   optics outline
# ##################################################################


def get_optics_outline(
    coll=None,
    key=None,
    add_points=None,
    mode=None,
    closed=None,
    ravel=None,
    total=None,
):

    # ------------
    # check inputs

    # key, cls
    key, cls = coll.get_optics_cls(optics=key)
    key, cls = key[0], cls[0]
    dgeom = coll.dobj[cls][key]['dgeom']

    # total
    total = ds._generic_check._check_var(
        total, 'total',
        types=bool,
        default=(cls == 'camera' and dgeom['type'] == '2d'),
    )
    if cls == 'camera' and dgeom['type'] != '2d':
        total = False

    # --------
    # compute

    if dgeom['type'] == '3d':
        return None, None

    if cls == 'camera' and total:
        # get centers
        cx0, cx1 = dgeom['cents']
        cx0 = coll.ddata[cx0]['data']
        cx1 = coll.ddata[cx1]['data']

        # derive half-spacing
        dx0 = np.mean(np.diff(cx0)) / 2.
        dx1 = np.mean(np.diff(cx1)) / 2.

        # derive global outline (not pixel outline)
        p0 = np.r_[
            cx0[0] - dx0, cx0[-1] + dx0,
            cx0[-1] + dx0, cx0[0] - dx0,
        ]
        p1 = np.r_[
            cx1[0] - dx1, cx1[0] - dx1,
            cx1[-1] + dx1, cx1[-1] + dx1,
        ]

    else:
        out = dgeom['outline']
        p0 = coll.ddata[out[0]]['data']
        p1 = coll.ddata[out[1]]['data']

    # -----------
    # add_points

    return _interp_poly(
        lp=[p0, p1],
        add_points=add_points,
        mode=mode,
        isclosed=False,
        closed=closed,
        ravel=ravel,
    )


# ##################################################################
# ##################################################################
#                   optics poly
# ##################################################################


def get_optics_poly(
    coll=None,
    key=None,
    add_points=None,
    mode=None,
    closed=None,
    ravel=None,
    total=None,
    return_outline=None,
):

    # ------------
    # check inputs

    key, cls = coll.get_optics_cls(optics=key)
    key, cls = key[0], cls[0]

    return_outline = ds._generic_check._check_var(
        return_outline, 'return_outline',
        types=bool,
        default=False,
    )

    ravel = ds._generic_check._check_var(
        ravel, 'ravel',
        default=False,
        types=bool,
    )

    # --------
    # compute

    dgeom = coll.dobj[cls][key]['dgeom']
    if cls in ['aperture', 'filter', 'crystal', 'grating']:

        if dgeom['type'] != '3d':
            p0, p1 = coll.get_optics_outline(
                key=key,
                add_points=add_points,
                mode=mode,
                closed=closed,
                ravel=ravel,
                total=total,
            )

            px, py, pz = _utils_surface3d._get_curved_poly(
                gtype=dgeom['type'],
                outline_x0=p0,
                outline_x1=p1,
                curve_r=dgeom['curve_r'],
                cent=dgeom['cent'],
                nin=dgeom['nin'],
                e0=dgeom['e0'],
                e1=dgeom['e1'],
            )

        else:
            px, py, pz = dgeom['poly']
            px = coll.ddata[px]['data']
            py = coll.ddata[py]['data']
            pz = coll.ddata[pz]['data']

    elif cls == 'camera':

        p0, p1 = coll.get_optics_outline(
            key=key,
            add_points=add_points,
            mode=mode,
            closed=closed,
            ravel=ravel,
            total=total,
        )

        # vectors
        dv = coll.get_camera_unit_vectors(key)
        lv = ['e0_x', 'e0_y', 'e0_z', 'e1_x', 'e1_y', 'e1_z']
        e0x, e0y, e0z, e1x, e1y, e1z = [dv[k0] for k0 in lv]
        if not np.isscalar(e0x):
            e0x = e0x[:, None]
            e0y = e0y[:, None]
            e0z = e0z[:, None]
            e1x = e1x[:, None]
            e1y = e1y[:, None]
            e1z = e1z[:, None]

        if dgeom['type'] == '2d' and total:
            cx, cy, cz = dgeom['cent']
            p02, p12 = p0, p1
        else:
            cx, cy, cz = coll.get_camera_cents_xyz(key)
            shape = [1 for ii in range(cx.ndim)] + [p0.size]
            cx, cy, cz = cx[..., None], cy[..., None], cz[..., None]
            p02 = p0.reshape(shape)
            p12 = p1.reshape(shape)

        # make 3d
        px = cx + p02 * e0x + p12 * e1x
        py = cy + p02 * e0y + p12 * e1y
        pz = cz + p02 * e0z + p12 * e1z

    # ----------
    # ravel

    if ravel is True and px.ndim > 1:
        nan = np.full(tuple(np.r_[px.shape[:-1], 1]), np.nan)
        px = np.concatenate((px, nan), axis=-1).ravel()
        py = np.concatenate((py, nan), axis=-1).ravel()
        pz = np.concatenate((pz, nan), axis=-1).ravel()

    # return
    if return_outline is True:
        return p0, p1, px, py, pz
    else:
        return px, py, pz


# ##################################################################
# ##################################################################
#                   Poly interpolation utilities
# ##################################################################


def _interp_poly_check(
    add_points=None,
    mode=None,
    closed=None,
    ravel=None,
):

    # -------
    # mode

    mode = ds._generic_check._check_var(
        mode, 'mode',
        default=None,
        allowed=[None, 'min'],
    )

    # ----------
    # add_points

    defadd = 1 if mode == 'min' else 0
    add_points = ds._generic_check._check_var(
        add_points, 'add_points',
        types=int,
        default=defadd,
        sign='>= 0',
    )

    # -------
    # closed

    closed = ds._generic_check._check_var(
        closed, 'closed',
        default=False,
        types=bool,
    )

    # -------
    # ravel

    ravel = ds._generic_check._check_var(
        ravel, 'ravel',
        default=False,
        types=bool,
    )
    return add_points, mode, closed, ravel


def _interp_poly(
    lp=None,
    add_points=None,
    mode=None,
    isclosed=None,
    closed=None,
    ravel=None,
    min_threshold=1.e-6,
):

    # ------------
    # check inputs

    add_points, mode, closed, ravel = _interp_poly_check(
        add_points=add_points,
        mode=mode,
        closed=closed,
        ravel=ravel,
    )

    # ------------
    # trivial case

    if add_points == 0:
        return lp

    # ------------
    # compute

    # close for interpolation
    if isclosed is not True:
        for ii, pp in enumerate(lp):

            if pp is None:
                continue

            if pp.ndim == 2:
                lp[ii] = np.concatenate((pp, pp[:, 0:1]), axis=1)
            else:
                lp[ii] = np.append(pp, pp[0])

    # -----------
    # mode

    if mode == 'min':
        if len(lp) == 3:
            dist = np.sqrt(
                np.diff(lp[0], axis=-1)**2
                + np.diff(lp[1], axis=-1)**2
                + np.diff(lp[2], axis=-1)**2
            )
        elif len(lp) == 2:
            dist = np.sqrt(
                np.diff(lp[0], axis=-1)**2
                + np.diff(lp[1], axis=-1)**2
            )

        if dist.ndim == 2:
            import pdb; pdb.set_trace()     # DB

        min_threshold = min(min_threshold, np.max(dist)/3.)
        mindist = np.min(dist[dist > min_threshold])
        add_points = add_points * np.ceil(dist / mindist).astype(int) - 1

    # -----------
    # add_points

    shape = [pp for pp in lp if pp is not None][0].shape
    nb = shape[-1]
    if np.isscalar(add_points):
        add_points = np.full((nb-1,), add_points, dtype=int)

    # -----------
    # indices

    ind0 = np.arange(0, nb)
    ind = np.concatenate(tuple([
        np.linspace(
            ind0[ii],
            ind0[ii+1],
            2 + add_points[ii],
            endpoint=True,
        )[:-1]
        for ii in range(nb-1)
    ] + [[ind0[-1]]]))

    # -----------
    # interpolate

    for ii, pp in enumerate(lp):

        if pp is None:
            continue

        lp[ii] = scpinterp.interp1d(
            ind0, pp, kind='linear', axis=-1,
        )(ind)

    # ------------
    # closed

    if closed is False:

        for ii, pp in enumerate(lp):
            if pp is None:
                continue

            if pp.ndim == 2:
                lp[ii] = pp[:, :-1]
            else:
                lp[ii] = pp[:-1]

    # ------------
    # ravel

    if ravel and len(shape) == 2:
        nan = np.full((pp.shape[0], 1), np.nan)
        for ii, pp in enumerate(lp[2:]):
            lp[ii+2] = np.concatenate((pp, nan), axis=1).ravel()
    return lp


# ##################################################################
# ##################################################################
#                       dplot
# ##################################################################


def _dplot_check(
    coll=None,
    key=None,
    key_cam=None,
    optics=None,
    elements=None,
    vect_length=None,
    axis_length=None,
):
    # -----
    # key

    key, key_cam = coll.get_diagnostic_cam(key, key_cam)

    # ------
    # optics

    if isinstance(optics, str):
        optics = [optics]

    lok = list(itt.chain.from_iterable([
        [k0] + v0['optics']
        for k0, v0 in coll.dobj['diagnostic'][key]['doptics'].items()
    ]))
    optics = ds._generic_check._check_var_iter(
        optics, 'optics',
        default=lok,
        allowed=lok,
    )

    # -------
    # elements

    lok = ['o', 'c', 'v', 'r']
    elements = ds._generic_check._check_var_iter(
        elements, 'elements',
        types=str,
        types_iter=str,
        default=''.join(lok),
        allowed=lok,
    )

    # -----------
    # vect_length

    vect_length = ds._generic_check._check_var(
        vect_length, 'vect_length',
        default=0.2,
        types=(float, int),
        sign='>= 0.'
    )

    # -----------
    # axis_length

    axis_length = ds._generic_check._check_var(
        axis_length, 'axis_length',
        default=1.,
        types=(float, int),
        sign='>= 0.'
    )

    return key, key_cam, optics, elements, vect_length, axis_length


def _dplot(
    coll=None,
    key=None,
    key_cam=None,
    optics=None,
    elements=None,
    vect_length=None,
    axis_length=None,
):

    # ------------
    # check inputs

    key, key_cam, optics, elements, vect_length, axis_length = _dplot_check(
        coll=coll,
        key=key,
        key_cam=key_cam,
        optics=optics,
        elements=elements,
        vect_length=vect_length,
        axis_length=axis_length,
    )

    # ------------
    # build dict

    dlw = {
        'camera': 2,
        'aperture': 1.,
        'filter': 1.,
        'crystal': 1.,
        'grating': 1.,
    }
    dplot = {k0: {} for k0 in optics}
    for k0 in optics:

        if k0 in coll.dobj.get('camera', []):
            cls = 'camera'
        elif k0 in coll.dobj.get('aperture', []):
            cls = 'aperture'
        elif k0 in coll.dobj.get('filter', []):
            cls = 'filter'
        elif k0 in coll.dobj.get('crystal', []):
            cls = 'crystal'
        elif k0 in coll.dobj.get('grating', []):
            cls = 'grating'
        else:
            msg = f"Unknown optics '{k0}'"
            raise Exception(msg)

        v0 = coll.dobj[cls][k0]['dgeom']
        color = coll.dobj[cls][k0]['dmisc']['color']

        # -----------
        # prepare data

        # cent
        if 'c' in elements or 'v' in elements or 'r' in elements:
            if v0.get('cent') is not None:
                cx, cy, cz = v0['cent'][:, None]
            elif 'cents' in v0.keys():
                cx, cy, cz = v0['cents']
                cx = coll.ddata[cx]['data']
                cy = coll.ddata[cy]['data']
                cz = coll.ddata[cz]['data']
            cr = np.hypot(cx, cy)

        # vectors
        if 'v' in elements or 'r' in elements:
            ninx, niny, ninz = v0['nin']
            e0x, e0y, e0z = v0['e0']
            e1x, e1y, e1z = v0['e1']
            if isinstance(ninx, str):
                vinx = coll.ddata[ninx]['data'] * vect_length
                viny = coll.ddata[niny]['data'] * vect_length
                vinz = coll.ddata[ninz]['data'] * vect_length
                v0x = coll.ddata[e0x]['data'] * vect_length
                v0y = coll.ddata[e0y]['data'] * vect_length
                v0z = coll.ddata[e0z]['data'] * vect_length
                v1x = coll.ddata[e1x]['data'] * vect_length
                v1y = coll.ddata[e1y]['data'] * vect_length
                v1z = coll.ddata[e1z]['data'] * vect_length
            else:
                vinx, viny, vinz = np.r_[ninx, niny, ninz] * vect_length
                v0x, v0y, v0z = np.r_[e0x, e0y, e0z] * vect_length
                v1x, v1y, v1z = np.r_[e1x, e1y, e1z] * vect_length

        # radius
        if 'r' in elements and v0['type'] not in ['planar', '1d', '2d', '3d']:
            if v0['type'] == 'cylindrical':
                icurv = (np.isfinite(v0['curve_r'])).nonzero()[0][0]
                rc = v0['curve_r'][icurv]
                eax = [(e0x, e0y, e0z), (e1x, e1y, e1z)][1 - icurv]
            elif v0['type'] == 'spherical':
                rc = v0['curve_r'][0]
            elif v0['type'] == 'toroidal':
                imax = np.argmax(v0['curve_r'])
                imin = 1 - imax
                rmax = v0['curve_r'][imax]
                rmin = v0['curve_r'][imin]
                emax = [(e0x, e0y, e0z), (e1x, e1y, e1z)][imax]
            # extenthalf = v0['extenthalf']

        # -----------------
        # get plotting data

        # outline
        if 'o' in elements:

            p0, p1, px, py, pz = coll.get_optics_poly(
                key=k0,
                add_points=3,
                closed=True,
                ravel=True,
                return_outline=True,
                total=True,
            )

            dplot[k0]['o'] = {
                'x0': p0,
                'x1': p1,
                'x': px,
                'y': py,
                'z': pz,
                'r': np.hypot(px, py),
                'props': {
                    'label': f'{k0}-o',
                    'lw': dlw[cls],
                    'c': color,
                },
            }

        # center
        if 'c' in elements:

            dplot[k0]['c'] = {
                'x': cx,
                'y': cy,
                'z': cz,
                'r': cr,
                'props': {
                    'label': f'{k0}-o',
                    'ls': 'None',
                    'marker': 'o',
                    'ms': 4,
                    'c': color,
                },
            }

        # unit vectors
        if 'v' in elements:

            vinr = np.hypot(cx + vinx, cy + viny) - cr
            v0r = np.hypot(cx + v0x, cy + v0y) - cr
            v1r = np.hypot(cx + v1x, cy + v1y) - cr

            # dict

            dplot[k0]['v-nin'] = {
                'x': cx,
                'y': cy,
                'z': cz,
                'r': cr,
                'ux': vinx,
                'uy': viny,
                'uz': vinz,
                'ur': vinr,
                'props': {
                    'label': f'{k0}-nin',
                    'fc': 'r',
                    'color': 'r',
                },
            }

            dplot[k0]['v-e0'] = {
                'x': cx,
                'y': cy,
                'z': cz,
                'r': cr,
                'ux': v0x,
                'uy': v0y,
                'uz': v0z,
                'ur': v0r,
                'props': {
                    'label': f'{k0}-e0',
                    'fc': 'g',
                    'color': 'g',
                },
            }

            dplot[k0]['v-e1'] = {
                'x': cx,
                'y': cy,
                'z': cz,
                'r': cr,
                'ux': v1x,
                'uy': v1y,
                'uz': v1z,
                'ur': v1r,
                'props': {
                    'label': f'{k0}-e1',
                    'fc': 'b',
                    'color': 'b',
                },
            }

        # rowland / axis for curved optics
        if 'r' in elements and cls in ['crystal', 'grating']:

            if v0['type'] not in ['cylindrical', 'spherical', 'toroidal']:
                continue

            theta = np.linspace(-1, 1, 50) * np.pi
            if v0['type'] == 'cylindrical':
                c2x = cx + ninx * rc
                c2y = cy + niny * rc
                c2z = cz + ninz * rc
                px = c2x + np.r_[-1, 1] * axis_length * eax[0]
                py = c2y + np.r_[-1, 1] * axis_length * eax[1]
                pz = c2z + np.r_[-1, 1] * axis_length * eax[2]

                lab = f'{k0}-axis',

            elif v0['type'] == 'spherical':
                c2x = cx + ninx * 0.5 * rc
                c2y = cy + niny * 0.5 * rc
                c2z = cz + ninz * 0.5 * rc
                px = (
                    c2x
                    + 0.5 * rc * np.cos(theta) * (-ninx)
                    + 0.5 * rc * np.sin(theta) * e0x
                )
                py = (
                    c2y
                    + 0.5 * rc * np.cos(theta) * (-niny)
                    + 0.5 * rc * np.sin(theta) * e0y
                )
                pz = (
                    c2z
                    + 0.5 * rc * np.cos(theta) * (-ninz)
                    + 0.5 * rc * np.sin(theta) * e0z
                )

                lab = f'{k0}-rowland',

            elif v0['type'] == 'toroidal':
                c2x = cx + ninx * (rmin + rmax)
                c2y = cy + niny * (rmin + rmax)
                c2z = cz + ninz * (rmin + rmax)
                px = (
                    c2x
                    + rmax * np.cos(theta) * (-ninx)
                    + rmax * np.sin(theta) * emax[0]
                )
                py = (
                    c2y
                    + rmax * np.cos(theta) * (-niny)
                    + rmax * np.sin(theta) * emax[1]
                )
                pz = (
                    c2z
                    + rmax * np.cos(theta) * (-ninz)
                    + rmax * np.sin(theta) * emax[2]
                )

                lab = f'{k0}-majorR'

            dplot[k0]['r'] = {
                'x': px,
                'y': py,
                'z': pz,
                'r': np.hypot(px, py),
                'props': {
                    'label': lab,
                    'ls': '--',
                    'lw': 1.,
                    'color': color,
                },
            }

    return dplot


# ##################################################################
# ##################################################################
#                   Wavelength from angle
# ##################################################################


def get_lamb_from_angle(
    coll=None,
    key=None,
    key_cam=None,
    lamb=None,
    rocking_curve=None,
):
    """"""

    # ----------
    # check

    # key
    lok = list(coll.dobj.get('diagnostic', {}).keys())
    key = ds._generic_check._check_var(
        key, 'key',
        types=str,
        allowed=lok,
    )
    
    # key_cam
    lok = list(coll.dobj['diagnostic'][key]['doptics'].keys())
    key_cam = ds._generic_check._check_var(
        key_cam, 'key_cam',
        types=str,
        allowed=lok,
    )
    
    # doptics
    doptics = coll.dobj['diagnostic'][key]['doptics'][key_cam]
    if 'crystal' not in doptics['cls']:
        raise Exception(f"Diag '{key}' is not a spectro!")

    kcryst = doptics['optics'][doptics['cls'].index('crystal')]

    dok = {
        'lamb': 'alpha',
        'lambmin': 'amin',
        'lambmax': 'amax',
        'res': 'res',
    }
    lok = list(dok.keys())
    lamb = ds._generic_check._check_var(
        lamb, 'lamb',
        types=str,
        allowed=lok,
    )

    # ----------
    # compute

    lv = []
    lk = ['lamb', 'lambmin', 'lambmax']
    for kk in lk:
        if lamb in [kk, 'res']:
            
            if kk == 'lamb':
                klos = coll.dobj['diagnostic'][key]['doptics'][key_cam]['los']
                ka = coll.dobj['rays'][klos][dok[kk]]
                ang = coll.ddata[ka]['data'][0, ...]
                ref = coll.ddata[ka]['ref'][1:]
            else:
                ka = coll.dobj['diagnostic'][key]['doptics'][key_cam][dok[kk]]
                ang = coll.ddata[ka]['data']
                ref = coll.ddata[ka]['ref']
                
            dd = coll.get_crystal_bragglamb(
                key=kcryst,
                bragg=ang,
                rocking_curve=rocking_curve,
            )[1]
            if lamb == kk:
                data = dd
            else:
                lv.append(dd)

    if lamb == 'res':
        data = lv[0] / (lv[2] - lv[1])

    return data, ref


# ##################################################################
# ##################################################################
#                   get data
# ##################################################################


def _get_data(
    coll=None,
    key=None,
    key_cam=None,
    data=None,
    rocking_curve=None,
    **kwdargs,
    ):
    
    # key, key_cam
    key, key_cam = coll.get_diagnostic_cam(key=key, key_cam=key_cam)
    spectro = coll.dobj['diagnostic'][key]['spectro']
    # is2d = coll.dobj['diagnostic'][key]['is2d']
    
    # basic check on data
    if data is not None:
        lquant = ['etendue', 'amin', 'amax']  # 'los'
        lcomp = ['tangency radius']
        if spectro:
            lcomp += ['lamb', 'lambmin', 'lambmax', 'res']
    
        data = ds._generic_check._check_var(
            data, 'data',
            types=str,
            allowed=lquant + lcomp,
        )

    # build ddata
    ddata = {}
    # comp = False
    if data is None or data in lquant:
    
        # --------------------------
        # data is None => kwdargs
    
        if data is None:
            # check kwdargs
            dparam = coll.get_param(which='data', returnas=dict)
            lkout = [k0 for k0 in kwdargs.keys() if k0 not in dparam.keys()]
            
            if len(lkout) > 0:
                msg= (
                    "The following args correspond to no data parameter:\n"
                    + "\n".join([f"\t- {k0}" for k0 in lkout])
                )
                raise Exception(msg)
            
            # list all available data
            lok = [
                k0 for k0, v0 in coll.ddata.items()
                if v0.get('camera') in key_cam
            ]
            
            # Adjust with kwdargs
            if len(kwdargs) > 0:
                lok2 = coll.select(
                    which='data', log='all', returnas=str, **kwdargs,
                )
                lok = [k0 for k0 in lok2 if k0 in lok]
                
            # check there is 1 data per cam
            lcam = [
                coll.ddata[k0]['camera'] for k0 in lok
                if coll.ddata[k0]['camera'] in key_cam
            ]
            
            if len(set(lcam)) > len(key_cam):
                msg = (
                    "There are more / less data identified than cameras:\n"
                    f"\t- key_cam:  {key_cam}\n"
                    f"\t- data cam: {lcam}\n"
                    f"\t- data: {data}"
                )
                raise Exception(msg)
            elif len(set(lcam)) < len(key_cam):
                pass
            
            # reorder
            ddata = {
                cc: lok[lcam.index(cc)]
                for cc in key_cam if cc in lcam
            }
                
        # -----------------
        # data in lquant
        
        elif data in lquant:
            for cc in key_cam:
                # if data == 'los':
                #     kr = coll.dobj['diagnostic'][key]['doptics'][cc][data]
                #     dd = coll.dobj['rays'][kr]['pts']
                # else:
                dd = coll.dobj['diagnostic'][key]['doptics'][cc][data]
                lc = [
                    isinstance(dd, str) and dd in coll.ddata.keys(),
                    # isinstance(dd, tuple)
                    # and all([isinstance(di, str) for di in dd])
                    # and all([di in coll.ddata.keys() for di in dd])
                ]
                if lc[0]:
                    ddata[cc] = dd
                # elif lc[1]:
                #     ddata[cc] = list(dd)
                elif dd is None:
                    pass
                else:
                    msg = f"Unknown data: '{data}'"
                    raise Exception(msg)
        
        # dref
        dref = {
            k0: coll.ddata[v0]['ref']
            for k0, v0 in ddata.items()
        } 
        
        # get actual data
        ddata = {
            k0 : coll.ddata[v0]['data']
            for k0, v0 in ddata.items()
        }
 
    # --------------------
    # data to be computed 
       
    elif data in lcomp:
        
        # comp = True
        ddata = {}
        dref = {}
        
        if data in ['lamb', 'lambmin', 'lambmax', 'res']:
            for cc in key_cam: 
               ddata[cc], dref[cc] = coll.get_diagnostic_lamb(
                   key=key,
                   key_cam=cc,
                   rocking_curve=rocking_curve,
                   lamb=data,
               )
           
        elif data == 'tangency radius':
            for cc in key_cam: 
                ddata[cc], _, dref[cc] = coll.get_rays_tangency_radius(
                    key=key,
                    key_cam=cc,
                    segment=-1,
                    lim_to_segments=False,
                )

    return ddata, dref


# ##################################################################
# ##################################################################
#                   concatenate data
# ##################################################################


def _concatenate_check(
    coll=None,
    key=None,
    key_cam=None,
    data=None,
    rocking_curve=None,
    returnas=None,
    # naming
    key_data=None,
    key_ref=None,
    **kwdargs,
    ):
    
    # -------------
    # key, key_cam
    # -------------
    
    key, key_cam = coll.get_diagnostic_cam(key=key, key_cam=key_cam)
    spectro = coll.dobj['diagnostic'][key]['spectro']
    is2d = coll.dobj['diagnostic'][key]['is2d']
    # stack = coll.dobj['diagnostic'][key]['stack']
    
    if is2d and len(key_cam) > 1:
        msg = (
            "Cannot yet concatenate several 2d cameras\n"
            "\t- key: '{key}'\n"
            "\t- is2d: {is2d}\n"
            "\t- key_cam: {key_cam}\n"
        )
        raise NotImplementedError(msg)
    
    # ---------------
    # build ddata
    # -------------
    
    # basic check on data
    if data is not None:
        lquant = ['los', 'etendue', 'amin', 'amax']
        lcomp = ['tangency radius']
        if spectro:
            lcomp += ['lamb', 'lambmin', 'lambmax', 'res']
    
        data = ds._generic_check._check_var(
            data, 'data',
            types=str,
            allowed=lquant + lcomp,
        )

    # build ddata
    ddata = {}
    comp = False
    if data is None or data in lquant:
    
        # --------------------------
        # data is None => kwdargs
    
        if data is None:
            # check kwdargs
            dparam = coll.get_param(which='data', returnas=dict)
            lkout = [k0 for k0 in kwdargs.keys() if k0 not in dparam.keys()]
            
            if len(lkout) > 0:
                msg= (
                    "The following args correspond to no data parameter:\n"
                    + "\n".join([f"\t- {k0}" for k0 in lkout])
                )
                raise Exception(msg)
            
            # list all available data
            lok = [
                k0 for k0, v0 in coll.ddata.items()
                if v0.get('camera') in key_cam
            ]
            
            # Adjust with kwdargs
            if len(kwdargs) > 0:
                lok2 = coll.select(
                    which='data', log='all', returnas=str, **kwdargs,
                )
                lok = [k0 for k0 in lok2 if k0 in lok]
                
            # check there is 1 data per cam
            lcam = [
                coll.ddata[k0]['camera'] for k0 in lok
                if coll.ddata[k0]['camera'] in key_cam
            ]
            
            if len(set(lcam)) > len(key_cam):
                msg = (
                    "There are more / less data identified than cameras:\n"
                    f"\t- key_cam:  {key_cam}\n"
                    f"\t- data cam: {lcam}\n"
                    f"\t- data: {data}"
                )
                raise Exception(msg)
            elif len(set(lcam)) < len(key_cam):
                pass
            
            # reorder
            ddata = {
                cc: [lok[lcam.index(cc)]]
                for cc in key_cam if cc in lcam
            }
                
        # -----------------
        # data in lquant
        
        elif data in lquant:
            for cc in key_cam:
                if data == 'los':
                    kr = coll.dobj['diagnostic'][key]['doptics'][cc][data]
                    dd = coll.dobj['rays'][kr]['pts']
                else:
                    dd = coll.dobj['diagnostic'][key]['doptics'][cc][data]
                lc = [
                    isinstance(dd, str) and dd in coll.ddata.keys(),
                    isinstance(dd, tuple)
                    and all([isinstance(di, str) for di in dd])
                    and all([di in coll.ddata.keys() for di in dd])
                ]
                if lc[0]:
                    ddata[cc] = [dd]
                elif lc[1]:
                    ddata[cc] = list(dd)
                elif dd is None:
                    pass
                else:
                    msg = f"Unknown data: '{data}'"
                    raise Exception(msg)         
       
        # dref
        dref = {
            k0: [coll.ddata[k1]['ref'] for k1 in v0]
            for k0, v0 in ddata.items()
        }
        
    # --------------------
    # data to be computed 
       
    # TBF
    elif data in lcomp:
        
        comp = True
        ddata = {[None] for cc in key_cam}
        dref = {[None] for cc in key_cam}
        
        if data in ['lamb', 'lambmin', 'lambmax', 'res']:
            for cc in key_cam: 
               ddata[cc][0], dref[cc][0] = coll.get_diagnostic_lamb(
                   key=key,
                   key_cam=cc,
                   rocking_curve=rocking_curve,
                   lamb=data,
               )
           
        elif data == 'tangency radius':
            ddata[cc][0], _, dref[cc][0] = coll.get_rays_tangency_radius(
                key=key,
                key_cam=key_cam,
                segment=-1,
                lim_to_segments=False,
            )

    # -----------------------------------
    # Final safety checks and adjustments
    # -----------------------------------
    
    # adjust key_cam
    key_cam = [cc for cc in key_cam if cc in ddata.keys()]

    # ddata vs dref vs key_cam
    lcd = sorted(list(ddata.keys()))
    lcr = sorted(list(dref.keys()))
    if not (sorted(key_cam) == lcd == lcr):
        msg = (
            "Wrong keys!\n"
            f"\t- key_cam: {key_cam}\n"
            f"\t- ddata.keys(): {lcd}\n"
            f"\t- dref.keys(): {lcr}\n"
        )
        raise Exception(msg)

    # nb of data per cam
    ln = [len(v0) for v0 in ddata.values()]
    if len(set(ln)) != 1:
        msg = (
            "Not the same number of data per cameras!\n"
            + str(ddata)
        )
        raise Exception(msg)

    # check shapes and ndim
    dshapes = {
        k0: [tuple([coll.dref[k2]['size'] for k2 in k1]) for k1 in v0]
        for k0, v0 in dref.items()
    }
    
    # all same ndim
    ndimref = None
    for k0, v0 in dshapes.items():
        lndim = [len(v1) for v1 in v0]
        if len(set(lndim)) > 1:
            msg = "All data must have same number of dimensions!\n{dshapes}"
            raise Exception(msg)
        if ndimref is None:
            ndimref = lndim[0]
        elif lndim[0] != ndimref:
            msg = "All data must have same number of dimensions!\n{dshapes}"
            raise Exception(msg)
 
    # check indices of camera ref in data ref
    indref = None
    for k0, v0 in dref.items():
        for v1 in v0:
            ind = [v1.index(rr) for rr in coll.dobj['camera'][k0]['dgeom']['ref']]
            if indref is None:
                indref = ind
            elif ind != indref:
                msg = "All data must have same index of cam ref!\n{drf}"
                raise Exception(msg)
                
    if len(indref) > 1:
        msg = "Cannot conatenate 2d cameras so far"
        raise Exception(msg)

    # check all shapes other than camera shapes are identical
    if ndimref > len(indref):
        ind = np.delete(np.arange(0, ndimref), indref)
        shape0 = tuple(np.r_[dshapes[key_cam[0]][0]][ind])
        lcout = [
            cc for cc in key_cam
            if any([tuple(np.r_[vv][ind]) != shape0 for vv in dshapes[cc]])
        ]
        if len(lcout) > 0:
            msg = (
                "The cameras data shall all have same shape (except pixels)\n"
                + str(dshapes)
            )
            raise Exception(msg)
            
    # check indices of camera ref in data ref
    ref = None
    for k0, v0 in dref.items():
        for v1 in v0:
            if ref is None:
                ref = [
                    None if ii == indref[0] else rr
                    for ii, rr in enumerate(v1)
                ]
            else:
                lc = [
                    v1[ii] == ref[ii] for ii in range(ndimref)
                    if ii not in indref
                ]
                if not all(lc):
                    msg = (
                        "All ref axcept the camera ref must be the same!\n"
                        f"\t- ref: {ref}\n"
                        f"\t- indref: {indref}\n"
                        f"\t- ndimref: {ndimref}\n"
                        f"\t- v1: {v1}\n"
                        f"\t- lc: {lc}\n"
                        + str(dref)
                    )
                    raise Exception(msg)

    # -----------------------------------
    # keys for new data and ref
    # -----------------------------------

    if key_data is None:
        if data in lquant + lcomp:
            if data == 'los':
                key_data = [
                    f'{key}_los_ptsx',
                    f'{key}_los_ptsy',
                    f'{key}_los_ptsz',
                ]
            else:
                key_data = [f'{key}_{data}']
        else:
            key_data = [f'{key}_data']
    elif isinstance(key_data, str):
        key_data = [key_data]
            
    if key_ref is None:
        key_ref = f'{key}_npix'

    ref = tuple([key_ref if rr is None else rr for rr in ref])

    # -----------------------------------
    # Other variables
    # -----------------------------------

    # returnas
    returnas = ds._generic_check._check_var(
        returnas, 'returnas',
        default='Datastock',
        allowed=[dict, 'Datastock'],
    )

    return (
        key, key_cam, is2d,
        ddata, ref, comp,
        dshapes, ndimref, indref,
        key_data, key_ref,
        returnas,
    )


# TBF
def _concatenate_data(
    coll=None,
    key=None,
    key_cam=None,
    data=None,
    rocking_curve=None,
    returnas=None,
    # naming
    key_data=None,
    key_ref=None,
    **kwdargs,
    ):
    
    # --------------------
    # check inputs
    # --------------------
    
    (
     key, key_cam, is2d, 
     ddata0, ref0, comp,
     dshapes, ndimref, indref,
     key_data, key_ref,
     returnas,
     ) = _concatenate_check(
        coll=coll,
        key=key,
        key_cam=key_cam,
        data=data,
        # naming
        key_data=key_data,
        key_ref=key_ref,
    )
    
    print(ddata0)
    print(ref0)
    print(dshapes)
    print(indref)
    print(comp)
    
    # -----------------------------------
    # ddata => check shapes, define dref
    # -----------------------------------

    # ------------
    # check shapes
    
    
    
    # ------------
    # concatenate
    
    ndata = len(ddata0[key_cam[0]])
    print(ndata)
    ddata, dref = {}, {}
    for ii in range(ndata):
        
        if comp is True:
            
            datai = np.concatenate(
                tuple([ddata0[k0][ii] for k0 in key_cam]),
                axis=indref[0],
            )
            ref = None
            
        else:
            datai = np.concatenate(
                tuple([coll.ddata[ddata0[k0][ii]]['data'] for k0 in key_cam]),
                axis=indref[0],
            )

        # ----------
        # build dict

        ddata[key_data[ii]] = {
            'data': datai,
            'ref': ref0,
            'units': None,
            'dim': None,
        }
        
    dref = {
        k0: {'size': coll.dref[k0]['size']} for k0 in ref0 if k0 != key_ref
    }
    dref[key_ref] = {'size': datai.shape[indref[0]]}
        
    # -------------------------
    # build dict
    # -------------------------
    
    return key, key_cam, ddata, dref
    

# ##################################################################
# ##################################################################
#             interpolated along los
# ##################################################################


def _interpolated_along_los(
    coll=None,
    key=None,
    key_cam=None,
    key_data_x=None,
    key_data_y=None,
    res=None,
    mode=None,
    segment=None,
    radius_max=None,
    plot=None,
    dcolor=None,
    dax=None,
    ):
    
    # ------------
    # check inputs
    
    # key_cam
    key, key_cam = coll.get_diagnostic_cam(key=key, key_cam=key_cam)
    
    # key_data
    lok_coords = ['x', 'y', 'z', 'R', 'phi', 'k', 'l', 'ltot', 'itot']
    lok_2d = [
        k0 for k0, v0 in coll.ddata.items()
        if v0.get('bsplines') is not None
    ]
    
    key_data_x = ds._generic_check._check_var(
        key_data_x, 'key_data_x',
        types=str,
        default='k',
        allowed=lok_coords + lok_2d,
    )
    
    key_data_y = ds._generic_check._check_var(
        key_data_y, 'key_data_y',
        types=str,
        default='k',
        allowed=lok_coords + lok_2d,
    )
    
    # segment
    segment = ds._generic_check._check_var(
        segment, 'segment',
        types=int,
        default=-1,
    )
    
    # plot
    plot = ds._generic_check._check_var(
        plot, 'plot',
        types=bool,
        default=True,
    )
    
    # dcolor
    if not isinstance(dcolor, dict):
        if dcolor is None:
            lc = ['k', 'r', 'g', 'b', 'm', 'c']
        elif mcolors.is_color_like(dcolor):
            lc = [dcolor]
            
        dcolor = {
            kk: lc[ii%len(lc)]
            for ii, kk in enumerate(key_cam)
            }
    
    # --------------
    # prepare output
    
    ncam = len(key_cam)
    
    xx = [None for ii in range(ncam)]
    yy = [None for ii in range(ncam)]
    
    # ---------------
    # loop on cameras
    
    if key_data_x in lok_coords and key_data_y in lok_coords:
        
        for ii, kk in enumerate(key_cam):
            
            klos = coll.dobj['diagnostic'][key]['doptics'][kk]['los']
            if klos is None:
                continue
            
            xx[ii], yy[ii] = coll.sample_rays(
                key=klos,
                res=res,
                mode=mode,
                segment=segment,
                radius_max=radius_max,
                concatenate=True,
                return_coords=[key_data_x, key_data_y],
                )    
            
            if key_data_x in ['x', 'y', 'z', 'R', 'l', 'ltot']:
                xlab = f"{key_data_x} (m)"
            else:
                xlab = key_data_x
                
            if key_data_y in ['x', 'y', 'z', 'R', 'l', 'ltot']:
                ylab = f"{key_data_y} (m)"
            else:
                ylab = key_data_y
    
    elif key_data_x in lok_coords or key_data_y in lok_coords:
    
        if key_data_x in lok_coords:
            cll = key_data_x
            c2d = key_data_y
            if key_data_x in ['x', 'y', 'z', 'R', 'l', 'ltot']:
                xlab = f"{key_data_x} (m)"
            else:
                xlab = key_data_x
            ylab = f"{key_data_y} ({coll.ddata[key_data_y]['units']})"
        else:
            cll = key_data_y
            c2d = key_data_x
            if key_data_y in ['x', 'y', 'z', 'R', 'l', 'ltot']:
                ylab = f"{key_data_y} (m)"
            else:
                ylab = key_data_y
            xlab = f"{key_data_x} ({coll.ddata[key_data_x]['units']})"

        for ii, kk in enumerate(key_cam): 
            
            klos = coll.dobj['diagnostic'][key]['doptics'][kk]['los']
            if klos is None:
                continue
            
            pts_x, pts_y, pts_z, pts_ll = coll.sample_rays(
                key=klos,
                res=res,
                mode=mode,
                segment=segment,
                radius_max=radius_max,
                concatenate=True,
                return_coords=['x', 'y', 'z', cll],
                )      
            
            Ri = np.hypot(pts_x, pts_y)
            
            q2d, _ = coll.interpolate_profile2d(
                key=c2d,
                R=Ri,
                Z=pts_z,
                grid=False,
                crop=True,
                nan0=True,
                nan_out=True,
                imshow=False,
                return_params=None,
                store=False,
                inplace=False,
            )  
                
            isok = ~(np.isnan(q2d) & (~np.isnan(Ri)))
            if key_data_x in lok_coords:
                xx[ii] = pts_ll[isok]
                yy[ii] = q2d[isok]
            else:
                xx[ii] = q2d[isok]
                yy[ii] = pts_ll[isok]
    
    else:
        for ii, kk in enumerate(key_cam):   
            
            klos = coll.dobj['diagnostic'][key]['doptics'][kk]['los']
            if klos is None:
                continue
            
            pts_x, pts_y, pts_z = coll.sample_rays(
                key=klos,
                res=res,
                mode=mode,
                segment=segment,
                radius_max=radius_max,
                concatenate=True,
                return_coords=['x', 'y', 'z'],
                )      
    
            Ri = np.hypot(pts_x, pts_y)
            
            q2dx, _ = coll.interpolate_profile2d(
                key=key_data_x,
                R=Ri,
                Z=pts_z,
                grid=False,
                crop=True,
                nan0=True,
                nan_out=True,
                imshow=False,
                return_params=None,
                store=False,
                inplace=False,
            )  
    
            q2dy, _ = coll.interpolate_profile2d(
                key=key_data_y,
                R=Ri,
                Z=pts_z,
                grid=False,
                crop=True,
                nan0=True,
                nan_out=True,
                imshow=False,
                return_params=None,
                store=False,
                inplace=False,
            )  
    
            isok = ~((np.isnan(q2dx) | np.isnan(q2dy)) & (~np.isnan(Ri)))
            xx[ii] = q2dx[isok]
            yy[ii] = q2dy[isok]
            
            xlab = f"{key_data_x} ({coll.ddata[key_data_x]['units']})"
            ylab = f"{key_data_y} ({coll.ddata[key_data_y]['units']})"
   
    # ------------
    # plot
    
    if plot is True:
        if dax is None:
            
            fig = plt.figure()
            
            ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
            
            tit = f"{key} LOS\nminor radius vs major radius"
            ax.set_title(tit, size=12, fontweight='bold')
            ax.set_xlabel(xlab)
            ax.set_ylabel(ylab)
            
            dax = {'main': ax}
            
        # main
        kax = 'main'
        if dax.get(kax) is not None:
            ax = dax[kax]
            
            for ii, kk in enumerate(key_cam):
                ax.plot(
                    xx[ii],
                    yy[ii],
                    c=dcolor[kk],
                    marker='.',
                    ls='-',
                    ms=8,
                    label=kk,
                )
     
            ax.legend()
    
        return xx, yy, dax
    else:
        return xx, yy
    
    
# ##################################################################
# ##################################################################
#             MOVE
# ##################################################################


def move_to(
    coll=None,
    key=None,
    key_cam=None,
    optics=None,
    # location
    x=None,
    y=None,
    R=None,
    z=None,
    phi=None,
    theta=None,
    dphi=None,
    tilt=None,
    ):

    # ------------
    # check inputs
    
    # trivial case
    nochange = all([ss is None for ss in [x, y, z, R, phi, theta, dphi, tilt]])
    
    # key, key_cam
    key, key_cam = coll.get_diagnostic_cam(key=key, key_cam=key_cam)
    is2d = coll.dobj['diagnostic'][key]['is2d']
    
    if len(key_cam) != 1:
        msg = "move_diagnostic_to() can only be used on one camera"
        raise Exception(msg)
    key_cam = key_cam[0]
    doptics = coll.dobj['diagnostic'][key]['doptics'][key_cam]
    
    # optics
    lok = [key_cam] + doptics['optics']
    op_ref = ds._generic_check._check_var(
        optics, 'optics',
        types=str,
        default=doptics['optics'][0],
        allowed=lok,
    )
    
    # get optics, op_cls
    optics = doptics['optics']
    op_cls = doptics['cls']
    
    # x, y vs R, phi
    lc = [
        x is not None or y is not None,
        R is not None or phi is not None,
    ]
    if np.sum(lc) > 1:
        msg = "Please provide (x, y) xor (R, phi) !"
        raise Exception(msg)
    
    # ----------------------------------
    # use the chosen optics center as reference
    
    if op_ref == key_cam:
        if is2d:
            cls_ref = 'camera'
            cc = coll.dobj[cls_ref][op_ref]['dgeom']['cent']
            nin = coll.dobj[cls_ref][op_ref]['dgeom']['nin']
            e0 = coll.dobj[cls_ref][op_ref]['dgeom']['e0']
            e1 = coll.dobj[cls_ref][op_ref]['dgeom']['e1']
            
        else:
            raise NotImplementedError()
    
    else:
        cls_ref = op_cls[optics.index(op_ref)]
        cc = coll.dobj[cls_ref][op_ref]['dgeom']['cent']
        nin = coll.dobj[cls_ref][op_ref]['dgeom']['nin']
        e0 = coll.dobj[cls_ref][op_ref]['dgeom']['e0']
        e1 = coll.dobj[cls_ref][op_ref]['dgeom']['e1']
        
    # ----------------------------------
    # get initial local coordinates in this frame
        
    dinit = _get_initial_parameters(
        cc=cc,
        nin=nin,
        e0=e0,
        e1=e1,
    )
        
    # ----------------------------------
    # get all local coordinates in this frame
    
    dcoords = {}
    
    # camera
    if is2d:
        dcoords[key_cam] = _extract_coords(
            dg=coll.dobj['camera'][key_cam]['dgeom'],
            cc=cc,
            nin=nin,
            e0=e0,
            e1=e1,
        )
    else:
        dcoords[key_cam] = _extract_coords_cam1d(
            coll=coll,
            key_cam=key_cam,
            cc=cc,
            nin=nin,
            e0=e0,
            e1=e1,
        )

    # optics
    for op, opc in zip(optics, op_cls):  
        dcoords[op] = _extract_coords(
            dg=coll.dobj[opc][op]['dgeom'],
            cc=cc,
            nin=nin,
            e0=e0,
            e1=e1,
        )

    # ----------------------------------
    # get new default values
    
    if not any(lc):
        x, y = dinit['x'], dinit['y']
        R = np.hypot(x, y)
        phi = np.arctan2(y, x)
    elif lc[0]:
        if x is None:
            x = dinit['x']
        if y is None:
            y = dinit['y']
        R = np.hypot(x, y)
        phi = np.arctan2(y, x)
    else:
        if R is None:
            R = dinit['R']
        if phi is None:
            phi = dinit['phi']
        x = R * np.cos(phi)
        y = R * np.sin(phi)

    if z is None:
        z = dinit['z']

    if dphi is None:
        dphi = dinit['dphi']
        
    if theta is None:
        theta = dinit['theta']
        
    if tilt is None:
        tilt = dinit['tilt']

    # ----------------------------------
    # get new coordinates of reference
    
    cc_new, nin_new, e0_new, e1_new = get_new_frame(
        key_cam=key_cam,
        dinit=dinit,
        x=x,
        y=y,
        z=z,
        phi=phi,
        dphi=dphi,
        theta=theta,
        tilt=tilt,
        # safety check
        nochange=nochange,
        cc=cc,
        nin=nin,
        e0=e0,
        e1=e1,
    )

    # ----------------------------------
    # Update all coordinates

    # camera
    if is2d:
        reset_coords(
            coll=coll,
            op=key_cam,
            opc='camera',
            dcoords=dcoords,
            cc_new=cc_new,
            nin_new=nin_new,
            e0_new=e0_new,
            e1_new=e1_new,
        )
    else:
        reset_coords_cam1d(
            coll=coll,
            op=key_cam,
            opc='camera',
            dcoords=dcoords,
            cc_new=cc_new,
            nin_new=nin_new,
            e0_new=e0_new,
            e1_new=e1_new,
        )

    # optics
    for op, opc in zip(optics, op_cls):
        reset_coords(
            coll=coll,
            op=op,
            opc=opc,
            dcoords=dcoords,
            cc_new=cc_new,
            nin_new=nin_new,
            e0_new=e0_new,
            e1_new=e1_new,
        )

    return



def _get_initial_parameters(
    cc=None,
    nin=None,
    e0=None,
    e1=None,
):
    
    # cordinates
    x, y, z = cc
    R = np.hypot(x, y)
    
    # angles
    phi = np.arctan2(y, x)
    
    # unit vectors
    eR = np.r_[np.cos(phi), np.sin(phi), 0.]
    ephi = np.r_[-np.sin(phi), np.cos(phi), 0.]

    # orientation angles: dphi
    dphi = np.pi/2. - np.arccos(np.sum(nin * ephi))
        
    # orientation angles: theta
    ni = nin - np.sum(nin*ephi)*ephi
    ni = ni / np.linalg.norm(ni)
    theta = np.arctan2(ni[2], np.sum(ni * eR))
    
    # orientation: tilt
    er = np.cos(theta) * eR + np.sin(theta) * np.r_[0, 0, 1]
    etheta = -np.sin(theta) * eR + np.cos(theta) * np.r_[0, 0, 1]
    e0bis = -np.cos(dphi) * ephi + np.sin(dphi) * er
    
    tilt = np.arctan2(np.sum(e0*etheta), np.sum(e0*e0bis))
    
    return {
        'x': x,
        'y': y,
        'z': z,
        'R': R,
        'phi': phi,
        'dphi': dphi,
        'theta': theta,
        'tilt': tilt,
    }


def get_new_frame(
    key_cam=None,
    dinit=None,
    x=None,
    y=None,
    z=None,
    phi=None,
    dphi=None,
    theta=None,
    tilt=None,
    # safety check
    nochange=None,
    cc=None,
    nin=None,
    e0=None,
    e1=None,
):
    
    # orientation
    eR = np.r_[np.cos(phi), np.sin(phi), 0.]
    ephi = np.r_[-np.sin(phi), np.cos(phi), 0.]
    er = np.cos(theta) * eR + np.sin(theta) * np.r_[0, 0, 1] 
    etheta = -np.sin(theta) * eR + np.cos(theta) * np.r_[0, 0, 1] 
    e0bis = -np.cos(dphi) * ephi + np.sin(dphi) * er
    
    # translation
    cc_new = np.r_[x, y, z]
    
    # new unit vectors
    nin_new = np.cos(dphi) * er + np.sin(dphi) * ephi
    e0_new = np.cos(tilt) * e0bis + np.sin(tilt) * etheta
    e1_new = np.cross(nin_new, e0_new)
    
    # safety check
    nin_new, e0_new, e1_new = ds._generic_check._check_vectbasis(
        e0=nin_new,
        e1=e0_new,
        e2=e1_new,
        dim=3,
        tol=1e-12,
    )
    
    # safety check
    if nochange:
        dout = {}
        for ss in ['cc', 'nin', 'e0', 'e1']:
            if not np.allclose(eval(ss), eval(f'{ss}_new')):
                dout[ss] = (eval(ss), eval(f'{ss}_new'))
        
        if len(dout) > 0:
            lstr = [f"\t- '{k0}': {v0[0]} vs {v0[1]}" for k0, v0 in dout.items()]
            msg = (
                f"Immobile diagnostic camera '{key_cam}' has moved:\n"
                + "\n".join(lstr)
                + f"\n\ndinit = {dinit}"
            )
            raise Exception(msg)
    
    return cc_new, nin_new, e0_new, e1_new


def _extract_coords(
    dg=None,
    cc=None,
    nin=None,
    e0=None,
    e1=None,
    ):
    
    return {
        'c_n01': np.r_[
            np.sum((dg['cent'] - cc) * nin),
            np.sum((dg['cent'] - cc) * e0),
            np.sum((dg['cent'] - cc) * e1),
        ],
        'n_n01': np.r_[
            np.sum(dg['nin'] * nin),
            np.sum(dg['nin'] * e0),
            np.sum(dg['nin'] * e1),
        ],
        'e0_n01': np.r_[
            np.sum(dg['e0'] * nin),
            np.sum(dg['e0'] * e0),
            np.sum(dg['e0'] * e1),
        ],
        'e1_n01': np.r_[
            np.sum(dg['e1'] * nin),
            np.sum(dg['e1'] * e0),
            np.sum(dg['e1'] * e1),
        ],
    }


def _extract_coords_cam1d(
    coll=None,
    key_cam=None,
    cc=None,
    nin=None,
    e0=None,
    e1=None,
    ):
    
    dout = {}
    kc = coll.dobj['camera'][key_cam]['dgeom']['cents']
    parallel = coll.dobj['camera'][key_cam]['dgeom']['parallel']
    
    # cents 
    shape = tuple(np.r_[3, coll.ddata[kc[0]]['data'].shape])
    dout['cents'] = np.zeros(shape)
    for ss, ii in [('x', 0), ('y', 1), ('z', 2)]:
        dout['cents'] += np.array([
            (coll.ddata[kc[ii]]['data'] - cc[ii]) * nin[ii],
            (coll.ddata[kc[ii]]['data'] - cc[ii]) * e0[ii],
            (coll.ddata[kc[ii]]['data'] - cc[ii]) * e1[ii],
        ])
    
    # unit vectors
    if parallel:
        for kk in ['nin', 'e0', 'e1']:
            dout[f'{kk}_n01'] = np.array([
                np.sum(coll.dobj['camera'][key_cam]['dgeom'][kk] * nin),
                np.sum(coll.dobj['camera'][key_cam]['dgeom'][kk] * e0),
                np.sum(coll.dobj['camera'][key_cam]['dgeom'][kk] * e1),
            ])
    else:
        for kk in ['nin', 'e0', 'e1']:
            dout[kk] = np.zeros(shape)
            kv = coll.dobj['camera'][key_cam]['dgeom'][kk]
            for ss, ii in [('x', 0), ('y', 1), ('z', 2)]:
                dout[kk] += np.array([
                    coll.ddata[kv[ii]]['data'] * nin[ii],
                    coll.ddata[kv[ii]]['data'] * e0[ii],
                    coll.ddata[kv[ii]]['data'] * e1[ii],
                ])
    return dout


def reset_coords(
    coll=None,
    op=None,
    opc=None,
    dcoords=None,
    cc_new=None,
    nin_new=None,
    e0_new=None,
    e1_new=None,
    ):

    if coll._dobj[opc][op]['dgeom']['type'] == '3d':
        raise NotImplementedError()
    
    # translate
    coll._dobj[opc][op]['dgeom']['cent'] = (
        cc_new
        + dcoords[op]['c_n01'][0] * nin_new
        + dcoords[op]['c_n01'][1] * e0_new
        + dcoords[op]['c_n01'][2] * e1_new
    )

    # rotate
    nin = (
        dcoords[op]['n_n01'][0] * nin_new
        + dcoords[op]['n_n01'][1] * e0_new
        + dcoords[op]['n_n01'][2] * e1_new
    )
    e0 = (
        dcoords[op]['e0_n01'][0] * nin_new
        + dcoords[op]['e0_n01'][1] * e0_new
        + dcoords[op]['e0_n01'][2] * e1_new
    )
    e1 = (
        dcoords[op]['e1_n01'][0] * nin_new
        + dcoords[op]['e1_n01'][1] * e0_new
        + dcoords[op]['e1_n01'][2] * e1_new
    )
    
    # --------------
    # safety check

    nin, e0, e1 = ds._generic_check._check_vectbasis(
        e0=nin,
        e1=e0,
        e2=e1,
        dim=3,
        tol=1e-12,
    )

    # store
    coll._dobj[opc][op]['dgeom']['nin'] = nin
    coll._dobj[opc][op]['dgeom']['e0'] = e0
    coll._dobj[opc][op]['dgeom']['e1'] = e1
    
    
def reset_coords_cam1d(
    coll=None,
    op=None,
    opc=None,
    dcoords=None,
    cc_new=None,
    nin_new=None,
    e0_new=None,
    e1_new=None,
    ):
    
    kc = coll.dobj[opc][op]['dgeom']['cents']
    parallel = coll.dobj[opc][op]['dgeom']['parallel']

    # cents 
    for ss, ii in [('x', 0), ('y', 1), ('z', 2)]:
        coll._ddata[kc[ii]]['data'] = (
            cc_new[ii]
            + dcoords[op]['cents'][0] * nin_new[ii]
            + dcoords[op]['cents'][1] * e0_new[ii]
            + dcoords[op]['cents'][2] * e1_new[ii]
        )

    # rotate
    if parallel:
        nin = (
            dcoords[op]['nin_n01'][0] * nin_new
            + dcoords[op]['nin_n01'][1] * e0_new
            + dcoords[op]['nin_n01'][2] * e1_new
        )
        e0 = (
            dcoords[op]['e0_n01'][0] * nin_new
            + dcoords[op]['e0_n01'][1] * e0_new
            + dcoords[op]['e0_n01'][2] * e1_new
        )
        e1 = (
            dcoords[op]['e1_n01'][0] * nin_new
            + dcoords[op]['e1_n01'][1] * e0_new
            + dcoords[op]['e1_n01'][2] * e1_new
        )
        
        # safety check
        nin, e0, e1 = ds._generic_check._check_vectbasis(
            e0=nin,
            e1=e0,
            e2=e1,
            dim=3,
            tol=1e-12,
        )

        coll._dobj[opc][op]['dgeom']['nin'] = nin
        coll._dobj[opc][op]['dgeom']['e0'] = e0
        coll._dobj[opc][op]['dgeom']['e1'] = e1

    else:
        for kk in ['nin', 'e0', 'e1']:
            kv = coll.dobj[opc][op]['dgeom'][kk]
            for ss, ii in [('x', 0), ('y', 1), ('z', 2)]:
                coll.ddata[kv[ii]]['data'] = (
                    dcoords[op][kk][0] * nin_new[ii]
                    + dcoords[op][kk][1] * e0_new[ii]
                    + dcoords[op][kk][2] * e1_new[ii]
                )