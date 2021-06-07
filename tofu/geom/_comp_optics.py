

import warnings

import numpy as np
import scipy.interpolate as scpinterp
import scipy.stats as scpstats
import matplotlib.pyplot as plt


_LTYPES = [int, float, np.int_, np.float_]



# ###############################################
#           utility
# ###############################################

def _are_broadcastable(**kwdargs):

    lv = list(kwdargs.values())
    c0 = (
        all([isinstance(vv, np.ndarray) for vv in lv])
        and all([
            all([
                (m == n) or (m == 1) or (n == 1)
                for m, n in zip(vv.shape[::-1], lv[0].shape[::-1])
            ])
            for vv in lv
        ])
    )
    if not c0:
        msg = (
            "All args must be broadcastable with each other!\n"
            + "You provided:\n"
            + "\n".join([
                '\t- {}.shape = {}'.format(k0, v0.shape)
                for k0, v0 in kwdargs.items()
            ])
        )
        raise Exception(msg)


# ###############################################
# ###############################################
#           CrystalBragg
# ###############################################
# ###############################################

# ###############################################
#           sampling
# ###############################################


def _check_dthetapsi(
    dtheta=None, psi=None,
    extenthalf_psi=None, extenthalf_dtheta=None,
    ntheta=None, npsi=None,
    include_summit=None,
):
    # Check inputs
    if dtheta is None:
        dtheta = 0.
    if psi is None:
        psi = 0.

    # if envelop => get all points around cryst + summit
    if any([isinstance(vv, str) and vv == 'envelop' for vv in [dtheta, psi]]):
        psi, dtheta = CrystBragg_sample_outline_sphrect(
            extenthalf_psi, extenthalf_dtheta,
            npsi=npsi, ntheta=ntheta,
            include_summit=include_summit,
        )

    c0 = all([
        type(vv) in _LTYPES
        or isinstance(vv, np.ndarray)
        for vv in [dtheta, psi]
    ])

    dtheta = np.atleast_1d(dtheta)
    psi = np.atleast_1d(psi)
    if psi.shape != dtheta.shape:
        msg = (
            "dtheta and psi should have the same shape\n"
            + "\t- dtheta.shape = {}\n".format(dtheta.shape)
            + "\t- psi.shape = {}".format(psi.shape)
        )
        raise Exception(msg)
    return dtheta, psi


def CrystBragg_sample_outline_sphrect(
    extent_psi, extent_dtheta,
    npsi=None, ntheta=None,
    include_summit=None,
):
    # check inputs
    if include_summit is None:
        include_summit = True
    if ntheta is None:
        ntheta = 5
    if npsi is None:
        npsi = 3

    # compute
    psi = extent_psi*np.linspace(-1, 1., npsi)
    dtheta = extent_dtheta*np.linspace(-1, 1., ntheta)
    psimin = np.full((ntheta,), psi[0])
    psimax = np.full((ntheta,), psi[-1])
    dthetamin = np.full((npsi,), dtheta[0])
    dthetamax = np.full((npsi,), dtheta[-1])
    psi = np.concatenate((psi, psimax, psi[::-1], psimin))
    dtheta = np.concatenate((dthetamin, dtheta, dthetamax, dtheta[::-1]))
    if include_summit is True:
        psi = np.r_[psi, 0.]
        dtheta = np.r_[dtheta, 0.]
    return psi, dtheta


