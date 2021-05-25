

# Built-in
import itertools as itt

# Common
import numpy as np
from scipy.interpolate import BSpline
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import matplotlib.gridspec as gridspec
from matplotlib.axes._axes import Axes
from mpl_toolkits.mplot3d import Axes3D

# tofu
from tofu.version import __version__
from . import _def as _def

_GITHUB = 'https://github.com/ToFuProject/tofu/issues'
_WINTIT = 'tofu-%s        report issues / requests at %s'%(__version__, _GITHUB)

_QUIVERCOLOR = plt.cm.viridis(np.linspace(0, 1, 3))
_QUIVERCOLOR = np.array([[1., 0., 0., 1.],
                         [0., 1., 0., 1.],
                         [0., 0., 1., 1.]])
_QUIVERCOLOR = ListedColormap(_QUIVERCOLOR)


# Generic
def _check_projdax_mpl(dax=None, proj=None,
                       dmargin=None, fs=None, wintit=None):

    # ----------------------
    # Check inputs
    if proj is None:
        proj = 'all'
    assert isinstance(proj, str)
    proj = proj.lower()
    lproj = ['cross', 'hor', '3d']
    assert proj in lproj + ['all']
    if proj == 'all':
        proj = ['cross', 'hor']
    else:
        proj = [proj]

    # ----------------------
    # Check dax
    lc = [dax is None,
          issubclass(dax.__class__, Axes),
          isinstance(dax, dict),
          isinstance(dax, list)]
    assert any(lc)
    if lc[0]:
        dax = dict.fromkeys(proj)
    elif lc[1]:
        assert len(proj) == 1
        dax = {proj[0]: dax}
    elif lc[2]:
        lcax = [dax.get(pp) is None or issubclass(dax.get(pp).__class__, Axes)
                for pp in proj]
        if not all(lcax):
            msg = "Wrong key or axes in dax:\n"
            msg += "    - proj = %s"%str(proj)
            msg += "    - dax = %s"%str(dax)
            raise Exception(msg)
    else:
        assert len(dax) == 2
        assert all([ax is None or issubclass(ax.__class__, Axes)
                    for ax in dax])
        dax = {'cross': dax[0], 'hor': dax[1]}

    # Populate with default axes if necessary
    if 'cross' in proj and 'hor' in proj:
        if dax['cross'] is None:
            assert dax['hor'] is None
            lax = _def.Plot_LOSProj_DefAxes('all', fs=fs,
                                            dmargin=dmargin,
                                            wintit=wintit)
            dax['cross'], dax['hor'] = lax
    elif 'cross' in proj and dax['cross'] is None:
        dax['cross'] = _def.Plot_LOSProj_DefAxes('cross', fs=fs,
                                                 dmargin=dmargin,
                                                 wintit=wintit)
    elif 'hor' in proj and dax['hor'] is None:
        dax['hor'] = _def.Plot_LOSProj_DefAxes('hor', fs=fs,
                                               dmargin=dmargin,
                                               wintit=wintit)
    elif '3d' in proj  and dax['3d'] is None:
        dax['3d'] = _def.Plot_3D_plt_Tor_DefAxes(fs=fs,
                                                 dmargin=dmargin,
                                                 wintit=wintit)
    for kk in lproj:
        dax[kk] = dax.get(kk, None)
    return dax



# #################################################################
# #################################################################
#                   Generic geometry plot
# #################################################################
# #################################################################

