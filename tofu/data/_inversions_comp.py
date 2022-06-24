# -*- coding: utf-8 -*-


# Built-in
import time


# Common
import numpy as np
import scipy.sparse as scpsp


# tofu
from . import _generic_check
from . import _inversions_checks
from . import _inversions_algos
tomotok2tofu = _inversions_checks.tomotok2tofu


__all__ = ['get_available_inversions_algo']


# #############################################################################
# #############################################################################
#                           main
# #############################################################################


def compute_inversions(
    # resources
    coll=None,
    # inversion name
    key=None,
    # input data
    key_matrix=None,
    key_data=None,
    key_sigma=None,
    sigma=None,
    # constraints
    dconstraints=None,
    # regularity operator
    operator=None,
    geometry=None,
    # choice of algo
    algo=None,
    # misc
    solver=None,
    conv_crit=None,
    chain=None,
    verb=None,
    store=None,
    # algo and solver-specific options
    kwdargs=None,
    method=None,
    options=None,
):

    # -------------
    # check inputs

    (
        key_matrix, key_data, key_sigma, keybs, keym,
        data, sigma, matrix, t,
        m3d, indok,
        dconstraints,
        opmat, operator, geometry,
        dalgo, dconstraints, dcon,
        conv_crit, crop, chain, kwdargs, method, options,
        solver, verb, store,
        keyinv, refinv, reft, notime,
    ) = _inversions_checks._compute_check(
        # resources
        coll=coll,
        # inversion name
        key=key,
        # input data
        key_matrix=key_matrix,
        key_data=key_data,
        key_sigma=key_sigma,
        sigma=sigma,
        # constraints
        dconstraints=dconstraints,
        # choice of algo
        algo=algo,
        # regularity operator
        solver=solver,
        operator=operator,
        geometry=geometry,
        # misc
        conv_crit=conv_crit,
        chain=chain,
        verb=verb,
        store=store,
        # algo and solver-specific options
        kwdargs=kwdargs,
        method=method,
        options=options,
    )

    nt, nchan = data.shape
    nbs = matrix.shape[-1]

    # -------------
    # get func

    if isinstance(dalgo['func'], str):
        if dalgo['source'] == 'tofu':
            dalgo['func'] = getattr(_inversions_algos, dalgo['func'])
        elif dalgo['source'] == 'tomotok':
            dalgo['func'] = getattr(tomotok2tofu, dalgo['func'])

    # -------------
    # prepare data

    if verb >= 1:
        # t0 = time.process_time()
        t0 = time.perf_counter()
        print("Preparing data... ", end='', flush=True)

    # indt (later)

    # normalization
    data_n = (data / sigma)
    mu0 = 1.

    # Define Regularization operator
    if dalgo['family'] == 'Non-regularized':
        R = None
    else:
        if dalgo['source'] == 'tomotok' and dalgo['reg_operator'] == 'MinFisher':
            R = opmat
        elif operator == 'D0N2':
            R = opmat[0]
        elif operator == 'D1N2':
            R = opmat[0] + opmat[1]
        elif operator == 'D2N2':
            R = opmat[0] + opmat[1]
        else:
            msg = 'unknown operator!'
            raise Exception(msg)

    # prepare computation intermediates
    precond = None
    Tyn = np.full((nbs,), np.nan)
    mat0 = matrix[0, ...] if m3d else matrix
    if dalgo['sparse'] is True:
        Tn = scpsp.diags(1./np.nanmean(sigma, axis=0)).dot(mat0)
        TTn = Tn.T.dot(Tn)
        if solver != 'spsolve':
            # preconditioner to approx inv(TTn + reg*Rn)
            # should improves convergence, but actually slower...
            # precond = scpsp.linalg.inv(TTn + mu0*R)
            pass

    else:
        Tn = mat0 / np.nanmean(sigma, axis=0)[:, None]
        TTn = Tn.T.dot(Tn)

    # prepare output arrays
    sol = np.full((nt, nbs), np.nan)
    mu = np.full((nt,), np.nan)
    chi2n = np.full((nt,), np.nan)
    regularity = np.full((nt,), np.nan)
    niter = np.zeros((nt,), dtype=int)
    spec = [None for ii in range(nt)]

    # -------------
    # initial guess

    if indok is None:
        sol0 = np.full((nbs,), np.mean(data[0, :]) / mat0.mean())
    else:
        sol0 = np.full((nbs,), np.mean(data[0, indok[0, :]]) / mat0.mean())

    if verb >= 1:
        # t1 = time.process_time()
        t1 = time.perf_counter()
        print(f"{t1-t0} s", end='\n', flush=True)
        print("Setting inital guess... ", end='', flush=True)

    # -------------
    # compute

    if verb >= 1:
        # t2 = time.process_time()
        t2 = time.perf_counter()
        print(f"{t2-t1} s", end='\n', flush=True)
        print("Starting time loop...", end='\n', flush=True)

    if dalgo['source'] == 'tofu':
        out = _compute_inv_loop(
            sol0=sol0,
            mu0=mu0,
            matrix=matrix,
            Tn=Tn,              # normalized geometry matrix (T)
            TTn=TTn,            # normalized tTT
            Tyn=Tyn,            # normalized
            R=R,                # Regularity operator
            precond=precond,
            data_n=data_n,      # normalized data
            sigma=sigma,
            indok=indok,
            # parameters
            m3d=m3d,
            dalgo=dalgo,
            isotropic=dalgo['isotropic'],
            conv_crit=conv_crit,
            sparse=dalgo['sparse'],
            positive=dalgo['positive'],
            chain=chain,
            verb=verb,
            kwdargs=kwdargs,
            method=method,
            options=options,
            dcon=dcon,
            # output
            sol=sol,
            mu=mu,
            chi2n=chi2n,
            regularity=regularity,
            niter=niter,
            spec=spec,
        )

    elif dalgo['source'] == 'tomotok':
        out = _compute_inv_loop_tomotok(
            sol0=sol0,
            mu0=mu0,
            matrix=matrix,
            Tn=Tn,
            TTn=TTn,
            Tyn=Tyn,
            R=R,
            precond=precond,
            data_n=data_n,
            sigma=sigma,
            indok=indok,
            # parameters
            m3d=m3d,
            dalgo=dalgo,
            isotropic=dalgo['isotropic'],
            conv_crit=conv_crit,
            sparse=dalgo['sparse'],
            positive=dalgo['positive'],
            chain=chain,
            verb=verb,
            kwdargs=kwdargs,
            method=method,
            options=options,
            # output
            sol=sol,
            mu=mu,
            chi2n=chi2n,
            regularity=regularity,
            niter=niter,
            spec=spec,
        )

    if verb >= 1:
        # t3 = time.process_time()
        t3 = time.perf_counter()
        print(f"{t3-t2} s", end='\n', flush=True)
        print("Post-formatting results...", end='\n', flush=True)

    # -------------
    # format output

    # reshape solution
    if crop is True:
        shapebs = coll.dobj['bsplines'][keybs]['shape']
        shapesol = tuple(np.r_[nt, shapebs])
        sol_full = np.zeros(shapesol, dtype=float)
        cropbs = coll.ddata[coll.dobj['bsplines'][keybs]['crop']]['data']
        cropbsflat = cropbs.ravel(order='F')
        iR = np.tile(np.arange(0, shapebs[0]), shapebs[1])[cropbsflat]
        iZ = np.repeat(np.arange(0, shapebs[1]), shapebs[0])[cropbsflat]
        sol_full[:, iR, iZ] = sol
    else:
        sol_full = sol

    # -------------
    # store

    if store is True:

        # reshape if unique time step
        if notime:
            assert sol_full.shape[0] == 1
            sol_full = sol_full[0, ...]

        # dict
        ddata = {
            keyinv: {
                'data': sol_full,
                'ref': refinv,
            },
        }

        dref = None
        if notime is False:
            if isinstance(t, np.ndarray):
                dref = {
                    reft: {'size': nt},
                }
                ddata.update({
                    f'{keyinv}-t': {
                        'data': t,
                        'ref': reft,
                        'dim': 'time',
                    },
                })

            ddata.update({
                f'{keyinv}-chi2n': {
                    'data': chi2n,
                    'ref': reft,
                },
                f'{keyinv}-mu': {
                    'data': mu,
                    'ref': reft,
                },
                f'{keyinv}-reg': {
                    'data': regularity,
                    'ref': reft,
                },
                f'{keyinv}-niter': {
                    'data': niter,
                    'ref': reft,
                },
            })

        # add inversion
        dobj = {
            'inversions': {
                keyinv: {
                    'data_in': key_data,
                    'sigma_in': key_sigma,
                    'matrix': key_matrix,
                    'sol': keyinv,
                    'operator': operator,
                    'geometry': geometry,
                    'isotropic': dalgo['isotropic'],
                    'algo': dalgo['name'],
                    'solver': solver,
                    'chain': chain,
                    'positive': dalgo['positive'],
                    'conv_crit': conv_crit,
                },
            },
        }
        if notime is True:
            dobj['inversions'][keyinv].update({
                'chi2n': chi2n,
                'mu': mu,
                'reg': regularity,
                'niter': niter,
            })

        coll.update(dobj=dobj, dref=dref, ddata=ddata)

    else:
        return sol_full, mu, chi2n, regularity, niter, spec, t