def CrystBragg_get_noute1e2_from_psitheta(
    nout, e1, e2,
    psi=None, dtheta=None,
    e1e2=None, sameshape=None,
    extenthalf_psi=None,
    extenthalf_dtheta=None,
    ntheta=None, npsi=None,
    include_summit=None,
):
    # check inputs
    if e1e2 is None:
        e1e2 = True
    if sameshape is None:
        sameshape = psi.shape == nout.shape[1:]
    if sameshape:
        assert psi.shape == nout.shape[1:]

    dtheta, psi = _check_dthetapsi(
        dtheta=dtheta, psi=psi,
        extenthalf_psi=extenthalf_psi,
        extenthalf_dtheta=extenthalf_dtheta,
        ntheta=ntheta, npsi=npsi,
        include_summit=include_summit,
    )

    # Prepare
    if sameshape is False:
        assert psi.ndim in [1, 2, 3, 4]
        if psi.ndim == 1:
            nout = nout[:, None]
            e1, e2 = e1[:, None], e2[:, None]
        elif psi.ndim == 2:
            nout = nout[:, None, None]
            e1, e2 = e1[:, None, None], e2[:, None, None]
        elif psi.ndim == 3:
            nout = nout[:, None, None, None]
            e1, e2 = e1[:, None, None, None], e2[:, None, None, None]
        else:
            nout = nout[:, None, None, None, None]
            e1 = e1[:, None, None, None, None]
            e2 = e2[:, None, None, None, None]

    # Not necessary for broadcasting (last dims first)
    theta = np.pi/2.  + dtheta# [None, ...]
    #psi = psi[None, ...]

    # Compute
    vout = (
         (np.cos(psi)*nout + np.sin(psi)*e1)*np.sin(theta) + np.cos(theta)*e2
         )
    if e1e2:
        ve1 = -np.sin(psi)*nout + np.cos(psi)*e1
        ve2 = np.array([vout[1, ...]*ve1[2, ...] - vout[2, ...]*ve1[1, ...],
                        vout[2, ...]*ve1[0, ...] - vout[0, ...]*ve1[2, ...],
                        vout[0, ...]*ve1[1, ...] - vout[1, ...]*ve1[0, ...]])
        return vout, ve1, ve2
    else:
        return vout


def CrystBragg_sample_outline_plot_sphrect(
    center, nout, e1, e2,
    rcurve, extenthalf, res=None,
):
    """ Get the set of points in (x, y, z) coordinates sampling the crystal
    outline
    """

    # check inputs
    if res is None:
        res = np.min(extenthalf)/5.

    # compute
    npsi = 2*int(np.ceil(extenthalf[0] / res)) + 1
    ntheta = 2*int(np.ceil(extenthalf[1] / res)) + 1

    psi, dtheta = CrystBragg_sample_outline_sphrect(
        extenthalf[0], extenthalf[1],
        npsi=npsi, ntheta=ntheta,
        include_summit=False,
    )

    vout = CrystBragg_get_noute1e2_from_psitheta(
        nout, e1, e2, psi, dtheta,
        e1e2=False, sameshape=False,
    )
    return center[:, None] + rcurve*vout


# ###############################################
#           lamb <=> bragg
# ###############################################

def get_bragg_from_lamb(lamb, d, n=None):
    """ n*lamb = 2d*sin(bragg)
    The angle bragg is defined as the angle of incidence of the emissed photon
    vector and the crystal mesh, and not the crystal dioptre.
    For record, both are parallel and coplanar when is defined parallelism
    into the crystal.
    """
    if n is None:
        n = 1
    bragg = np.full(lamb.shape, np.nan)
    sin = n*lamb/(2.*d)
    indok = np.abs(sin) <= 1.
    bragg[indok] = np.arcsin(sin[indok])
    return bragg

def get_lamb_from_bragg(bragg, d, n=None):
    """ n*lamb = 2d*sin(bragg)
    The angle bragg is defined as the angle of incidence of the emissed photon
    vector and the crystal mesh, and not the crystal dioptre.
    For record, both are parallel and coplanar when is defined parallelism
    into the crystal.
    """
    if n is None:
        n = 1
    return 2*d*np.sin(bragg) / n

# ###############################################
#           vectors <=> angles
# ###############################################

def get_vectors_from_angles(alpha, beta, nout, e1, e2):
    """Return new unit vectors according to alpha and beta entries from user
    caused by the non parallelism assumed on the crystal.
    """

    e1_bis = np.cos(alpha)*(
                    np.cos(beta)*e1 + np.sin(beta)*e2
                    ) - np.sin(alpha)*nout

    e2_bis = np.cos(beta)*e2-np.sin(beta)*e1

    nout_bis = np.cos(alpha)*nout + np.sin(alpha)*(
             np.cos(beta)*e1+ np.sin(beta)*e2
             )
    nin_bis = -nout_bis

    return nin_bis, nout_bis, e1_bis, e2_bis


# ###############################################
#           Approximate solution
# ###############################################


def get_rowland_dist_from_bragg(bragg=None, rcurve=None):
    return rcurve*np.sin(bragg)