def CrystalBragg_plot(cryst=None, dcryst=None,
                      det=None, ddet=None,
                      dax=None, proj=None, res=None, element=None,
                      color=None, dP=None,
                      pts0=None, pts1=None, rays_color=None, rays_npts=None,
                      dleg=None, draw=True, fs=None, dmargin=None,
                      use_non_parallelism=None,
                      wintit=None, tit=None):

    # ---------------------
    # Check / format inputs

    assert type(draw) is bool, "Arg draw must be a bool !"
    assert cryst is None or cryst.__class__.__name__ == 'CrystalBragg'
    if wintit is None:
        wintit = _WINTIT
    if dleg is None:
         dleg = _def.TorLegd

    # elements
    lelement = ['s', 'c', 'r', 'o', 'v']
    if element is None:
        element = 'oscrv'
    c0 = (isinstance(element, str)
          and all([ss in lelement for ss in element.lower()]))
    if not c0:
        msg = ("Arg element must be str contain some of the following:\n"
               + "\t- 'o': outline\n"
               + "\t- 'c': center (of curvature sphere)\n"
               + "\t- 's': summit (geometrical center of crystal piece)\n"
               + "\t- 'r': rowland circle (along e1 direction)\n"
               + "\t- 'v': local unit vectors\n"
               + "You provided:\n{}".format(element))
        raise Exception(msg)
    element = element.lower()

    # cryst
    if element != '' and cryst is None:
        msg = ("cryst cannot be None if element contains any of:\n"
               + "\t- {}\n".format(lelement)
               + "You provided: {}".format(element))
        raise Exception(msg)

    # vectors
    nout, e1, e2 = cryst.get_unit_vectors(
        use_non_parallelism=use_non_parallelism,
    )
    nin = -nout

    # outline
    outline = cryst.sample_outline_plot(
        res=res,
        use_non_parallelism=use_non_parallelism,
    )

    # det
    if det is None:
        det = False
    if det is not False and any([ss in element for ss in 'ocv']):
        c0 = (isinstance(det, dict)
              and 'cent' in det.keys())
        if c0 and 'o' in element:
            c0 = c0 and all([ss in det.keys()
                             for ss in ['outline', 'ei', 'ej']])
        if c0 and 'v' in element:
            c0 = c0 and all([ss in det.keys() for ss in ['nout', 'ei', 'ej']])
        if not c0:
            msg = ("Arg det must be a dict with keys:\n"
                   + "\t- 'cent': center of the detector\n"
                   + "\t- 'nout': outward unit vector (normal to surface)\n"
                   + "\t- 'ei': first local coordinate unit vector\n"
                   + "\t- 'ej': second coordinate unit vector\n"
                   + "\t- 'outline': 2d local coordinates of outline\n"
                   + "\tAll (except outline) are 3d cartesian coordinates\n"
                   + "You provided:\n{}".format(det))
            raise Exception(msg)

    # pts
    lc = [pts0 is None, pts1 is None]
    c0 = (np.sum(lc) == 1
          or (not any(lc)
              and (pts0.shape != pts1.shape or pts0.shape[0] != 3)))
    if c0:
        msg = ("pts0 and pts1 must be:\n"
               + "\t- both None\n"
               + "\t- both np.ndarray of same shape, with shape[0] == 3\n"
               + "  You provided:\n"
               + "\t- pts0: {}\n".format(pts0)
               + "\t- pts1: {}".format(pts1))
        raise Exception(msg)
    if pts0 is not None:
        if rays_color is None:
            rays_color = 'k'
        if rays_npts is None:
            rays_npts = 10

    # dict for plotting
    if color is None:
        color = False
    lkd = ['outline', 'cent', 'summit', 'rowland', 'vectors']
    # Avoid passing default by reference
    if dcryst is None:
        dcryst = dict({k0: dict(v0)
                       for k0, v0 in _def._CRYSTAL_PLOT_DDICT.items()})
    else:
        dcryst = dict({k0: dict(v0) for k0, v0 in dcryst.items()})

    for k0 in lkd:
        if dcryst.get(k0) is None:
            dcryst[k0] = dict(_def._CRYSTAL_PLOT_DDICT[k0])
        if dcryst[k0].get('color') is None:
            if cryst is not None and cryst._dmisc.get('color') is not None:
                dcryst[k0]['color'] = cryst._dmisc['color']
        if color is not False:
            dcryst[k0]['color'] = color
    if ddet is None:
        # Avoid passing default by reference
        ddet = dict({k0: dict(v0)
                     for k0, v0 in _def._DET_PLOT_DDICT.items()})
    else:
        ddet = dict({k0: dict(v0) for k0, v0 in ddet.items()})
    for k0 in lkd:
        if ddet.get(k0) is None:
            ddet[k0] = dict(_def._DET_PLOT_DDICT[k0])
        if color is not False:
            ddet[k0]['color'] = color

    # ---------------------
    # call plotting functions

    kwa = dict(fs=fs, wintit=wintit)
    if proj == '3d':
        # Temporary matplotlib issue
        dax = _CrystalBragg_plot_3d(
            cryst=cryst, dcryst=dcryst,
            det=det, ddet=ddet,
            nout=nout, nin=nin, e1=e1, e2=e2, outline=outline,
            proj=proj, res=res, dax=dax, element=element,
            pts0=pts0, pts1=pts1, rays_color=rays_color, rays_npts=rays_npts,
            draw=draw, dmargin=dmargin, fs=fs, wintit=wintit)
    else:
        dax = _CrystalBragg_plot_crosshor(
            cryst=cryst, dcryst=dcryst,
            det=det, ddet=ddet,
            nout=nout, nin=nin, e1=e1, e2=e2, outline=outline,
            proj=proj, res=res, dax=dax, element=element,
            pts0=pts0, pts1=pts1, rays_color=rays_color, rays_npts=rays_npts,
            draw=draw, dmargin=dmargin, fs=fs, wintit=wintit)

    # recompute the ax.dataLim
    ax0 = None
    for kk, vv in dax.items():
        if vv is None:
            continue
        dax[kk].relim()
        dax[kk].autoscale_view()
        if dleg is not False:
            dax[kk].legend(**dleg)
        ax0 = vv

    # set title
    if tit != False:
        ax0.figure.suptitle(tit)
    if draw:
        ax0.figure.canvas.draw()
    return dax