# #############################################################################
# #############################################################################
#                   _compute time loop
# #############################################################################


def _compute_inv_loop(
    # inputs
    dalgo=None,
    sol0=None,
    mu0=None,
    matrix=None,
    Tn=None,        # normalized geometry matrix (T)
    TTn=None,       # normalized tTT
    Tyn=None,       # normalized tTy
    R=None,
    precond=None,
    data_n=None,
    sigma=None,
    indok=None,
    # parameters
    m3d=None,
    conv_crit=None,
    isotropic=None,
    sparse=None,
    positive=None,
    chain=None,
    verb=None,
    kwdargs=None,
    method=None,
    options=None,
    dcon=None,
    # output
    sol=None,
    mu=None,
    chi2n=None,
    regularity=None,
    niter=None,
    spec=None,
):

    # -----------------------------------
    # Getting initial solution - step 1/2

    regul = dalgo['family'] != 'Non-regularized'

    nt, nchan = data_n.shape
    nbs = Tn.shape[1]

    if verb >= 2:
        form = "nchan * chi2n   +   mu *  R           "
        verb2head = f"\n\t\titer    {form} \t\t\t  tau  \t      conv"
    else:
        verb2head = None

    # -----------------------------------
    # Options for quadratic solvers only

    bounds = None
    func_val, func_jac, func_hess = None, None, None
    if regul and positive is True:

        bounds = tuple([(0., None) for ii in range(0, sol0.size)])

        def func_val(x, mu=mu0, Tn=Tn, yn=data_n[0, :], TTn=None, Tyn=None):
            return np.sum((Tn.dot(x) - yn)**2) + mu*x.dot(R.dot(x))

        def func_jac(x, mu=mu0, Tn=None, yn=None, TTn=TTn, Tyn=Tyn):
            return 2.*(TTn + mu*R).dot(x) - 2.*Tyn

        def func_hess(x, mu=mu0, Tn=None, yn=None, TTn=TTn, Tyn=Tyn):
            return 2.*(TTn + mu*R)

    elif not regul:

        if positive is True:
            bounds = (
                np.zeros((nbs,), dtype=float),
                np.full((nbs,), np.inf),
            )
        else:
            bounds = (-np.inf, np.inf)

    # ---------
    # time loop

    # Beware of element-wise operations vs matrix operations !!!!
    nbsi = nbs
    bi = bounds
    indbsi = np.ones((nbsi,), dtype=bool)
    for ii in range(0, nt):

        if verb >= 1:
            msg = f"\ttime step {ii+1} / {nt} "
            print(msg, end='', flush=True)

        # update intermediates if multiple sigmas
        if sigma.shape[0] > 1 or m3d or indok is not None:

            # update terms
            Tni, TTni, Tyni, yni, nchani = _update_TTyn(
                sparse=sparse,
                data_n=data_n,
                sigma=sigma,
                matrix=matrix,
                Tn=Tn,
                TTn=TTn,
                Tyn=Tyn,
                indok=indok,
                ii=ii,
                m3d=m3d,
                regul=regul,
            )

        if dcon is not None:
            ic = 0 if ii == 0 and not dcon['hastime'] else ii
            nbsi, indbsi, Tni, TTni, Tyni, yni, bi = _update_ttyn_constraints(
                sparse=sparse,
                Tni=Tni,
                TTni=TTni,
                Tyni=Tyni,
                yni=yni,
                bounds=bounds,
                ii=ic,
                dcon=dcon,
                regul=regul,
            )

        # solving
        (
            sol[ii, indbsi], mu[ii], chi2n[ii], regularity[ii],
            niter[ii], spec[ii],
        ) = dalgo['func'](
            Tn=Tni,
            TTn=TTni,
            Tyn=Tyni,
            R=R,
            yn=yni,
            # initial guess
            sol0=sol0[indbsi],
            mu0=mu0,
            # problem size
            nchan=nchani,
            nbs=nbsi,
            # parameters
            conv_crit=conv_crit,
            precond=precond,
            verb=verb,
            verb2head=verb2head,
            # quad-only
            func_val=func_val,
            func_jac=func_jac,
            func_hess=func_hess,
            bounds=bi,
            method=method,
            options=options,
            **kwdargs,
        )

        if dcon is not None:
            if dcon['coefs'] is not None:
                sol[ii, :] = (
                    dcon['coefs'][ic].dot(sol[ii, indbsi])
                    + dcon['offset'][ic, :]
                )
            else:
                sol[ii, :] = sol[ii, :] + dcon['offset'][ic, :]
        # post
        if chain:
            sol0[:] = sol[ii, :]
        mu0 = mu[ii]

        if verb == 1:
            msg = f"   chi2n = {chi2n[ii]:.3e}    niter = {niter[ii]}"
            print(msg, end='\n', flush=True)