def get_approx_detector_rel(rcurve, bragg,
                            braggref=None, xiref=None,
                            bragg01=None, dist01=None,
                            tangent_to_rowland=None):
    """ Return the approximative detector position on the Rowland circle
    relatively to the Bragg crystal.
    Possibility to define tangential position of the detector to the Rowland
    circle or not.
    On WEST, the maximum non-parallelism between two halves can be up to few
    arcmin so here, doesn't need to define the precise location of the detector.
    The bragg angle is provided and naturally defined as the angle between the
    emissed photon vector and the crystal mesh.
    So, if non parallelism approuved, bragg is relative
    to the vector basis dmat(nout,e1,e2).
    The position of the detector, relatively to the crystal, will be so in
    another Rowland circle with its center shifted from the original one.
    """

    if tangent_to_rowland is None:
        tangent_to_rowland = True

    # distance crystal - det_center
    ## bragg between incident vector and mesh
    det_dist = rcurve*np.sin(bragg)

    # det_nout and det_e1 in (nout, e1, e2) (det_e2 = e2)
    n_crystdet_rel = np.r_[-np.sin(bragg), np.cos(bragg), 0.]
    if tangent_to_rowland is True:
        bragg2 = 2.*bragg
        det_nout_rel = np.r_[-np.cos(bragg2), -np.sin(bragg2), 0.]
        det_ei_rel = np.r_[np.sin(bragg2), -np.cos(bragg2), 0.]
    else:
        det_nout_rel = -n_crystdet_rel
        det_ei_rel = np.r_[np.cos(bragg), np.sin(bragg), 0]

    # update with bragg01 and dist01
    if bragg01 is not None:
        ang = np.diff(np.sort(bragg01))
        # h = l1 tan(theta1) = l2 tan(theta2)
        # l = l2 (tan(theta1) + tan(theta2)) / tan(theta1)
        # l = l2 / cos(theta2)
        # l = l tan(theta1) / (cos(theta2) * (tan(theta1) + tan(theta2)))
        theta2 = bragg  if tangent_to_rowland is True else np.pi/2
        theta1 = np.abs(bragg-bragg01[0])
        tan1 = np.tan(theta1)
        d0 = det_dist * tan1 / (np.cos(theta2) * (tan1+np.tan(theta2)))
        theta1 = np.abs(bragg-bragg01[1])
        tan1 = np.tan(theta1)
        d1 = det_dist * tan1 / (np.cos(theta2) * (tan1+np.tan(theta2)))
        if np.prod(np.sign(bragg01-bragg)) >= 0:
            d01 = np.abs(d0 - d1)
        else:
            d01 = d0 + d1
        det_dist = det_dist * dist01 / d01

    return det_dist, n_crystdet_rel, det_nout_rel, det_ei_rel


def get_det_abs_from_rel(det_dist, n_crystdet_rel, det_nout_rel, det_ei_rel,
                         summit, nout, e1, e2,
                         ddist=None, di=None, dj=None,
                         dtheta=None, dpsi=None, tilt=None):
    """ Return the absolute detector position, according to tokamak's frame,
    on the Rowland circle from its relative position to the Bragg crystal.
    If non parallelism approuved, bragg is relative to the vector basis
    dmat(nout,e1,e2).
    The position of the detector, relatively to the crystal, will be so in
    another Rowland circle with its center shifted from the original one.
    """

    # Reference on detector
    det_nout = (det_nout_rel[0]*nout
                + det_nout_rel[1]*e1 + det_nout_rel[2]*e2)
    det_ei = (det_ei_rel[0]*nout
                + det_ei_rel[1]*e1 + det_ei_rel[2]*e2)
    det_ej = np.cross(det_nout, det_ei)

    # Apply translation of center (ddist, di, dj)
    if ddist is None:
        ddist = 0.
    if di is None:
        di = 0.
    if dj is None:
        dj = 0.
    det_dist += ddist

    n_crystdet = (n_crystdet_rel[0]*nout
                  + n_crystdet_rel[1]*e1 + n_crystdet_rel[2]*e2)
    det_cent = summit + det_dist*n_crystdet + di*det_ei + dj*det_ej

    # Apply angles on unit vectors with respect to themselves
    if dtheta is None:
        dtheta = 0.
    if dpsi is None:
        dpsi = 0.
    if tilt is None:
        tilt = 0.

    # dtheta and dpsi
    det_nout2 = ((np.cos(dpsi)*det_nout
                 + np.sin(dpsi)*det_ei)*np.cos(dtheta)
                 + np.sin(dtheta)*det_ej)
    det_ei2 = (np.cos(dpsi)*det_ei - np.sin(dpsi)*det_nout)
    det_ej2 = np.cross(det_nout2, det_ei2)

    # tilt
    det_ei3 = np.cos(tilt)*det_ei2 + np.sin(tilt)*det_ej2
    det_ej3 = np.cross(det_nout2, det_ei3)

    return det_cent, det_nout2, det_ei3, det_ej3