def _CrystalBragg_plot_crosshor(cryst=None, dcryst=None,
                                det=None, ddet=None,
                                nout=None, nin=None, e1=None, e2=None,
                                outline=None,
                                proj=None, dax=None,
                                element=None, res=None,
                                pts0=None, pts1=None,
                                rays_color=None, rays_npts=None,
                                quiver_cmap=None, draw=True,
                                dmargin=None, fs=None, wintit=None):

    # ---------------------
    # Check / format inputs

    if 'v' in element and quiver_cmap is None:
        quiver_cmap = _QUIVERCOLOR

    # ---------------------
    # Prepare axe and data

    dax = _check_projdax_mpl(dax=dax, proj=proj,
                             dmargin=dmargin, fs=fs, wintit=wintit)

    if 's' in element or 'v' in element:
        summ = cryst._dgeom['summit']
    if 'c' in element:
        cent = cryst._dgeom['center']
    if 'r' in element:
        ang = np.linspace(0, 2.*np.pi, 200)
        rr = 0.5*cryst._dgeom['rcurve']
        row = cryst._dgeom['summit'] + rr*nin
        row = (row[:, None]
               + rr*(np.cos(ang)[None, :]*nin[:, None]
                     + np.sin(ang)[None, :]*e1[:, None]))

    # ---------------------
    # plot
    cross = dax.get('cross') is not None
    hor = dax.get('hor') is not None

    if 'o' in element:
        if cross:
            dax['cross'].plot(
                np.hypot(outline[0,:], outline[1,:]),
                outline[2,:],
                label=cryst.Id.NameLTX+' outline',
                **dcryst['outline'],
            )
        if hor:
            dax['hor'].plot(outline[0,:], outline[1,:],
                            label=cryst.Id.NameLTX+' outline',
                            **dcryst['outline'])
    if 's' in element:
        if cross:
            dax['cross'].plot(np.hypot(summ[0], summ[1]), summ[2],
                              label=cryst.Id.NameLTX+" summit",
                              **dcryst['summit'])
        if hor:
            dax['hor'].plot(summ[0], summ[1],
                            label=cryst.Id.NameLTX+" summit",
                            **dcryst['summit'])
    if 'c' in element:
        if cross:
            dax['cross'].plot(np.hypot(cent[0], cent[1]), cent[2],
                              label=cryst.Id.NameLTX+" center",
                              **dcryst['cent'])
        if hor:
            dax['hor'].plot(cent[0], cent[1],
                            label=cryst.Id.NameLTX+" center",
                            **dcryst['cent'])
    if 'r' in element:
        if cross:
            dax['cross'].plot(np.hypot(row[0,:], row[1,:]), row[2,:],
                              label=cryst.Id.NameLTX+' rowland',
                              **dcryst['rowland'])
        if hor:
            dax['hor'].plot(row[0,:], row[1,:],
                            label=cryst.Id.NameLTX+' rowland',
                            **dcryst['rowland'])
    if 'v' in element:
        p0 = np.repeat(summ[:,None], 3, axis=1)
        v = np.concatenate((nout[:, None], e1[:, None], e2[:, None]), axis=1)
        if cross:
            pr = np.hypot(p0[0, :], p0[1, :])
            vr = np.hypot(p0[0, :]+v[0, :], p0[1, :]+v[1, :]) - pr
            dax['cross'].quiver(pr, p0[2, :],
                                vr, v[2, :],
                                np.r_[0., 0.5, 1.], cmap=quiver_cmap,
                                angles='xy', scale_units='xy',
                                label=cryst.Id.NameLTX+" unit vect",
                                **dcryst['vectors'])
        if hor:
            dax['hor'].quiver(p0[0, :], p0[1, :],
                              v[0, :], v[1, :],
                              np.r_[0., 0.5, 1.], cmap=quiver_cmap,
                              angles='xy', scale_units='xy',
                              label=cryst.Id.NameLTX+" unit vect",
                              **dcryst['vectors'])

    # -------------
    # Detector
    if det is not False:
        if det.get('cent') is not None and 'c' in element:
            if cross:
                dax['cross'].plot(np.hypot(det['cent'][0], det['cent'][1]),
                                  det['cent'][2],
                                  label="det_cent",
                                  **ddet['cent'])
            if hor:
                dax['hor'].plot(det['cent'][0], det['cent'][1],
                                label="det_cent",
                                **ddet['cent'])

        if det.get('nout') is not None and 'v' in element:
            assert det.get('ei') is not None and det.get('ej') is not None
            p0 = np.repeat(det['cent'][:, None], 3, axis=1)
            v = np.concatenate((det['nout'][:, None], det['ei'][:, None],
                                det['ej'][:, None]), axis=1)
            if cross:
                pr = np.hypot(p0[0, :], p0[1, :])
                vr = np.hypot(p0[0, :]+v[0, :], p0[1, :]+v[1, :]) - pr
                dax['cross'].quiver(pr, p0[2, :],
                                    vr, v[2, :],
                                    np.r_[0., 0.5, 1.], cmap=quiver_cmap,
                                    angles='xy', scale_units='xy',
                                    label="det unit vect",
                                    **ddet['vectors'])
            if hor:
                dax['hor'].quiver(p0[0, :], p0[1, :],
                                  v[0, :], v[1, :],
                                  np.r_[0., 0.5, 1.], cmap=quiver_cmap,
                                  angles='xy', scale_units='xy',
                                  label="det unit vect",
                                  **ddet['vectors'])

        if det.get('outline') is not None and 'o' in element:
            det_out = (det['outline'][0:1, :]*det['ei'][:, None]
                        + det['outline'][1:2, :]*det['ej'][:, None]
                       + det['cent'][:, None])
            if cross:
                dax['cross'].plot(np.hypot(det_out[0, :], det_out[1, :]),
                                  det_out[2, :],
                                  label='det outline',
                                  **ddet['outline'])
            if hor:
                dax['hor'].plot(det_out[0, :],
                                det_out[1, :],
                                label='det outline',
                                **ddet['outline'])

    # -------------
    # pts0 and pts1
    if pts0 is not None:
        if pts0.ndim == 3:
            pts0 = np.reshape(pts0, (3, pts0.shape[1]*pts0.shape[2]))
            pts1 = np.reshape(pts1, (3, pts1.shape[1]*pts1.shape[2]))
        if cross:
            k = np.r_[np.linspace(0, 1, rays_npts), np.nan]
            pts01 = np.reshape((pts0[:, :, None]
                                + k[None, None, :]*(pts1-pts0)[:, :, None]),
                               (3, pts0.shape[1]*(rays_npts+1)))
            linesr = np.hypot(pts01[0, :], pts01[1, :])
            dax['cross'].plot(linesr, pts01[2, :],
                              color=rays_color, lw=1., ls='-')
        if hor:
            k = np.r_[0, 1, np.nan]
            pts01 = np.reshape((pts0[:2, :, None]
                                + k[None, None, :]*(pts1-pts0)[:2, :, None]),
                               (2, pts0.shape[1]*3))
            dax['hor'].plot(pts01[0, :], pts01[1, :],
                            color=rays_color, lw=1., ls='-')
    return dax


