# -*- coding: utf-8 -*-


import numpy as np
import bsplines2d as bs2
from contourpy import contour_generator
from matplotlib.path import Path
from scipy.spatial import ConvexHull
import datastock as ds
import Polygon as plg


# ###########################################################
# ###########################################################
#               Get cross-section indices
# ###########################################################


def _get_cross_section_indices(
    dsamp=None,
    # polygon
    pcross0=None,
    pcross1=None,
    phor0=None,
    phor1=None,
    margin_poly=None,
    # points
    x0f=None,
    x1f=None,
    sh=None,
):

    # ----------
    # check

    margin_poly = ds._generic_check._check_var(
        margin_poly, 'margin_poly',
        types=float,
        default=0.2,
        sign='>0'
    )

    # ---------------------------
    # add extra margin to pcross

    # get centroid
    center = plg.Polygon(np.array([pcross0, pcross1]).T).center()

    # add margin
    pcross02 = center[0] + (1. + margin_poly) * (pcross0 - center[0])
    pcross12 = center[1] + (1. + margin_poly) * (pcross1 - center[1])

    # define path
    pcross = Path(np.array([pcross02, pcross12]).T)

    # ---------------------------
    # add extra margin to phor

    # get center
    center = plg.Polygon(np.array([phor0, phor1]).T).center()

    # add margin
    phor02 = center[0] + (1. + margin_poly) * (phor0 - center[0])
    phor12 = center[1] + (1. + margin_poly) * (phor1 - center[1])

    # define path
    phor = Path(np.array([phor02, phor12]).T)

    # get ind
    return (
        dsamp['ind']['data']
        & pcross.contains_points(np.array([x0f, x1f]).T).reshape(sh)
    ), phor


# ###########################################################
# ###########################################################
#               get polygons
# ###########################################################


def _get_polygons(
    x0=None,
    x1=None,
    bool_cross=None,
    res=None,
):

    # ------------
    # get contour

    contgen = contour_generator(
        x=x0,
        y=x1,
        z=bool_cross,
        name='serial',
        corner_mask=None,
        line_type='Separate',
        fill_type=None,
        chunk_size=None,
        chunk_count=None,
        total_chunk_count=None,
        quad_as_tri=True,       # for sub-mesh precision
        # z_interp=<ZInterp.Linear: 1>,
        thread_count=0,
    )

    no_cont, cj = bs2._class02_contours._get_contours_lvls(
        contgen=contgen,
        level=0.5,
        largest=True,
    )

    assert no_cont is False

    # -------------
    # simplify poly

    return _simplify_polygon(cj[:, 0], cj[:, 1], res=res)


def _simplify_polygon(c0, c1, res=None):

    # -----------
    # convex hull

    npts = c0.size

    # get hull
    convh = ConvexHull(np.array([c0, c1]).T)
    indh = convh.vertices
    ch0 = c0[indh]
    ch1 = c1[indh]
    nh = indh.size

    sign = np.median(np.diff(indh))

    # segments norms
    seg0 = np.r_[ch0[1:] - ch0[:-1], ch0[0] - ch0[-1]]
    seg1 = np.r_[ch1[1:] - ch1[:-1], ch1[0] - ch1[-1]]
    norms = np.sqrt(seg0**2 + seg1**2)

    # keep egdes that match res
    lind = []
    for ii, ih in enumerate(indh):

        # ind of points in between
        i1 = indh[(ii + 1) % nh]
        if sign > 0:
            if i1 > ih:
                ind = np.arange(ih, i1 + 1)
            else:
                ind = np.r_[np.arange(ih, npts), np.arange(0, i1 + 1)]
        else:
            if i1 < ih:
                ind = np.arange(ih, i1 - 1, -1)
            else:
                ind = np.r_[np.arange(ih, -1, -1), np.arange(npts - 1, i1 - 1, -1)]

        # trivial
        if ind.size == 2:
            lind.append((ih, i1))
            continue

        # get distances
        x0 = c0[ind]
        x1 = c1[ind]

        # segment unit vect
        vect0 = x0 - ch0[ii]
        vect1 = x1 - ch1[ii]

        # perpendicular distance
        cross = (vect0*seg1[ii] - vect1*seg0[ii]) / norms[ii]

        # criterion
        if np.all(np.abs(cross) <= 0.8*res):
            lind.append((ih, i1))
        else:
            lind += _simplify_concave(
                x0=x0,
                x1=x1,
                ind=ind,
                cross=cross,
                res=res,
            )

    # ------------------------------------
    # point by point on remaining segments

    iok = np.unique(np.concatenate(tuple(lind)))

    return c0[iok], c1[iok]


def _simplify_concave(
    x0=None,
    x1=None,
    ind=None,
    cross=None,
    res=None,
):

    # ------------
    # safety check

    sign = np.sign(cross)
    sign0 = np.mean(sign)
    assert np.all(cross * sign0 >= -1e-12)

    # ------------
    # loop

    i0 = 0
    i1 = 1
    iok = 1
    lind_loc, lind = [], []
    while iok <= ind.size - 1:

        # reference normalized vector
        vref0, vref1 = x0[i1] - x0[i0], x1[i1] - x1[i0]
        normref = np.sqrt(vref0**2 + vref1**2)
        vref0, vref1 = vref0 / normref, vref1 / normref

        # intermediate vectors
        indi = np.arange(i0 + 1, i1)
        v0 = x0[indi] - x0[i0]
        v1 = x1[indi] - x1[i0]

        # sign and distance (from cross product)
        cross = v0 * vref1 - v1 * vref0
        dist = np.abs(cross)

        # conditions
        c0 = np.all(dist <= 0.8*res)
        c1 = np.all(cross * sign0 >= -1e-12)
        c2 = i1 == ind.size - 1

        append = False
        # cases
        if c0 and c1 and (not c2):
            iok = int(i1)
            i1 += 1
        elif c0 and c1 and c2:
            iok = int(i1)
            append = True
        elif c0 and (not c1) and (not c2):
            i1 += 1
        elif c0 and (not c1) and c2:
            append = True
        elif not c0:
            append = True

        # append
        if append is True:
            lind_loc.append((i0, iok))
            lind.append((ind[i0], ind[iok]))
            i0 = iok
            i1 = i0 + 1
            iok = int(i1)

        if i1 > ind.size - 1:
            break

    return lind


# #################################################################
# #################################################################
#               Get dphi from R and phor
# #################################################################


def _get_dphi_from_R_phor(
    R=None,
    phor0=None,
    phor1=None,
    phimin=None,
    phimax=None,
    res=None,
):

    # ------------
    # check inputs

    # R
    R = np.unique(np.atleast_1d(R).ravel())

    # path
    path = Path(np.array([phor0, phor1]).T)

    # --------------
    # sample phi

    dphi = np.full((2, R.size), np.nan)
    for ir, rr in enumerate(R):

        nphi = np.ceil(rr*(phimax - phimin) / (0.05*res)).astype(int)
        phi = np.linspace(phimin, phimax, nphi)

        ind = path.contains_points(
            np.array([rr*np.cos(phi), rr*np.sin(phi)]).T
        )

        if np.any(ind):
            dphi[0, ir] = np.min(phi[ind]) - (phi[1] - phi[0])
            dphi[1, ir] = np.max(phi[ind]) + (phi[1] - phi[0])

    return dphi