# ###############################################
#           Coordinates transforms
# ###############################################


def checkformat_vectang(Z, nn, frame_cent, frame_ang):
    # Check / format inputs
    nn = np.atleast_1d(nn).ravel()
    assert nn.size == 3
    nn = nn / np.linalg.norm(nn)
    Z = float(Z)

    frame_cent = np.atleast_1d(frame_cent).ravel()
    assert frame_cent.size == 2
    frame_ang = float(frame_ang)

    return Z, nn, frame_cent, frame_ang


def get_e1e2_detectorplane(nn, nIn):
    e1 = np.cross(nn, nIn)
    e1n = np.linalg.norm(e1)
    if e1n < 1.e-10:
        e1 = np.array([nIn[2], -nIn[1], 0.])
        e1n = np.linalg.norm(e1)
    e1 = e1 / e1n
    e2 = np.cross(nn, e1)
    e2 = e2 / np.linalg.norm(e2)
    return e1, e2


def calc_xixj_from_braggphi(
    det_cent=None, det_nout=None, det_ei=None, det_ej=None,
    summit=None, nout=None, e1=None, e2=None,
    bragg=None, phi=None,
    option=None,
):
    """ Several options for shapes

    de_cent, det_nout, det_ei and det_ej are always of shape (3,)

    option:
        0:
            (summit, e1, e2).shape = (3,)
            (bragg, phi).shape = (nbragg,)
            => (xi, xj).shape = (nbragg,)
        1:
            (summit, e1, e2).shape = (3, nlamb, npts, nbragg)
            (bragg, phi).shape = (nlamb, npts, nbragg)
            => (xi, xj).shape = (nlamb, npts, nbragg)
    """
    # Check option
    gdet = [det_cent, det_nout, det_ei, det_ej]
    g0 = [summit, nout, e1, e2]
    g1 = [bragg, phi]

    # check nbroadcastable
    _are_broadcastable(bragg=bragg, phi=phi)
    assert all([gg.shape == (3,) for gg in gdet]), "gdet no broadcast!"
    assert all([gg.shape == g0[0].shape for gg in g0]), "g0 no broadcast!"
    lc = [
        g0[0].shape[0] == 3 and g1[0].ndim == 1,
        g0[0].ndim in [4, 5] and g0[0].shape[0] == 3
        and phi.shape == g0[0].shape[1:],
    ]
    assert np.sum(lc) == 1, "Multiple options!"
    if option is None:
        option = lc.index(True)
    assert (lc[0] and option == 0) or (lc[1] and option == 1)

    # Prepare
    summit, nout, e1, e2 = (
        summit.ravel(), nout.ravel(),
        e1.ravel(), e2.ravel(),
        )

    if option == 0:
        det_cent = det_cent[:, None]
        det_nout = det_nout[:, None]
        det_ei, det_ej = det_ei[:, None], det_ej[:, None]
        summit, nout = summit[:, None], nout[:, None],
        e1, e2 = e1[:, None], e2[:, None]
    else:
        det_cent = det_cent[:, None, None, None]
        det_nout = det_nout[:, None, None, None]
        det_ei = det_ei[:, None, None, None]
        det_ej = det_ej[:, None, None, None]
        if g0[0].ndim == 5:
            det_cent = det_cent[..., None]
            det_nout = det_nout[..., None]
            det_ei = det_ei[..., None]
            det_ej = det_ej[..., None]

    # Not necessary for broadcasting (last dims first)
    # bragg = bragg[None, ...]
    # phi = phi[None, ...]

    # Compute
    vect = (
        -np.sin(bragg)*nout
        + np.cos(bragg)*(np.cos(phi)*e1 + np.sin(phi)*e2)
    )
    k = np.sum(
        (det_cent-summit)*det_nout, axis=0
        ) / np.sum(vect*det_nout, axis=0)
    pts = summit + k[None, ...]*vect
    xi = np.sum((pts - det_cent)*det_ei, axis=0)
    xj = np.sum((pts - det_cent)*det_ej, axis=0)
    return xi, xj