def _CrystalBragg_plot_3d(cryst=None, dcryst=None,
                          det=None, ddet=None,
                          nout=None, nin=None, e1=None, e2=None,
                          outline=None,
                          proj=None, dax=None,
                          element=None, res=None,
                          pts0=None, pts1=None,
                          rays_color=None, rays_npts=None,
                          quiver_cmap=None, draw=True,
                          dmargin=None, fs=None, wintit=None):

    # ---------------------
    # Check / format inputs

    if 'v' in element and quiver_cmap is None:
        quiver_cmap = _QUIVERCOLOR

    # ---------------------
    # Prepare axe and data

    dax = _check_projdax_mpl(dax=dax, proj=proj,
                             dmargin=dmargin, fs=fs, wintit=wintit)

    if 's' in element or 'v' in element:
        summ = cryst._dgeom['summit']
    if 'c' in element:
        cent = cryst._dgeom['summit'] + cryst._dgeom['rcurve']*nin
        # cryst._dgeom['center']
    if 'r' in element:
        ang = np.linspace(0, 2.*np.pi, 200)
        rr = 0.5*cryst._dgeom['rcurve']
        row = cryst._dgeom['summit'] + rr*nin
        row = (row[:, None]
               + rr*(np.cos(ang)[None, :]*nin[:, None]
                     + np.sin(ang)[None, :]*e1[:, None]))

    # ---------------------
    # plot

    if 'o' in element:
        if dax['3d'] is not None:
            dax['3d'].plot(outline[0, :], outline[1, :], outline[2, :],
                           label=cryst.Id.NameLTX+' outline',
                           **dcryst['outline'])
    if 's' in element:
        if dax['3d'] is not None:
            dax['3d'].plot(summ[0:1], summ[1:2], summ[2:3],
                           label=cryst.Id.NameLTX+" summit",
                           **dcryst['summit'])
    if 'c' in element:
        if dax['3d'] is not None:
            dax['3d'].plot(cent[0:1], cent[1:2], cent[2:3],
                           label=cryst.Id.NameLTX+" center",
                           **dcryst['cent'])
    if 'r' in element:
        if dax['3d'] is not None:
            dax['3d'].plot(row[0, :], row[1, :], row[2, :],
                           label=cryst.Id.NameLTX+' rowland',
                           **dcryst['rowland'])
    if 'v' in element:
        p0 = np.repeat(summ[:, None], 3, axis=1)
        v = np.concatenate((nout[:, None], e1[:, None], e2[:, None]), axis=1)
        if dax['3d'] is not None:
            dax['3d'].quiver(
                p0[0, :], p0[1, :], p0[2, :],
                v[0, :], v[1, :], v[2, :],
                np.r_[0., 0.5, 1.],
                length=0.1,
                normalize=True,
                cmap=quiver_cmap,
                label=cryst.Id.NameLTX+" unit vect",
                **dcryst['vectors'],
            )
             #, **Vdict)
            # angles='xy', scale_units='xy',

    # -------------
    # Detector
    if det is not False:
        if det.get('cent') is not None and 'c' in element:
            if dax['3d'] is not None:
                dax['3d'].plot(det['cent'][0:1],
                               det['cent'][1:2],
                               det['cent'][2:3],
                               label="det_cent",
                               **ddet['cent'])

        if det.get('nout') is not None and 'v' in element:
            p0 = np.repeat(det['cent'][:, None], 3, axis=1)
            v = np.concatenate((det['nout'][:, None], det['ei'][:, None],
                                det['ej'][:, None]), axis=1)
            if dax['3d'] is not None:
                dax['3d'].quiver(
                    p0[0, :], p0[1, :], p0[2, :],
                    v[0, :], v[1, :], v[2, :],
                    np.r_[0., 0.5, 1.],
                    length=0.1,
                    normalize=True,
                    cmap=quiver_cmap,
                    label="det unit vect",
                    **ddet['vectors'],
                )
                #, **Vdict)
                # angles='xy', scale_units='xy',
        if det.get('outline') is not None and 'o' in element:
            det_out = (det['outline'][0:1, :]*det['ei'][:, None]
                       + det['outline'][1:2, :]*det['ej'][:, None]
                       + det['cent'][:, None])
            if dax['3d'] is not None:
                dax['3d'].plot(det_out[0, :],
                               det_out[1, :],
                               det_out[2, :],
                               label='det outline',
                               **ddet['outline'])

    # -------------
    # pts0 and pts1
    if pts0 is not None:
        if pts0.ndim == 3:
            pts0 = np.reshape(pts0, (3, pts0.shape[1]*pts0.shape[2]))
            pts1 = np.reshape(pts1, (3, pts1.shape[1]*pts1.shape[2]))
        if dax['3d'] is not None:
            k = np.r_[0, 1, np.nan]
            pts01 = np.reshape((pts0[:, :, None]
                                + k[None, None, :]*(pts1-pts0)[:, :, None]),
                               (3, pts0.shape[1]*3))
            dax['3d'].plot(pts01[0, :], pts01[1, :], pts01[2, :],
                           color=rays_color, lw=1., ls='-')
    return dax


