

import datastock as ds


from ..geom import _etendue


# #############################################################################
# #############################################################################
#                       Etendue
# #############################################################################


def _diag_compute_etendue_check(
    coll=None,
    key=None,
    analytical=None,
    numerical=None,
    store=None,
):

    # --------
    # key

    lok = [
        k0 for k0, v0 in coll.dobj.get('diagnostic', {}).items()
        if len(v0['optics']) > 1
    ]
    key = ds._generic_check._check_var(
        key, 'key',
        types=str,
        allowed=lok,
    )

    # -----------
    # analytical

    analytical = ds._generic_check._check_var(
        analytical, 'analytical',
        types=bool,
        default=True,
    )

    # -----------
    # numerical

    numerical = ds._generic_check._check_var(
        numerical, 'numerical',
        types=bool,
        default=True,
    )

    # -----------
    # store

    lok = [False]
    if analytical is True:
        lok.append('analytical')
    if numerical is True:
        lok.append('numerical')
    store = ds._generic_check._check_var(
        store, 'store',
        default=lok[-1],
        allowed=lok,
    )

    return key, analytical, numerical, store


def _diag_compute_etendue(
    coll=None,
    key=None,
    analytical=None,
    numerical=None,
    res=None,
    check=None,
    verb=None,
    plot=None,
    store=None,
):

    # ------------
    # check inputs

    key, analytical, numerical, store = _diag_compute_etendue_check(
        coll=coll,
        key=key,
        analytical=analytical,
        numerical=numerical,
        store=store,
    )

    # prepare optics
    optics = coll.dobj['diagnostic'][key]['optics']
    key_cam = optics[0]

    # --------
    # etendues

    detend = _etendue.compute_etendue(
        det=coll.get_as_dict(which='camera', key=optics[0]),
        aperture=coll.get_as_dict(which='aperture', key=optics[1:]),
        analytical=analytical,
        numerical=numerical,
        res=res,
        margin_par=None,
        margin_perp=None,
        check=check,
        verb=verb,
        plot=plot,
    )

    # ----------
    # store

    if store is not False:

        # data
        etendue = detend[store][-1, :]

        # dict for etendue
        ketendue = f'{key}-etend'

        ddata = {
            ketendue: {
                'data': etendue,
                'ref': coll.dobj['camera'][key_cam]['ref'],
                'dim': 'etendue',
                'quant': 'etendue',
                'name': 'etendue',
                'units': 'm2.sr'
            },
        }
        coll.update(ddata=ddata)

        coll.set_param(
            which='diagnostic',
            key=key,
            param='etendue',
            value=ketendue,
        )

    return detend