def calc_braggphi_from_pts_summits(
    pts=None,
    summits=None,
    vin=None, ve1=None, ve2=None,
):
    # check inputs
    _are_broadcastable(pts=pts, summits=summits, vin=vin, ve1=ve1, ve2=ve2)

    # compute
    vect = pts - summits
    vect = vect / np.sqrt(np.sum(vect**2, axis=0))[None, ...]
    bragg = np.arcsin(np.sum(vect*vin, axis=0))
    if np.any(bragg < 0.):
        msg = (
            "There seems to be negative bragg angles!\n"
            + "  => double-check inputs!"
        )
        raise Exception(msg)
    phi = np.arctan2(np.sum(vect*ve2, axis=0), np.sum(vect*ve1, axis=0))
    return bragg, phi


def calc_braggphi_from_xixjpts(
    det_cent, det_ei, det_ej,
    summit, nin, e1, e2,
    xi=None, xj=None, pts=None,
    grid=None,
):
    """ Return bragg phi for pts or (xj, xi) seen from (summit, nin, e1, e2)

    Either provide:
        pts => (3, npts)
        xi, xj => pts with shape (3, nxi, nxj)

    summit, nin, e1, e2 must have the same shape (3, nsumm)

    bragg.shape = (nsum, )

    if grid is True:
        all pts evaluated for all summ/nin
        return  (nsumm, npts) or (nsum, nxi, nxj) arrays
    else:
        each pts has a unique corresponding summ/nin (except possibly ndtheta)
        return (npts,) or (nxi, nxj) arrays
            or (npts, ndtheta) or (nxi, nxj, ndtheta) arrays
    """

    # --------------
    # Check format
    if grid is None:
        grid = True

    lc = [pts is not None, all([xx is not None for xx in [xi, xj]])]
    if np.sum(lc) != 1:
        msg = "Provide either pts xor (xi, xj)!"
        raise Exception(msg)

    if lc[0]:
        assert pts.shape[0] == 3
        if pts.ndim == 1:
            pts = pts.reshape((3, 1))
    elif lc[1]:
        xi = np.atleast_1d(xi)
        xj = np.atleast_1d(xj)
        if xi.shape != xj.shape:
            msg = "xi and xj must have the same shape!"
            raise Exception(msg)
        assert xi.ndim in [1, 2]
        if xi.ndim == 1:
            pts = (det_cent[:, None]
                   + xi[None, :]*det_ei[:, None]
                   + xj[None, :]*det_ej[:, None])
        else:
            pts = (det_cent[:, None, None]
                   + xi[None, ...]*det_ei[:, None, None]
                   + xj[None, ...]*det_ej[:, None, None])

    c0 = summit.shape == nin.shape == e1.shape == e2.shape
    if not c0:
        msg = "(summit, nin, e1, e2) must all have the same shape"
        raise Exception(msg)
    ndimsum = summit.ndim
    ndimpts = pts.ndim
    assert ndimsum in [1, 2, 3, 4, 5], summit.shape
    err = False
    c0 = (
        (
            grid is True
            and pts.ndim in [1, 2, 3]
            and summit.ndim in [1, 2, 3, 4]
        )
        or (
            grid is False
        )
    )
    if not c0:
        msg = (
            "Args pts and summit/nin/e1/e2 must be such that:\n"
            + "\t- grid = True:\n"
            + "\t\tpts.ndim in [1, 2, 3] and pts.shape[0] == 3\n"
            + "\t\tsummit.ndim in [1, 2, 3, 4]\n"
            + "\t- grid = False:\n"
            + "\t\tpts can be directly broadcasted to summit\n"
            + "  You provided:\n"
            + "\t- pts.shape = {}\n".format(pts.shape)
            + "\t- summit.shape = {}".format(summit.shape)
        )
        raise Exception(msg)


    # --------------
    # Prepare
    # This part should be re-checked for all combinations !
    if grid is True:
        if ndimpts == 2:
            summit = summit[..., None]
            nin, e1, e2 = nin[..., None], e1[..., None], e2[..., None]
        else:
            summit = summit[..., None, None]
            nin = nin[..., None, None]
            e1, e2 = e1[..., None, None], e2[..., None, None]
        if ndimsum == 1:
            pass
        elif ndimsum == 2:
            pts = pts[:, None, ...]
        elif ndimsum == 3:
            pts = pts[:, None, ...]
        elif ndimsum == 4:
            pts = pts[:, None, :, None]
    else:
        pass

    # --------------
    # Compute
    # Everything has shape (3, nxi0, nxi1, npts0, npts1) => sum on axis=0
    # or is broadcastable
    return calc_braggphi_from_pts_summits(
        pts=pts,
        summits=summit,
        vin=nin, ve1=e1, ve2=e2,
    )