# #################################################################
# #################################################################
#                   Rocking curve plot
# #################################################################
# #################################################################

def CrystalBragg_plot_rockingcurve(func=None, bragg=None, lamb=None,
                                   sigma=None, npts=None,
                                   ang_units=None, axtit=None,
                                   color=None,
                                   legend=None, fs=None, ax=None):

    # Prepare
    if legend is None:
        legend = True
    if color is None:
        color = 'k'
    if ang_units is None:
        ang_units = 'deg'
    if axtit is None:
        axtit = 'Rocking curve'
    if sigma is None:
        sigma = 0.005*np.pi/180.
    if npts is None:
        npts = 1000
    angle = bragg + 3.*sigma*np.linspace(-1, 1, npts)
    curve = func(angle)
    lab = r"$\lambda = {:9.6} A$".format(lamb*1.e10)
    if ang_units == 'deg':
        angle = angle*180/np.pi
        bragg = bragg*180/np.pi

    # Plot
    if ax is None:
        if fs is None:
            fs = (8, 6)
        fig = plt.figure(figsize=fs)
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        ax.set_title(axtit, size=12)
        ax.set_xlabel('angle ({})'.format(ang_units))
        ax.set_ylabel('reflectivity (adim.)')
    ax.plot(angle, curve, ls='-', lw=1., c=color, label=lab)
    ax.axvline(bragg, ls='--', lw=1, c=color)
    if legend is not False:
        ax.legend()
    return ax


# #################################################################
# #################################################################
#                   Bragg diffraction plot
# #################################################################
# #################################################################

# Deprecated ? re-use ?
def CrystalBragg_plot_approx_detector_params(Rrow, bragg, d, Z,
                                             frame_cent, nn):

    R = 2.*Rrow
    L = 2.*R
    ang = np.linspace(0., 2.*np.pi, 100)

    fig = plt.figure()
    ax = fig.add_axes([0.1,0.1,0.8,0.8], aspect='equal')

    ax.axvline(0, ls='--', c='k')
    ax.plot(Rrow*np.cos(ang), Rrow + Rrow*np.sin(ang), c='r')
    ax.plot(R*np.cos(ang), R + R*np.sin(ang), c='b')
    ax.plot(L*np.cos(bragg)*np.r_[-1,0,1],
            L*np.sin(bragg)*np.r_[1,0,1], c='k')
    ax.plot([0, d*np.cos(bragg)], [Rrow, d*np.sin(bragg)], c='r')
    ax.plot([0, d*np.cos(bragg)], [Z, d*np.sin(bragg)], 'g')
    ax.plot([0, L/10*nn[1]], [Z, Z+L/10*nn[2]], c='g')
    ax.plot(frame_cent[1]*np.cos(2*bragg-np.pi),
            Z + frame_cent[1]*np.sin(2*bragg-np.pi), c='k', marker='o', ms=10)

    ax.set_xlabel(r'y')
    ax.set_ylabel(r'z')
    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1.), frameon=False)
    return ax