# #############################################################################
# #############################################################################
#                   _compute time loop - TOMOTOK
# #############################################################################


def _compute_inv_loop_tomotok(
    dalgo=None,
    # func=None,
    sol0=None,
    mu0=None,
    matrix=None,
    Tn=None,
    TTn=None,
    Tyn=None,
    R=None,
    precond=None,
    data_n=None,
    sigma=None,
    indok=None,
    # parameters
    conv_crit=None,
    isotropic=None,
    sparse=None,
    positive=None,
    chain=None,
    verb=None,
    sol=None,
    mu=None,
    chi2n=None,
    regularity=None,
    niter=None,
    spec=None,
    kwdargs=None,
    method=None,
    options=None,
):

    # -----------------------------------
    # Getting initial solution - step 1/2

    nt, nchan = data_n.shape
    if not isinstance(R, np.ndarray):
        nbs = R[0].shape[0]
        R = (R,)
    else:
        nbs = R.shape[0]

    if verb >= 2:
        form = "nchan * chi2n   +   mu *  R           "
        verb2head = f"\n\t\titer    {form} \t\t\t  tau  \t      conv"
    else:
        verb2head = None

    # ---------
    # time loop

    # Beware of element-wise operations vs matrix operations !!!!
    for ii in range(0, nt):

        if verb >= 1:
            msg = f"\ttime step {ii+1} / {nt} "
            print(msg, end='\n', flush=True)

        # update intermediates if multiple sigmas
        if sigma.shape[0] > 1:
            _update_TTyn(
                sparse=sparse,
                sigma=sigma,
                mati=mi,
                Tn=Tn,
                TTn=TTn,
                ii=ii,
            )

        Tyn[:] = Tn.T.dot(data_n[ii, :])

        # solving
        (
            sol[ii, :], chi2n[ii], regularity[ii],
        ) = dalgo['func'](
            sig_norm=data_n[ii, :],
            gmat_norm=Tn,
            deriv=R,
            method=None,
            num=None,
            # additional
            nchan=nchan,
            **kwdargs,
        )

        # post
        if chain:
            sol0[:] = sol[ii, :]
        mu0 = mu[ii]

        if verb == 1:
            msg = f"   chi2n = {chi2n[ii]:.3e}    niter = {niter[ii]}"
            print(msg, end='\n', flush=True)