# ###############################################
#           2D spectra to 1D
# ###############################################


def get_lambphifit(lamb, phi, nxi, nxj):
    lambD = np.nanmax(lamb)-np.nanmin(lamb)
    lambfit = np.nanmin(lamb) +lambD*np.linspace(0, 1, nxi)
    phiD = np.nanmax(phi) - np.nanmin(phi)
    phifit = np.nanmin(phi) + phiD*np.linspace(0, 1, nxj)
    return lambfit, phifit


def _calc_spect1d_from_data2d(ldata, lamb, phi,
                              nlambfit=None, nphifit=None,
                              spect1d=None, mask=None,
                              vertsum1d=None):
    # Check / format inputs
    if spect1d is None:
        spect1d = 'mean'
    if isinstance(ldata, np.ndarray):
        ldata = [ldata]
    lc = [isinstance(spect1d, tuple) and len(spect1d) == 2,
          (isinstance(spect1d, list)
           and all([isinstance(ss, tuple) and len(ss) == 2
                    for ss in spect1d])),
          spect1d in ['mean', 'cent']]
    if lc[0]:
        spect1d = [spect1d]
    elif lc[1]:
        pass
    elif lc[2]:
        if spect1d == 'cent':
            spect1d = [(0., 0.2)]
            nspect = 1
    else:
        msg = ("spect1d must be either:\n"
               + "\t- 'mean': the avearge spectrum\n"
               + "\t- 'cent': the central spectrum +/- 20%\n"
               + "\t- (target, tol); a tuple of 2 floats:\n"
               + "\t\ttarget: the central value of the window in [-1,1]\n"
               + "\t\ttol:    the window tolerance (width) in [0,1]\n"
               + "\t- list of (target, tol)")
        raise Exception(msg)

    if not isinstance(nlambfit, int) or not isinstance(nphifit, int):
        msg = ("nlambfit and nphifit must be int!\n"
               + "\t- nlambfit provided: {}\n".format(nlambfit)
               + "\t- nphifit provided : {}\n".format(nphifit))
        raise Exception(msg)

    if vertsum1d is None:
        vertsum1d = True

    # Compute lambfit / phifit and spectrum1d
    if mask is not None:
        for ii in range(len(ldata)):
            ldata[ii][~mask] = np.nan
    lambfit, phifit = get_lambphifit(lamb, phi, nlambfit, nphifit)
    lambfitbins = 0.5*(lambfit[1:] + lambfit[:-1])
    ind = np.digitize(lamb, lambfitbins)

    # Get phi window
    if spect1d == 'mean':
        phiminmax = np.r_[phifit.min(), phifit.max()][None, :]
        spect1d_out = [np.array([np.nanmean(dd[ind == jj])
                                 for jj in np.unique(ind)])[None, :]
                       for dd in ldata]
    else:
        nspect = len(spect1d)
        dphi = np.nanmax(phifit) - np.nanmin(phifit)
        spect1d_out = [np.full((nspect, lambfit.size), np.nan)
                       for dd in ldata]
        phiminmax = np.full((nspect, 2), np.nan)
        for ii in range(nspect):
            phicent = np.nanmean(phifit) + spect1d[ii][0]*dphi/2.
            indphi = np.abs(phi - phicent) < spect1d[ii][1]*dphi
            for jj in np.unique(ind):
                indj = indphi & (ind == jj)
                if np.any(indj):
                    for ij in range(len(ldata)):
                        spect1d_out[ij][ii, jj] = np.nanmean(ldata[ij][indj])
            phiminmax[ii, :] = (np.nanmin(phi[indphi]),
                                np.nanmax(phi[indphi]))

    if vertsum1d is True:
        phifitbins = 0.5*(phifit[1:] + phifit[:-1])
        ind = np.digitize(phi, phifitbins)
        vertsum1d = [np.array([np.nanmean(dd[ind == ii])
                               for ii in np.unique(ind)])
                     for dd in ldata]
    if len(ldata) == 1:
        spect1d_out = spect1d_out[0]
        if vertsum1d is not False:
            vertsum1d = vertsum1d[0]
    return spect1d_out, lambfit, phifit, vertsum1d, phiminmax