def CrystalBragg_plot_xixj_from_braggangle(bragg=None, xi=None, xj=None,
                                           data=None, ax=None):
    if ax is None:
        fig = plt.figure()
        ax = fig.add_axes([0.1,0.1,0.8,0.8], aspect='equal')

    for ii in range(len(bragg)):
        deg ='{0:07.3f}'.format(bragg[ii]*180/np.pi)
        ax.plot(xi[:,ii], xj[:,ii], '.', label='bragg %s'%deg)

    ax.set_xlabel(r'xi')
    ax.set_ylabel(r'yi')
    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1.), frameon=False)
    return ax




def CrystalBragg_plot_braggangle_from_xixj(xi=None, xj=None,
                                           bragg=None, angle=None,
                                           ax=None, plot=None,
                                           braggunits='rad', angunits='rad',
                                           leg=None, colorbar=None,
                                           fs=None, wintit=None,
                                           tit=None, **kwdargs):

    # Check inputs
    if isinstance(plot, bool):
        plot = 'contour'
    if fs is None:
        fs = (6, 6)
    if wintit is None:
        wintit = _WINTIT
    if tit is None:
        tit = False
    if colorbar is None:
        colorbar = True
    if leg is None:
        leg = False
    if leg is True:
        leg = {}


    # Prepare axes
    if ax is None:
        fig = plt.figure(figsize=fs)
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8],
                          aspect='equal', adjustable='box')
    dobj = {'phi': {'ax': ax}, 'bragg': {'ax': ax}}
    dobj['bragg']['kwdargs'] = dict(kwdargs)
    dobj['phi']['kwdargs'] = dict(kwdargs)
    dobj['phi']['kwdargs']['cmap'] = plt.cm.seismic

    # Clear cmap if colors provided
    if 'colors' in kwdargs.keys():
        if 'cmap' in dobj['bragg']['kwdargs'].keys():
            del dobj['bragg']['kwdargs']['cmap']
        if 'cmap' in dobj['phi']['kwdargs'].keys():
            del dobj['phi']['kwdargs']['cmap']

    # Plot
    if plot == 'contour':
        if 'levels' in kwdargs.keys():
            lvls = kwdargs['levels']
            del kwdargs['levels']
            obj0 = dobj['bragg']['ax'].contour(xi, xj, bragg, lvls,
                                               **dobj['bragg']['kwdargs'])
            obj1 = dobj['phi']['ax'].contour(xi, xj, angle, lvls,
                                             **dobj['phi']['kwdargs'])
        else:
            obj0 = dobj['bragg']['ax'].contour(xi, xj, bragg,
                                               **dobj['bragg']['kwdargs'])
            obj1 = dobj['phi']['ax'].contour(xi, xj, angle,
                                             **dobj['phi']['kwdargs'])
    elif plot == 'imshow':
        extent = (xi.min(), xi.max(), xj.min(), xj.max())
        obj0 = dobj['bragg']['ax'].imshow(bragg, extent=extent, aspect='equal',
                                          adjustable='datalim',
                                          **dobj['bragg']['kwdargs'])
        obj1 = dobj['phi']['ax'].imshow(angle, extent=extent, aspect='equal',
                                        adjustable='datalim',
                                        **dobj['phi']['kwdargs'])
    elif plot == 'pcolor':
        obj0 = dobj['bragg']['ax'].pcolor(xi, xj, bragg,
                                          **dobj['bragg']['kwdargs'])
        obj1 = dobj['phi']['ax'].pcolor(xi, xj, angle,
                                        **dobj['phi']['kwdargs'])
    dobj['bragg']['obj'] = obj0
    dobj['phi']['obj'] = obj1

    # Post polish
    for k0 in set(dobj.keys()):
        dobj[k0]['ax'].set_xlabel(r'xi (m)')
        dobj[k0]['ax'].set_ylabel(r'xj (m)')

    if colorbar is True:
        cax0 = plt.colorbar(dobj['bragg']['obj'], ax=dobj['bragg']['ax'])
        cax1 = plt.colorbar(dobj['phi']['obj'], ax=dobj['phi']['ax'])
        cax0.ax.set_title(r'$\theta_{bragg}$' + '\n' + r'($%s$)'%braggunits)
        cax1.ax.set_title(r'$ang$' + '\n' + r'($%s$)'%angunits)

    if leg is not False:
        ax.legend(**leg)
    if wintit is not False:
        ax.figure.canvas.set_window_title(wintit)
    if tit is not False:
        ax.figure.suptitle(tit, size=10, weight='bold', ha='right')
    return ax


