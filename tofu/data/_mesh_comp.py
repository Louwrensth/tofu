# -*- coding: utf-8 -*-


# Built-in
import warnings

# Common
import numpy as np
from matplotlib.path import Path


# tofu
from . import _generic_check
from . import _mesh_checks
from . import _mesh_bsplines_rect
from . import _mesh_bsplines_tri


# #############################################################################
# #############################################################################
#                           Mesh2D - select
# #############################################################################


def _select_ind(
    coll=None,
    key=None,
    ind=None,
    elements=None,
    returnas=None,
    crop=None,
):
    """ ind can be:
            - None
            - tuple: (R, Z), possibly 2d
            - 'tuple-flat': (R, Z) flattened
            - np.ndarray: array of unique indices
            - 'array-flat': flattened ordered array of unique
    """

    # ------------
    # check inputs

    # key = mesh or bspline ?
    lk1 = list(coll.dobj.get(coll._which_mesh, {}).keys())
    lk2 = list(coll.dobj.get('bsplines', {}).keys())
    key = _generic_check._check_var(
        key, 'key',
        allowed=lk1 + lk2,
        types=str,
    )

    cat = coll._which_mesh if key in lk1 else 'bsplines'
    if cat == coll._which_mesh:
        meshtype = coll.dobj[cat][key]['type']
    else:
        km = coll.dobj[cat][key]['mesh']
        meshtype = coll.dobj[coll._which_mesh][km]['type']

    # ind, elements, ...
    # elements = cents or knots
    ind, elements, returnas, crop = _mesh_checks._select_ind_check(
        ind=ind,
        elements=elements,
        returnas=returnas,
        crop=crop,
        meshtype=meshtype,
    )

    elem = f'{elements}' if cat == coll._which_mesh else 'ref'

    if meshtype == 'rect':
        if cat == coll._which_mesh:
            ke = f'shape-{elem[0]}'
            nR, nZ = coll.dobj[cat][key][ke]
        else:
            nR, nZ = coll.dobj[cat][key]['shape']
    else:
        if cat == coll._which_mesh:
            ke = f'shape-{elem[0]}'
            nelem = coll.dobj[cat][key][ke][0]
        else:
            nelem = coll.dobj[cat][key]['shape'][0]

    # ------------
    # ind to tuple

    if meshtype == 'rect':
        ind_bool = np.zeros((nR, nZ), dtype=bool)
        if ind is None:
            # make sure R is varying in dimension 0
            ind_tup = (
                np.repeat(np.arange(0, nR)[:, None], nZ, axis=1),
                np.tile(np.arange(0, nZ), (nR, 1)),
            )
            ind_bool[...] = True

        elif isinstance(ind, tuple):
            c0 = (
                np.all((ind[0] >= 0) & (ind[0] < nR))
                and np.all((ind[1] >= 0) & (ind[1] < nZ))
            )
            if not c0:
                msg = (
                    f"Non-valid values in ind (< 0 or >= size ({nR}, {nZ}))"
                )
                raise Exception(msg)
            ind_tup = ind
            ind_bool[ind_tup[0], ind_tup[1]] = True

        else:
            if np.issubdtype(ind.dtype, np.integer):
                c0 = np.all((ind >= 0) & (ind < nR*nZ))
                if not c0:
                    msg = (
                        f"Non-valid values in ind (< 0 or >= size ({nR*nZ}))"
                    )
                    raise Exception(msg)
                ind_tup = (ind % nR, ind // nR)
                ind_bool[ind_tup[0], ind_tup[1]] = True

            elif np.issubdtype(ind.dtype, np.bool_):
                if ind.shape != (nR, nZ):
                    msg = (
                        f"Arg ind, if bool, must have shape {(nR, nZ)}\n"
                        f"Provided: {ind.shape}"
                    )
                    raise Exception(msg)
                # make sure R varies first
                ind_tup = ind.T.nonzero()[::-1]
                ind_bool = ind

            else:
                msg = f"Unknown ind dtype!\n\t- ind.dtype: {ind.dtype}"
                raise Exception(msg)

        if ind_tup[0].shape != ind_tup[1].shape:
            msg = (
                "ind_tup components do not have the same shape!\n"
                f"\t- ind_tup[0].shape = {ind_tup[0].shape}\n"
                f"\t- ind_tup[1].shape = {ind_tup[1].shape}"
            )
            raise Exception(msg)

    # triangular case
    else:
        ind_bool = np.zeros((nelem,), dtype=bool)
        if ind is None:
            ind_bool[...] = True
        elif np.issubdtype(ind.dtype, np.integer):
            c0 = np.all((ind >= 0) & (ind < nelem))
            if not c0:
                msg = (
                    f"Arg ind has non-valid values (< 0 or >= size ({nelem}))"
                )
                raise Exception(msg)
            ind_bool[ind] = True
        elif np.issubdtype(ind.dtype, np.bool_):
            if ind.shape != (nelem,):
                msg = (
                    f"Arg ind, when array of bool, must have shape {(nelem,)}"
                    f"\nProvided: {ind.shape}"
                )
                raise Exception(msg)
            ind_bool = ind
        else:
            msg = (
                "Non-valid ind format!"
            )
            raise Exception(msg)

    # ------------
    # optional crop

    crop = (
        crop is True
        and coll.dobj[cat][key].get('crop') not in [None, False]
        and bool(np.any(~coll.ddata[coll.dobj[cat][key]['crop']]['data']))
    )
    if crop is True:
        cropi = coll.ddata[coll.dobj[cat][key]['crop']]['data']
        if meshtype == 'rect':
            if cat == coll._which_mesh and elements == 'knots':
                cropiknots = np.zeros(ind_bool.shape, dtype=bool)
                cropiknots[:-1, :-1] = cropi
                cropiknots[1:, :-1] = cropiknots[1:, :-1] | cropi
                cropiknots[1:, 1:] = cropiknots[1:, 1:] | cropi
                cropiknots[:-1, 1:] = cropiknots[:-1, 1:] | cropi

                ind_bool = ind_bool & cropiknots

                # ind_tup is not 2d anymore
                ind_tup = ind_bool.T.nonzero()[::-1]  # R varies first
                warnings.warn("ind is not 2d anymore!")

            elif ind_tup[0].shape == cropi.shape:
                ind_bool = ind_bool & cropi
                # ind_tup is not 2d anymore
                ind_tup = ind_bool.T.nonzero()[::-1]  # R varies first
                warnings.warn("ind is not 2d anymore!")

            else:
                ind_bool = ind_bool & cropi
                ind_tup = ind_bool.T.nonzero()[::-1]
        else:
            ind_bool &= cropi

    # ------------
    # tuple to return

    if returnas is bool:
        out = ind_bool
    elif returnas is int:
        out = ind_bool.nonzero()[0]
    elif returnas is tuple:
        out = ind_tup
    elif returnas == 'tuple-flat':
        # make sure R is varying first
        out = (ind_tup[0].T.ravel(), ind_tup[1].T.ravel())
    elif returnas is np.ndarray:
        out = ind_tup[0] + ind_tup[1]*nR
    elif returnas == 'array-flat':
        # make sure R is varying first
        out = (ind_tup[0] + ind_tup[1]*nR).T.ravel()
    else:
        out = ind_bool

    return out


# #############################################################################
# #############################################################################
#                           Mesh2D - select mesh rect
# #############################################################################


def _select_mesh_rect(
    coll=None,
    key=None,
    ind=None,
    elements=None,
    returnas=None,
    return_ind_as=None,
    return_neighbours=None,
):
    """ ind is a tuple for rect """

    # ------------
    # check inputs

    key = _generic_check._check_var(
        key, 'key',
        types=str,
        allowed=list(coll.dobj['mesh'].keys())
    )
    meshtype = coll.dobj['mesh'][key]['type']

    (
        elements, returnas,
        return_ind_as, return_neighbours,
    ) = _mesh_checks._select_check(
        elements=elements,
        returnas=returnas,
        return_ind_as=return_ind_as,
        return_neighbours=return_neighbours,
    )

    # ------------
    # prepare

    kR, kZ = coll.dobj[coll._which_mesh][key][elements]
    R = coll.ddata[kR]['data']
    Z = coll.ddata[kZ]['data']
    nR = R.size
    nZ = Z.size

    # ------------
    # non-trivial case

    if returnas == 'ind':
        out = ind
    else:
        out = R[ind[0]], Z[ind[1]]

    # ------------
    # neighbours

    if return_neighbours is True:

        elneig = 'cents' if elements == 'knots' else 'knots'
        kRneig, kZneig = coll.dobj[coll._which_mesh][key][f'{elneig}']
        Rneig = coll.ddata[kRneig]['data']
        Zneig = coll.ddata[kZneig]['data']
        nRneig = Rneig.size
        nZneig = Zneig.size

        # get tuple indices of neighbours
        shape = tuple(np.r_[ind[0].shape, 4])
        neig = (
            np.zeros(shape, dtype=int),
            np.zeros(shape, dtype=int),
        )
        rsh = tuple(
            [4 if ii == len(shape)-1 else 1 for ii in range(len(shape))]
        )

        if elements == 'cents':
            neig[0][...] = ind[0][..., None] + np.r_[0, 1, 1, 0].reshape(rsh)
            neig[1][...] = ind[1][..., None] + np.r_[0, 0, 1, 1].reshape(rsh)
        elif elements == 'knots':
            neig[0][...] = ind[0][..., None] + np.r_[-1, 0, 0, -1].reshape(rsh)
            neig[1][...] = ind[1][..., None] + np.r_[-1, -1, 0, 0].reshape(rsh)
            neig[0][(neig[0] < 0) | (neig[0] >= nRneig)] = -1
            neig[1][(neig[1] < 0) | (neig[1] >= nZneig)] = -1

        # return neighbours in desired format
        if returnas == 'ind':
            neig_out = neig
        else:
            neig_out = np.array([Rneig[neig[0]], Zneig[neig[1]]])
            neig_out[:, (neig[0] == -1) | (neig[1] == -1)] = np.nan

        return out, neig_out
    else:
        return out


# #############################################################################
# #############################################################################
#                           Mesh2D - select mesh tri
# #############################################################################


def _select_mesh_tri(
    coll=None,
    key=None,
    ind=None,
    elements=None,
    returnas=None,
    return_ind_as=None,
    return_neighbours=None,
):
    """ ind is a bool

    if returnas = 'ind', ind is returned as a bool array
    (because the nb. of neighbours is not constant on a triangular mesh)

    """

    # ------------
    # check inputs

    key = _generic_check._check_var(
        key, 'key',
        types=str,
        allowed=list(coll.dobj[coll._which_mesh].keys())
    )
    meshtype = coll.dobj[coll._which_mesh][key]['type']

    (
        elements, returnas,
        return_ind_as, return_neighbours,
    ) = _mesh_checks._select_check(
        elements=elements,
        returnas=returnas,
        return_ind_as=return_ind_as,
        return_neighbours=return_neighbours,
    )

    # ------------
    # prepare

    kn = coll.dobj[coll._which_mesh][key][elements]
    R = coll.ddata[kn[0]]['data']
    Z = coll.ddata[kn[1]]['data']

    # ------------
    # non-trivial case

    if returnas == 'ind':
        out = ind
    else:
        out = R[ind], Z[ind]

    # ------------
    # neighbours

    if return_neighbours is True:

        nind = ind.sum()
        kind = coll.dobj[coll._which_mesh][key]['ind']

        if returnas == 'data':
            elneig = 'cents' if elements == 'knots' else 'knots'
            kneig = coll.dobj[coll._which_mesh][key][elneig]
            Rneig = coll.ddata[kneig[0]]['data']
            Zneig = coll.ddata[kneig[1]]['data']

        if elements == 'cents':
            neig = coll.ddata[kind]['data'][ind, :]
            if returnas == 'ind':
                if return_ind_as is bool:
                    kknots = coll.dobj[coll._which_mesh][key]['knots']
                    import pdb; pdb.set_trace()     # DB
                    nneig = coll.dref[f'{kknots}-ind']['size']
                    neig_temp = np.zeros((nind, nneig), dtype=bool)
                    for ii in range(nind):
                        neig_temp[ii, neig[ii, :]] = True
                    neig = neig_temp
            else:
                neig = np.array([Rneig[neig], Zneig[neig]])
        else:
            ind_int = ind.nonzero()[0]
            neig = np.array([
                np.any(coll.ddata[kind]['data'] == ii, axis=1)
                for ii in ind_int
            ])
            c0 = returnas == 'ind' and return_ind_as is int
            if c0 or returnas == 'data':
                nmax = np.sum(neig, axis=1)
                if returnas == 'ind':
                    neig_temp = -np.ones((nind, nmax.max()), dtype=int)
                    for ii in range(nind):
                        neig_temp[ii, :nmax[ii]] = neig[ii, :].nonzero()[0]
                else:
                    neig_temp = np.full((2, nind, nmax.max()), np.nan)
                    for ii in range(nind):
                        neig_temp[0, ii, :nmax[ii]] = Rneig[neig[ii, :]]
                        neig_temp[1, ii, :nmax[ii]] = Zneig[neig[ii, :]]
                neig = neig_temp
        return out, neig
    else:
        return out


# #############################################################################
# #############################################################################
#                           Mesh2D - select bsplines rect
# #############################################################################


def _select_bsplines(
    coll=None,
    key=None,
    ind=None,
    returnas=None,
    return_cents=None,
    return_knots=None,
    crop=None,
):
    """ ind is a tuple """

    # ------------
    # check inputs

    _, returnas, _, _ = _mesh_checks._select_check(
        returnas=returnas,
    )

    key = _generic_check._check_var(
        key, 'key',
        types=str,
        allowed=list(coll.dobj.get('bsplines', {}).keys()),
    )

    keym = coll.dobj['bsplines'][key]['mesh']
    meshtype = coll.dobj['mesh'][keym]['type']

    # ----
    # ind

    ind = _select_ind(
        coll=coll,
        key=key,
        ind=ind,
        elements=None,
        returnas=tuple if meshtype == 'rect' else bool,
        crop=crop,
    )

    # ------------
    # knots, cents

    if meshtype == 'rect':
        kRk, kZk = coll.dobj['mesh'][keym]['knots']
        kRc, kZc = coll.dobj['mesh'][keym]['cents']

        out = _mesh2DRect_bsplines_knotscents(
            returnas=returnas,
            return_knots=return_knots,
            return_cents=return_cents,
            ind=ind,
            deg=coll.dobj['bsplines'][key]['deg'],
            Rknots=coll.ddata[kRk]['data'],
            Zknots=coll.ddata[kZk]['data'],
            Rcents=coll.ddata[kRc]['data'],
            Zcents=coll.ddata[kZc]['data'],
        )
    else:
        clas = coll.dobj['bsplines'][key]['class']
        out = clas._get_knotscents_per_bs(
            returnas=returnas,
            return_knots=return_knots,
            return_cents=return_cents,
            ind=ind,
        )

    # ------------
    # return

    if return_cents is True and return_knots is True:
        return ind, out[0], out[1]
    elif return_cents is True or return_knots is True:
        return ind, out
    else:
        return ind


# #############################################################################
# #############################################################################
#                           Mesh2D - select bsplines tri
# #############################################################################


# TODO


# #############################################################################
# #############################################################################
#                           Mesh2 - Tri - bsplines
# #############################################################################


def _mesh2DTri_bsplines(coll=None, keym=None, keybs=None, deg=None):

    # --------------
    # create bsplines

    kknots = coll.dobj[coll._which_mesh][keym]['knots']
    func_details, func_sum, clas = _mesh_bsplines_tri.get_bs2d_func(
        deg=deg,
        knotsR=coll.ddata[kknots[0]]['data'],
        knotsZ=coll.ddata[kknots[1]]['data'],
        cents=coll.ddata[coll.dobj[coll._which_mesh][keym]['ind']]['data'],
        trifind=coll.dobj[coll._which_mesh][keym]['trifind'],
    )
    keybsr = f'{keybs}-nbs'

    # ----------------
    # format into dict

    dref = {
        # bs index
        keybsr: {
            'size': clas.nbs,
        },
    }

    ddata = None

    dobj = {
        'bsplines': {
            keybs: {
                'deg': deg,
                'mesh': keym,
                'ref': (keybsr,),
                'shape': (clas.nbs,),
                'crop': False,
                'func_details': func_details,
                'func_sum': func_sum,
                'class': clas,
            }
        },
    }

    return dref, ddata, dobj


# #############################################################################
# #############################################################################
#                           Mesh2DRect - bsplines
# #############################################################################


def _mesh2DRect_bsplines(coll=None, keym=None, keybs=None, deg=None):

    # --------------
    # create bsplines

    kR, kZ = coll.dobj[coll._which_mesh][keym]['knots']
    Rknots = coll.ddata[kR]['data']
    Zknots = coll.ddata[kZ]['data']

    keybsr = f'{keybs}-nbs'
    kRbscr = f'{keybs}-nR'
    kZbscr = f'{keybs}-nZ'
    kRbsc = f'{keybs}-R'
    kZbsc = f'{keybs}-Z'

    (
        shapebs, Rbs_cent, Zbs_cent,
        knots_per_bs_R, knots_per_bs_Z,
    ) = _mesh_bsplines_rect.get_bs2d_RZ(
        deg=deg, Rknots=Rknots, Zknots=Zknots,
    )
    nbs = int(np.prod(shapebs))

    func_details, func_sum, clas = _mesh_bsplines_rect.get_bs2d_func(
        deg=deg,
        Rknots=Rknots,
        Zknots=Zknots,
        shapebs=shapebs,
        knots_per_bs_R=knots_per_bs_R,
        knots_per_bs_Z=knots_per_bs_Z,
    )

    # ----------------
    # format into dict

    dref = {
        kRbscr: {
            'size': Rbs_cent.size,
        },
        kZbscr: {
            'size': Zbs_cent.size,
        },
        keybsr: {
            'size': nbs,
        },
    }

    ddata = {
        kRbsc: {
            'data': Rbs_cent,
            'units': 'm',
            'dim': 'distance',
            'quant': 'R',
            'name': 'R',
            'ref': kRbscr,
        },
        kZbsc: {
            'data': Zbs_cent,
            'units': 'm',
            'dim': 'distance',
            'quant': 'R',
            'name': 'R',
            'ref': kZbscr,
        },
    }

    dobj = {
        'bsplines': {
            keybs: {
                'deg': deg,
                'mesh': keym,
                'ref': (kRbscr, kZbscr),
                'shape': shapebs,
                'crop': False,
                'func_details': func_details,
                'func_sum': func_sum,
                'class': clas,
            }
        },
    }

    return dref, ddata, dobj


def add_cropbs_from_crop(coll=None, keybs=None, keym=None):

    # ----------------
    # get

    kcropbs = False
    if coll.dobj[coll._which_mesh][keym]['crop'] is not False:
        kcropm = coll.dobj[coll._which_mesh][keym]['crop']
        cropbs = _get_cropbs_from_crop(
            coll=coll,
            crop=coll.ddata[kcropm]['data'],
            keybs=keybs,
        )
        kcropbs = f'{keybs}-crop'
        kcroppedbs = f'{keybs}-crop-nbs'

    # ----------------
    # optional crop

    if kcropbs is not False:

        # add cropped flat reference
        coll.add_ref(
            key=kcroppedbs,
            size=int(cropbs.sum()),
        )

        coll.add_data(
            key=kcropbs,
            data=cropbs,
            ref=coll._dobj['bsplines'][keybs]['ref'],
            dim='bool',
            quant='bool',
        )
        coll._dobj['bsplines'][keybs]['crop'] = kcropbs


def _mesh2DRect_bsplines_knotscents(
    returnas=None,
    return_knots=None,
    return_cents=None,
    ind=None,
    deg=None,
    Rknots=None,
    Zknots=None,
    Rcents=None,
    Zcents=None,
):

    # -------------
    # check inputs

    return_knots = _generic_check._check_var(
        return_knots, 'return_knots',
        types=bool,
        default=True,
    )
    return_cents = _generic_check._check_var(
        return_cents, 'return_cents',
        types=bool,
        default=True,
    )
    if return_knots is False and return_cents is False:
        return

    # -------------
    # compute

    if return_knots is True:

        knots_per_bs_R = _mesh_bsplines_rect._get_bs2d_func_knots(
            Rknots, deg=deg, returnas=returnas,
        )
        knots_per_bs_Z = _mesh_bsplines_rect._get_bs2d_func_knots(
            Zknots, deg=deg, returnas=returnas,
        )
        if ind is not None:
            knots_per_bs_R = knots_per_bs_R[:, ind[0]]
            knots_per_bs_Z = knots_per_bs_Z[:, ind[1]]

        nknots = knots_per_bs_R.shape[0]
        knots_per_bs_R = np.tile(knots_per_bs_R, (nknots, 1))
        knots_per_bs_Z = np.repeat(knots_per_bs_Z, nknots, axis=0)

    if return_cents is True:

        cents_per_bs_R = _mesh_bsplines_rect._get_bs2d_func_cents(
            Rcents, deg=deg, returnas=returnas,
        )
        cents_per_bs_Z = _mesh_bsplines_rect._get_bs2d_func_cents(
            Zcents, deg=deg, returnas=returnas,
        )
        if ind is not None:
            cents_per_bs_R = cents_per_bs_R[:, ind[0]]
            cents_per_bs_Z = cents_per_bs_Z[:, ind[1]]

        ncents = cents_per_bs_R.shape[0]
        cents_per_bs_R = np.tile(cents_per_bs_R, (ncents, 1))
        cents_per_bs_Z = np.repeat(cents_per_bs_Z, ncents, axis=0)

    # -------------
    # return

    if return_knots is True and return_cents is True:
        out = (
            (knots_per_bs_R, knots_per_bs_Z), (cents_per_bs_R, cents_per_bs_Z)
        )
    elif return_knots is True:
        out = (knots_per_bs_R, knots_per_bs_Z)
    else:
        out = (cents_per_bs_R, cents_per_bs_Z)
    return out


# #############################################################################
# #############################################################################
#                           Mesh2DRect - sample
# #############################################################################


def _sample_mesh_check(
    coll=None,
    key=None,
    res=None,
    mode=None,
    grid=None,
    imshow=None,
    R=None,
    Z=None,
    DR=None,
    DZ=None,
):

    # -----------
    # Parameters

    # key
    key = _generic_check._check_var(
        key, 'key',
        allowed=list(coll.dobj.get('mesh', {}).keys()),
        types=str,
    )
    meshtype = coll.dobj['mesh'][key]['type']

    # res
    if res is None:
        res = 0.1
    if np.isscalar(res):
        res = [res, res]
    c0 = (
        isinstance(res, list)
        and len(res) == 2
        and all([np.isscalar(rr) and rr > 0 for rr in res])
    )
    if not c0:
        msg = f"Arg res must be a list of 2 positive floats!\nProvided: {res}"
        raise Exception(msg)

    # mode
    mode = _generic_check._check_var(
        mode, 'mode',
        types=str,
        default='abs',
    )

    # grid
    grid = _generic_check._check_var(
        grid, 'grid',
        types=bool,
        default=False,
    )

    # imshow
    imshow = _generic_check._check_var(
        imshow, 'imshow',
        types=bool,
        default=False,
    )

    # R, Z
    if R is None and Z is None:
        pass
    elif R is None and np.isscalar(Z):
        pass
    elif Z is None and np.isscalar(R):
        pass
    else:
        msg = (
            "For mesh discretisation, (R, Z) can be either:\n"
            "\t- (None, None): will be created\n"
            "\t- (scalar, None): A vertical line will be created\n"
            "\t- (None, scalar): A horizontal line will be created\n"
        )
        raise Exception(msg)

    # -------------
    # R, Z

    if meshtype == 'rect':
        kR, kZ = coll.dobj['mesh'][key]['knots']
        Rk = coll.ddata[kR]['data']
        Zk = coll.ddata[kZ]['data']

        # custom R xor Z for vertical / horizontal lines only
        if R is None and Z is not None:
            R = Rk
        if Z is None and R is not None:
            Z = Zk
    else:
        kknots = coll.dobj['mesh'][key]['knots']
        Rk = coll.ddata[kknots[0]]['data']
        Zk = coll.ddata[kknots[1]]['data']

    # custom DR or DZ for mode='abs' only
    if DR is not None or DZ is not None:
        if mode != 'abs':
            msg = "Custom DR or DZ can only be provided with mode = 'abs'!"
            raise Exception(msg)

        for DD, DN in [(DR, 'DR'), (DZ, 'DZ')]:
            if DD is not None:
                c0 = (
                    hasattr(DD, '__iter__')
                    and len(DD) == 2
                    and all([
                        rr is None or (np.isscalar(rr) and np.isfinite(rr))
                        for rr in DD
                    ])
                )
                if not c0:
                    msg = f'Arg {DN} must be an iterable of 2 scalars!'
                    raise Exception(msg)

    if DR is None:
        DR = [Rk.min(), Rk.max()]
    if DZ is None:
        DZ = [Zk.min(), Zk.max()]

    return key, res, mode, grid, imshow, R, Z, DR, DZ, Rk, Zk


def sample_mesh(
    coll=None,
    key=None,
    res=None,
    mode=None,
    R=None,
    Z=None,
    DR=None,
    DZ=None,
    grid=None,
    imshow=None,
):

    # -------------
    # check inputs

    key, res, mode, grid, imshow, R, Z, DR, DZ, Rk, Zk = _sample_mesh_check(
        coll=coll,
        key=key,
        res=res,
        mode=mode,
        grid=grid,
        imshow=imshow,
        R=R,
        Z=Z,
        DR=DR,
        DZ=DZ,
    )

    # -------------
    # compute

    if mode == 'abs':
        if R is None:
            nR = int(np.ceil((DR[1] - DR[0]) / res[0]))
            R = np.linspace(DR[0], DR[1], nR)
        if Z is None:
            nZ = int(np.ceil((DZ[1] - DZ[0]) / res[1]))
            Z = np.linspace(DZ[0], DZ[1], nZ)
    else:
        if R is None:
            nR = int(np.ceil(1./res[0]))
            kR = np.linspace(0, 1, nR, endpoint=False)[None, :]
            R = np.concatenate((
                (Rk[:-1, None] + kR*np.diff(Rk)[:, None]).ravel(),
                Rk[-1:],
            ))
        if Z is None:
            nZ = int(np.ceil(1./res[1]))
            kZ = np.linspace(0, 1, nZ, endpoint=False)[None, :]
            Z = np.concatenate((
                (Zk[:-1, None] + kZ*np.diff(Zk)[:, None]).ravel(),
                Zk[-1:],
            ))

    if np.isscalar(R):
        R = np.full(Z.shape, R)
    if np.isscalar(Z):
        Z = np.full(R.shape, Z)

    # ------------
    # grid

    if grid is True:
        nZ = Z.size
        nR = R.size
        if imshow is True:
            R = np.tile(R, (nZ, 1))
            Z = np.repeat(Z[:, None], nR, axis=1)
        else:
            R = np.repeat(R[:, None], nZ, axis=1)
            Z = np.tile(Z, (nR, 1))

    return R, Z


# #############################################################################
# #############################################################################
#                           Mesh2DRect - crop
# #############################################################################


def _crop_check(
    coll=None,
    key=None,
    crop=None,
    thresh_in=None,
    remove_isolated=None,
):

    # key
    lkm = list(coll.dobj[coll._which_mesh].keys())
    key = _generic_check._check_var(
        key, 'key',
        default=None,
        types=str,
        allowed=lkm,
    )
    meshtype = coll.dobj[coll._which_mesh][key]['type']

    if meshtype != 'rect':
        raise NotImplementedError()

    # shape
    shape = coll.dobj[coll._which_mesh][key]['shape-c']

    # crop
    c0 = (
        isinstance(crop, np.ndarray)
        and crop.ndim == 2
        and np.all(np.isfinite(crop))
        and (
            (
                crop.shape[0] == 2
                and np.allclose(crop[:, 0], crop[:, -1])
                and (
                    np.issubdtype(crop.dtype, np.integer)
                    or np.issubdtype(crop.dtype, np.floating)
                )
            )
            or (
                crop.shape == shape
                and crop.dtype == np.bool_
            )
        )
    )
    if not c0:
        msg = (
            "Arg crop must be either:\n"
            f"\t- array of bool: mask of shape {shape}\n"
            f"\t- array of floats: (2, npts) closed (R, Z) polygon\n"
            f"Provided:\n{crop}"
        )
        raise Exception(msg)

    cropbool = crop.dtype == np.bool_

    # thresh_in and maxth
    if thresh_in is None:
        thresh_in = 3
    maxth = 5 if coll.dobj[coll._which_mesh][key]['type'] == 'rect' else 4

    c0 = isinstance(thresh_in, (int, np.integer)) and (1 <= thresh_in <= maxth)
    if not c0:
        msg = (
            f"Arg thresh_in must be a int in {1} <= thresh_in <= {maxth}\n"
            f"Provided: {thresh_in}"
        )
        raise Exception(msg)

    # remove_isolated
    remove_isolated = _generic_check._check_var(
        remove_isolated, 'remove_isolated',
        default=True,
        types=bool,
    )

    return key, cropbool, thresh_in, remove_isolated


def crop(
    coll=None,
    key=None,
    crop=None,
    thresh_in=None,
    remove_isolated=None,
):
    """ Crop a rect mesh

    Parameters
    ----------
    key:        str
        key of the rect mesh to be cropped
    crop:      np.ndarray
        Can be either:
            - bool: a boolean mask array
            - float: a closed 2d polygon used for cropping
    threshin:   int
        minimum nb. of corners for a mesh element to be included
    remove_isolated: bool
        flag indicating whether to remove isolated mesh elements

    Return
    ------
    crop:       np.ndarray
        bool mask
    key:        str
        key of the rect mesh to be cropped
    thresh_in:  int
        minimum nb. of corners for a mesh element to be included

    """

    # ------------
    # check inputs

    key, cropbool, thresh_in, remove_isolated = _crop_check(
        coll=coll, key=key, crop=crop, thresh_in=thresh_in,
        remove_isolated=remove_isolated,
    )

    # -----------
    # if crop is a poly => compute as bool

    if not cropbool:

        (Rc, Zc), (Rk, Zk) = coll.select_mesh_elements(
            key=key, elements='cents',
            return_neighbours=True, returnas='data',
        )
        nR, nZ = Rc.shape
        npts = Rk.shape[-1] + 1

        pts = np.concatenate(
            (
                np.concatenate((Rc[:, :, None], Rk), axis=-1)[..., None],
                np.concatenate((Zc[:, :, None], Zk), axis=-1)[..., None],
            ),
            axis=-1,
        ).reshape((npts*nR*nZ, 2))

        isin = Path(crop.T).contains_points(pts).reshape((nR, nZ, npts))
        crop = np.sum(isin, axis=-1) >= thresh_in

        # Remove isolated pixelsi
        if remove_isolated is True:
            # All pixels should have at least one neighbour in R and one in Z
            # This constraint is useful for discrete gradient evaluation (D1N2)
            neighR = np.copy(crop)
            neighR[0, :] &= neighR[1, :]
            neighR[-1, :] &= neighR[-2, :]
            neighR[1:-1, :] &= (neighR[:-2, :] | neighR[2:, :])
            neighZ = np.copy(crop)
            neighZ[:, 0] &= neighZ[:, 1]
            neighZ[:, -1] &= neighZ[:, -2]
            neighZ[:, 1:-1] &= (neighZ[:, :-2] | neighZ[:, 2:])
            crop = neighR & neighZ

    return crop, key, thresh_in


def _get_cropbs_from_crop(coll=None, crop=None, keybs=None):

    if isinstance(crop, str) and crop in coll.ddata.keys():
        crop = coll.ddata[crop]['data']

    shref = coll.dobj[coll._which_mesh][coll.dobj['bsplines'][keybs]['mesh']]['shape-c']
    if crop.shape != shref:
        msg = "Arg crop seems to have the wrong shape!"
        raise Exception(msg)

    keym = coll.dobj['bsplines'][keybs][coll._which_mesh]
    kRk, kZk = coll.dobj['mesh'][keym]['knots']
    kRc, kZc = coll.dobj['mesh'][keym]['cents']

    cents_per_bs_R, cents_per_bs_Z = _mesh2DRect_bsplines_knotscents(
        returnas='ind',
        return_knots=False,
        return_cents=True,
        ind=None,
        deg=coll.dobj['bsplines'][keybs]['deg'],
        Rknots=coll.ddata[kRk]['data'],
        Zknots=coll.ddata[kZk]['data'],
        Rcents=coll.ddata[kRc]['data'],
        Zcents=coll.ddata[kZc]['data'],
    )

    shapebs = coll.dobj['bsplines'][keybs]['shape']
    cropbs = np.array([
        [
            np.all(crop[cents_per_bs_R[:, ii], cents_per_bs_Z[:, jj]])
            for jj in range(shapebs[1])
        ]
        for ii in range(shapebs[0])
    ], dtype=bool)

    return cropbs


# #############################################################################
# #############################################################################
#                           Mesh2DRect - interp
# #############################################################################


def _interp_check(
    coll=None,
    key=None,
    R=None,
    Z=None,
    grid=None,
    indbs=None,
    indt=None,
    details=None,
    res=None,
    coefs=None,
    crop=None,
    nan0=None,
    imshow=None,
):
    # key
    dk = {
        kk: [
            k1 for k1, v1 in coll.dobj['bsplines'].items()
            if coll.ddata[kk]['ref'][-2:] == v1['ref']
        ][0]
        for kk in coll.ddata.keys()
        if any([
            coll.ddata[kk]['ref'][-2:] == v1['ref']
            for v1 in coll.dobj['bsplines'].values()
        ])
        and 'crop' not in kk
    }
    dk.update({kk: kk for kk in coll.dobj['bsplines'].keys()})
    if key is None and len(dk) == 1:
        key = list(dk.keys())[0]
    if key not in dk.keys():
        msg = (
            "Arg key must the key to a data referenced on a bsplines set\n"
            f"\t- available: {dk.keys()}\n"
            f"\t- provided: {key}\n"
        )
        raise Exception(msg)
    keybs = dk[key]
    keym = coll.dobj['bsplines'][keybs]['mesh']

    # coefs
    shapebs = coll.dobj['bsplines'][keybs]['shape']
    if coefs is None:
        if key == keybs:
            pass
        else:
            coefs = coll.ddata[key]['data']
    else:
        c0 = (
            coefs.ndim in [len(shapebs), len(shapebs) + 1]
            and coefs.shape[-2:] == shapebs
        )
        if not c0:
            msg = (
                f"Arg coefs must be a {shapebs} array!\n"
                f"Provided: {coefs.shape}"
            )
            raise Exception(msg)

    # indbs

    # indt
    c0 = (
        indt is not None
        and coefs is not None
        and coefs.ndim == len(shapebs) + 1
    )
    if c0:
        if coefs.shape[0] == 1:
            indt = 0
        try:
            assert np.isscalar(indt) and np.isfinite(indt)
            assert indt < coefs.shape[0]
            indt = int(indt)
        except Exception as err:
            msg = (
                f"Arg indt should be a int!\nProvided: {indt}"
            )
            raise Exception(msg)
        coefs = coefs[indt:indt+1, ...]

    # details
    details = _generic_check._check_var(
        details, 'details',
        types=bool,
        default=False,
    )

    # crop
    crop = _generic_check._check_var(
        crop, 'crop',
        types=bool,
        default=True,
    )

    # nan0
    nan0 = _generic_check._check_var(
        nan0, 'nan0',
        types=bool,
        default=True,
    )

    # R, Z
    if R is None or Z is None:
        R, Z = coll.get_sample_mesh(
            key=keym,
            res=res,
            mode='abs',
            grid=True,
            R=R,
            Z=Z,
            imshow=imshow,
        )
    else:
        if not isinstance(R, np.ndarray):
            try:
                R = np.atleast_1d(R).astype(float)
            except Exception as err:
                msg = "R must be convertible to np.arrays of floats"
                raise Exception(msg)
        if not isinstance(Z, np.ndarray):
            try:
                Z = np.atleast_1d(Z).astype(float)
            except Exception as err:
                msg = "Z must be convertible to np.arrays of floats"
                raise Exception(msg)

        # grid
        grid = _generic_check._check_var(
            grid, 'grid',
            default=R.shape != Z.shape,
            types=bool,
        )

        if grid is True and (R.ndim > 1 or Z.ndim > 1):
            msg = "If grid=True, R and Z must be 1d!"
            raise Exception(msg)
        elif grid is False and R.shape != Z.shape:
            msg = "If grid=False, R and Z must have the same shape!"
            raise Exception(msg)

        if grid is True:
            R = np.tile(R, Z.size)
            Z = np.repeat(Z, R.size)

    return key, keybs, R, Z, coefs, indbs, indt, details, crop, nan0


def interp2d(
    coll=None,
    key=None,
    R=None,
    Z=None,
    coefs=None,
    indbs=None,
    indt=None,
    grid=None,
    details=None,
    reshape=None,
    res=None,
    crop=None,
    nan0=None,
    imshow=None,
):

    # ---------------
    # check inputs

    key, keybs, R, Z, coefs, indbs, indt, details, crop, nan0 = _interp_check(
        coll=coll,
        key=key,
        R=R,
        Z=Z,
        coefs=coefs,
        indbs=indbs,
        indt=indt,
        grid=grid,
        details=details,
        res=res,
        crop=crop,
        nan0=nan0,
        imshow=imshow,
    )
    keym = coll.dobj['bsplines'][keybs]['mesh']
    meshtype = coll.dobj['mesh'][keym]['type']

    # ---------------
    # prepare

    if details is True:
        fname = 'func_details'
    elif details is False:
        fname = 'func_sum'
    else:
        raise Exception("Unknown details!")

    # ---------------
    # interp

    cropbs = coll.dobj['bsplines'][keybs]['crop']
    if cropbs is not False:
        cropbs = coll.ddata[cropbs]['data']

    if details is not False:
        if meshtype == 'rect':
            returnas = 'tuple-flat'
        else:
            returnas = bool
        indbs_tuple_flat = coll.select_ind(
            key=keybs,
            returnas=returnas,
            ind=indbs,
        )
    else:
        indbs_tuple_flat = None

    val = coll.dobj['bsplines'][keybs][fname](
        R, Z,
        coefs=coefs,
        crop=crop,
        cropbs=cropbs,
        indbs_tuple_flat=indbs_tuple_flat,
        reshape=reshape,
    )

    # ---------------
    # post-treatment

    if nan0 is True:
        val[val == 0] = np.nan

    return val


# #############################################################################
# #############################################################################
#                           Mesh2DRect - operators
# #############################################################################


def get_bsplines_operator(
    coll,
    key=None,
    operator=None,
    geometry=None,
    crop=None,
    store=None,
    returnas=None,
    # specific to deg = 0
    centered=None,
    # to return gradR, gradZ, for D1N2 deg 0, for tomotok
    returnas_element=None,
):

    # check inputs
    lk = list(coll.dobj.get('bsplines', {}).keys())
    key = _generic_check._check_var(
        key, 'key',
        types=str,
        allowed=lk,
    )

    store = _generic_check._check_var(
        store, 'store',
        default=True,
        types=bool,
    )

    returnas = _generic_check._check_var(
        returnas, 'returnas',
        default=store is False,
        types=bool,
    )

    crop = _generic_check._check_var(
        crop, 'crop',
        default=True,
        types=bool,
    )

    cropbs = coll.dobj['bsplines'][key]['crop']
    if cropbs is not False and crop is True:
        cropbs_flat = coll.ddata[cropbs]['data'].ravel(order='F')
        if coll.dobj['bsplines'][key]['deg'] == 0:
            cropbs = coll.ddata[cropbs]['data']
        keycropped = f'{key}-cropped'
    else:
        cropbs = False
        cropbs_flat = False
        keycropped = key

    # compute and return
    (
        opmat, operator, geometry, dim,
    ) = coll.dobj['bsplines'][key]['class'].get_operator(
        operator=operator,
        geometry=geometry,
        cropbs_flat=cropbs_flat,
        # specific to deg=0
        cropbs=cropbs,
        centered=centered,
        # to return gradR, gradZ, for D1N2 deg 0, for tomotok
        returnas_element=returnas_element,
    )

    # cropping
    if operator == 'D1':
        ref = (keycropped, keycropped)
    elif operator == 'D0N1':
        ref = (keycropped,)
    elif 'N2' in operator:
        ref = (keycropped, keycropped)

    return opmat, operator, geometry, dim, ref, crop, store, returnas, key