# ###############################################
#           From plasma pts
# ###############################################


def calc_dthetapsiphi_from_lambpts(
    pts,
    bragg,
    center=None, rcurve=None,
    nout=None, e1=None, e2=None,
    extenthalf=None,
    ndtheta=None,
    grid=None,
):
    """ Return (dtheta, psi) of pts on crystal where bragg diffraction happens

    For given pts and lamb/bragg

    For each pts/lamb, there may be up to 2 arcs on the crystal
    Only returns valid solution (inside extenthalf), with nan elsewhere

    psi and dtheta returned as (nlamb, npts, 2, ndtheta) arrays

    """

    # Check input
    if ndtheta is None:
        ndtheta = 10

    npts = pts.shape[1]
    nlamb = bragg.size
    if grid is None:
        grid = True
    if grid is False:
        if nlamb != npts:
            msg = "If grid = False, lamb.shape should be (pts.shape[1],)"
            raise Exception(msg)

    # Prepare output
    if grid is True:
        scaPCem = np.full((nlamb, npts, 2), np.nan)
        dtheta = np.full((nlamb, npts, ndtheta, 2), np.nan)
        psi = np.full((nlamb, npts, ndtheta, 2), np.nan)
        num = np.full((nlamb, npts, ndtheta, 2), np.nan)
        angextra = np.full((nlamb, npts, ndtheta, 2), np.nan)
        dtheta_u = np.full((nlamb, npts, ndtheta), np.nan)
        psi_u = np.full((nlamb, npts, ndtheta), np.nan)
        sol1 = np.full((nlamb, npts), np.nan)
        sol2 = np.full((nlamb, npts), np.nan)
    else:
        scaPCem = np.full((npts, 2), np.nan)
        dtheta = np.full((npts, ndtheta, 2), np.nan)
        psi = np.full((npts, ndtheta, 2), np.nan)
        num = np.full((npts, ndtheta, 2), np.nan)
        angextra = np.full((npts, ndtheta, 2), np.nan)
        dtheta_u = np.full((npts, ndtheta), np.nan)
        psi_u = np.full((npts, ndtheta), np.nan)
        sol1 = np.full((npts,), np.nan)
        sol2 = np.full((npts,), np.nan)


    # Get to scalar product scaPCem
    PC = center[:, None] - pts
    PCnorm2 = np.sum(PC**2, axis=0)
    cos2 = np.cos(bragg)**2
    if grid is True:
        deltaon4 = np.sin(bragg)[:, None]**2*(
            PCnorm2[None, :] - rcurve**2*cos2[:, None]
        )
    else:
        deltaon4 = np.sin(bragg)**2 * (PCnorm2 - rcurve**2*cos2)

    # Get two relevant solutions
    ind = deltaon4 >= 0.
    if grid is True:
        cos2 = np.repeat(cos2[:, None], npts, axis=1)[ind]
        PCnorm = np.tile(np.sqrt(PCnorm2), (nlamb, 1))[ind]
    else:
        cos2 = cos2[ind]
        PCnorm = np.sqrt(PCnorm2)[ind]
    sol1 = -rcurve*cos2 - np.sqrt(deltaon4[ind])
    sol2 = -rcurve*cos2 + np.sqrt(deltaon4[ind])

    # Only keep solution going outward sphere
    # scaPMem = scaPCem + rcurve >= 0
    ind1 = (sol1 >= -rcurve)
    ind2 = (sol2 >= -rcurve)

    sol1 = sol1[ind1]
    sol2 = sol2[ind2]
    if grid is True:
        indn = ind.nonzero()
        ind1 = [indn[0][ind1], indn[1][ind1]]
        ind2 = [indn[0][ind2], indn[1][ind2]]
        scaPCem[ind1[0], ind1[1], 0] = sol1
        scaPCem[ind2[0], ind2[1], 1] = sol2
    else:
        indn = ind.nonzero()[0]
        scaPCem[indn[ind1], 0] = sol1
        scaPCem[indn[ind2], 1] = sol2
    ind = ~np.isnan(scaPCem)

    # Get equation on PCem
    # Xcos(dtheta)cos(psi) + Ycos(dtheta)sin(psi) + Zsin(dtheta) = scaPCem
    X = np.sum(PC*nout[:, None], axis=0)
    Y = np.sum(PC*e1[:, None], axis=0)
    Z = np.sum(PC*e2[:, None], axis=0)

    if grid is True:
        scaPCem = np.repeat(scaPCem[:, :, None, :], ndtheta, axis=2)
    else:
        scaPCem = np.repeat(scaPCem[:, None, :], ndtheta, axis=1)

    ind = ~np.isnan(scaPCem)
    if grid is True:
        XYnorm = np.repeat(
            np.repeat(
                np.repeat(np.sqrt(X**2 + Y**2)[None, :], nlamb, axis=0)[..., None],
                ndtheta,
                axis=-1,
            )[..., None],
            2,
            axis=-1,
        )[ind]
        Z = np.repeat(
            np.repeat(
                np.repeat(Z[None, :], nlamb, axis=0)[..., None],
                ndtheta, 
                axis=-1,
            )[..., None],
            2,
            axis=-1,
        )[ind]
        # Define angextra to get
        # sin(psi + angextra) = (scaPCem - Z*sin(theta)) / (XYnorm*cos(theta))
        angextra[ind] = np.repeat(
            np.repeat(
                np.repeat(np.arctan2(X, Y)[None, :], nlamb, axis=0)[..., None],
                ndtheta, axis=-1)[..., None],
            2, axis=-1)[ind]
        dtheta[ind] = np.repeat(
            np.repeat(
                np.repeat(
                    extenthalf[1]*np.linspace(-1, 1, ndtheta)[:, None],
                    2, axis=1)[None, ...],
                npts, axis=0)[None, ...],
            nlamb, axis=0)[ind]
    else:
        XYnorm = np.repeat(
            np.repeat(np.sqrt(X**2+Y**2)[:, None], ndtheta, axis=1)[..., None],
            2,
            axis=-1,
        )[ind]
        Z = np.repeat(
            np.repeat(Z[:, None], ndtheta, axis=1)[..., None],
            2,
            axis=-1,
        )[ind]
        angextra[ind] = np.repeat(
            np.repeat(np.arctan2(X, Y)[:, None], ndtheta, axis=-1)[..., None],
            2,
            axis=-1,
        )[ind]
        dtheta[ind] = np.repeat(
            np.repeat(
                extenthalf[1]*np.linspace(-1, 1, ndtheta)[:, None],
                2,
                axis=1,
            )[None, ...],
            npts,
            axis=0,
        )[ind]

    num[ind] = (
        (scaPCem[ind] - Z*np.sin(dtheta[ind])) / (XYnorm*np.cos(dtheta[ind]))
    )
    ind[ind] = np.abs(num[ind]) <= 1.
    psi[ind] = np.arcsin(num[ind]) - angextra[ind]
    ind[ind] = np.abs(psi[ind]) <= extenthalf[0]
    psi[~ind] = np.nan
    dtheta[~ind] = np.nan
    if np.any(np.sum(ind, axis=-1) == 2):
        msg = (
            "\nDouble solutions found for {} / {} points!".format(
                np.sum(np.sum(ind, axis=-1) == 2),
                np.prod(ind.shape[:-1]),
            )
        )
        warnings.warn(msg)
    return dtheta, psi, ind, grid