def CrystalBragg_plot_line_tracing_on_det(lamb, xi, xj, xi_err, xj_err,
                                          det=None,
                                          johann=None, rocking=None,
                                          fs=None, dmargin=None,
                                          wintit=None, tit=None):

    # Check inputs
    # ------------

    if fs is None:
        fs = (6, 8)
    if dmargin is None:
        dmargin = {'left': 0.05, 'right': 0.99,
                   'bottom': 0.06, 'top': 0.92,
                   'wspace': None, 'hspace': 0.4}

    if wintit is None:
        wintit = _WINTIT
    if tit is None:
        tit = "line tracing"
        if johann is True:
            tit += " - johann error"
        if rocking is True:
            tit += " - rocking curve"

    plot_err = johann is True or rocking is True

    # Plot
    # ------------

    fig = plt.figure(figsize=fs)
    gs = gridspec.GridSpec(1, 1, **dmargin)
    ax0 = fig.add_subplot(gs[0, 0], aspect='equal', adjustable='datalim')

    if det.get('outline') is not None:
        ax0.plot(
            det['outline'][0, :], det['outline'][1, :],
            ls='-', lw=1., c='k',
        )
    for l in range(lamb.size):
        lab = r'$\lambda$'+' = {:6.3f} A'.format(lamb[l]*1.e10)
        l0, = ax0.plot(xi[l, :], xj[l, :], ls='-', lw=1., label=lab)
        if plot_err:
            ax0.plot(xi_err[l, ...], xj_err[l, ...],
                     ls='None', lw=1., c=l0.get_color(),
                     marker='.', ms=4)

    ax0.legend()

    if wintit is not False:
        fig.canvas.set_window_title(wintit)
    if tit is not False:
        fig.suptitle(tit, size=14, weight='bold')
    return [ax0]


def CrystalBragg_plot_johannerror(
                xi, xj, lamb, phi, err_lamb, err_phi,
                cmap=None, vmin=None, vmax=None,
                fs=None, dmargin=None, wintit=None, tit=None,
                angunits='deg', err=None,
                                  ):

    # Check inputs
    # ------------

    if fs is None:
        fs = (14, 8)
    if cmap is None:
        cmap = plt.cm.viridis
    if dmargin is None:
        dmargin = {'left': 0.05, 'right': 0.99,
                   'bottom': 0.06, 'top': 0.92,
                   'wspace': None, 'hspace': 0.4}
    assert angunits in ['deg', 'rad']
    if angunits == 'deg':
        # bragg = bragg*180./np.pi
        phi = phi*180./np.pi
        err_phi = err_phi*180./np.pi

    if err is None:
        err = 'abs'
    if err == 'rel':
        err_lamb = 100.*err_lamb / (np.nanmax(lamb) - np.nanmin(lamb))
        err_phi = 100.*err_phi / (np.nanmax(phi) - np.nanmin(phi))
        err_lamb_units = '%'
        err_phi_units = '%'
    else:
        err_lamb_units = 'm'
        err_phi_units = angunits

    if wintit is None:
        wintit = _WINTIT
    if tit is None:
        tit = False

    # pre-compute
    # ------------

    # extent
    extent = (xi.min(), xi.max(), xj.min(), xj.max())

    # Plot
    # ------------

    fig = plt.figure(figsize=fs)
    gs = gridspec.GridSpec(1, 3, **dmargin)
    ax0 = fig.add_subplot(gs[0, 0], aspect='equal') # adjustable='datalim')
    ax1 = fig.add_subplot(gs[0, 1], aspect='equal', # adjustable='datalim',
                          sharex=ax0, sharey=ax0)
    ax2 = fig.add_subplot(gs[0, 2], aspect='equal', # adjustable='datalim',
                          sharex=ax0, sharey=ax0)

    ax0.set_title('Iso-lamb and iso-phi at crystal summit')
    ax1.set_title('Focalization error on lamb ({})'.format(err_lamb_units))
    ax2.set_title('Focalization error on phi ({})'.format(err_phi_units))

    ax0.contour(xi, xj, lamb.T, 10, cmap=cmap)
    ax0.contour(xi, xj, phi.T, 10, cmap=cmap, ls='--')
    imlamb = ax1.imshow(err_lamb, extent=extent, aspect='equal',
                        origin='lower', interpolation='nearest',
                        vmin=vmin, vmax=vmax)
    imphi = ax2.imshow(err_phi, extent=extent, aspect='equal',
                       origin='lower', interpolation='nearest',
                       vmin=vmin, vmax=vmax)

    plt.colorbar(imlamb, ax=ax1)
    plt.colorbar(imphi, ax=ax2)
    if wintit is not False:
        fig.canvas.set_window_title(wintit)
    if tit is not False:
        fig.suptitle(tit, size=14, weight='bold')

    return [ax0, ax1, ax2]


# #################################################################
# #################################################################
#                   Ray tracing plot
# #################################################################
# #################################################################