# #############################################################################
# #############################################################################
#                      utility
# #############################################################################


def _update_TTyn(
    sparse=None,
    data_n=None,
    sigma=None,
    matrix=None,
    Tn=None,
    TTn=None,
    Tyn=None,
    indok=None,
    ii=None,
    m3d=None,
    regul=None,
):
    # update matrix
    if indok is None:
        if m3d:
            mi = matrix[ii, :, :]
        else:
            mi = matrix
    else:
        if m3d:
            mi = matrix[ii, indok[ii, :], :]
        else:
            mi = matrix[indok[ii, :], :]

    # update sig
    if sigma.shape[0] == 1:
        if indok is None:
            sig = sigma[0, :]
        else:
            sig = sigma[0, indok[ii, :]]
    else:
        if indok is None:
            sig = sigma[ii, :]
        else:
            sig = sigma[ii, indok[ii, :]]

    # update data_n
    if indok is None:
        yn = data_n[ii, :]
    else:
        yn = data_n[ii, indok[ii, :]]

    # intermediates
    if indok is None:
        if sparse:
            Tn.data = scpsp.diags(1./sig).dot(mi).data
            TTn.data = Tn.T.dot(Tn).data
        else:
            Tn[...] = mi / sig[:, None]
            TTn[...] = Tn.T.dot(Tn)

    else:
        if sparse:
            Tn = scpsp.diags(1./sig).dot(mi)
            TTn = Tn.T.dot(Tn)
        else:
            Tn = mi / sig[:, None]
            TTn = Tn.T.dot(Tn)

    # Tyn (for reguarized algorithms)
    if regul:
        if indok is None:
            Tyn[:] = Tni.T.dot(yni)
        else:
            Tyn = Tni.T.dot(yni)

    return Tn, TTn, Tyn, yn, yn.size


def _update_ttyn_constraints(
    sparse=None,
    Tni=None,
    TTni=None,
    Tyni=None,
    yni=None,
    bounds=None,
    ii=None,
    dcon=None,
    regul=None,
):

    # yni
    yni = yni - Tni.dot(dcon['offset'][ii, :])

    # Tni
    Tni = Tni.dot(dcon['coefs'][ii])

    # regul => Tyni, TTni
    if regul:
        raise NotImplementedError()

    # nbsi
    nbsi = Tni.shape[1]

    # indbsi
    indbsi = dcon['indbs'][ii]

    # bounds
    if np.isscalar(bounds[0]):
        pass
    else:
        bounds = (bounds[0][indbsi], bounds[1][indbsi])

    return nbsi, indbsi, Tni, TTni, Tyni, yni, bounds