def CrystalBragg_plot_raytracing_from_lambpts(xi=None, xj=None, lamb=None,
                                              xi_bounds=None, xj_bounds=None,
                                              pts=None, ptscryst=None,
                                              ptsdet=None,
                                              det_cent=None, det_nout=None,
                                              det_ei=None, det_ej=None,
                                              cryst=None, proj=None,
                                              fs=None, ax=None, dmargin=None,
                                              wintit=None, tit=None,
                                              legend=None, draw=None):
    # Check
    assert xi.shape == xj.shape and xi.ndim == 3
    assert (isinstance(proj, list)
            and all([pp in ['det', '2d', '3d'] for pp in proj]))
    if legend is None or legend is True:
        legend = dict(bbox_to_anchor=(1.02, 1.), loc='upper left',
                      ncol=1, mode="expand", borderaxespad=0.,
                      prop={'size': 6})
    if wintit is None:
        wintit = _WINTIT
    if draw is None:
        draw = True

    # Prepare
    nlamb, npts, ndtheta = xi.shape
    det = np.array([[xi_bounds[0], xi_bounds[1], xi_bounds[1],
                     xi_bounds[0], xi_bounds[0]],
                    [xj_bounds[0], xj_bounds[0], xj_bounds[1],
                     xj_bounds[1], xj_bounds[0]]])
    lcol = ['r', 'g', 'b', 'm', 'y', 'c']
    lm = ['+', 'o', 'x', 's']
    lls = ['-', '--', ':', '-.']
    ncol, nm, nls = len(lcol), len(lm), len(lls)

    if '2d' in proj or '3d' in proj:
        pts = np.repeat(np.repeat(pts[:, None, :], nlamb, axis=1)[..., None],
                        ndtheta, axis=-1)[..., None]
        ptsall = np.concatenate((pts,
                                 ptscryst[..., None],
                                 ptsdet[..., None],
                                 np.full((3, nlamb, npts, ndtheta, 1), np.nan)),
                                axis=-1).reshape((3, nlamb, npts, ndtheta*4))
        del pts, ptscryst, ptsdet
        if '2d' in proj:
            R = np.hypot(ptsall[0, ...], ptsall[1, ...])

    # --------
    # Plot
    lax = []
    if 'det' in proj:

        # Prepare
        if ax is None:
            if fs is None:
                fsi = (8, 6)
            else:
                fsi = fs
            if dmargin is None:
                dmargini = {'left': 0.1, 'right': 0.8,
                            'bottom': 0.1, 'top': 0.9,
                            'wspace': None, 'hspace': 0.4}
            else:
                dmargini = dmargin
            if tit is None:
                titi = False
            else:
                titi = tit
            fig = plt.figure(figsize=fsi)
            gs = gridspec.GridSpec(1, 1, **dmargini)
            axi = fig.add_subplot(gs[0, 0], aspect='equal', adjustable='datalim')
            axi.set_xlabel(r'$x_i$ (m)')
            axi.set_ylabel(r'$x_j$ (m)')
        else:
            axi = ax

        # plot
        axi.plot(det[0, :], det[1, :], ls='-', lw=1., c='k')
        for pp in range(npts):
            for ll in range(nlamb):
                lab = (r'pts {} - '.format(pp)
                       + '$\lambda$'+' = {:6.3f} A'.format(lamb[ll]*1.e10))
                axi.plot(xi[ll, pp, :], xj[ll, pp, :],
                         ls='None', marker=lm[ll%nm], c=lcol[pp%ncol], label=lab)

        # decorate
        if legend is not False:
            axi.legend(**legend)
        if wintit is not False:
            axi.figure.canvas.set_window_title(wintit)
        if titi is not False:
            axi.figure.suptitle(titi, size=14, weight='bold')
        if draw:
            axi.figure.canvas.draw()
        lax.append(axi)

    if '2d' in proj:

        # Prepare
        if tit is None:
            titi = False
        else:
            titi = tit

        # plot
        dax = cryst.plot(lax=ax, proj='all',
                         det_cent=det_cent, det_nout=det_nout,
                         det_ei=det_ei, det_ej=det_ej, draw=False)
        for pp in range(npts):
            for ll in range(nlamb):
                lab = (r'pts {} - '.format(pp)
                       + '$\lambda$'+' = {:6.3f} A'.format(lamb[ll]*1.e10))
                dax['cross'].plot(R[ll, pp, :], ptsall[2, ll, pp, :],
                                  ls=lls[ll%nls], color=lcol[pp%ncol],
                                  label=lab)
                dax['hor'].plot(ptsall[0, ll, pp, :], ptsall[1, ll, pp, :],
                                ls=lls[ll%nls], color=lcol[pp%ncol], label=lab)
        # decorate
        if legend is not False:
            dax['cross'].legend(**legend)
        if wintit is not False:
            dax['cross'].figure.canvas.set_window_title(wintit)
        if titi is not False:
            dax['cross'].figure.suptitle(titi, size=14, weight='bold')
        if draw:
            dax['cross'].figure.canvas.draw()
        lax.append(dax['cross'])
        lax.append(dax['hor'])

    return lax
