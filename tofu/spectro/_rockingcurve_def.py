
import numpy as np


# #############################################################################
# #############################################################################
#                                   _DCRYST
# #############################################################################
# #############################################################################

_DCRYST = {
    'alpha-Quartz': {
        'name': 'alpha-Quartz',
        'symbol': 'aQz',
        'atoms': ['Si', 'O'],
        'atomic number': [14., 8.],
        'number of atoms': [3., 6.],
        'Miller indices (h,k,l)': np.r_[1., 1., 0.],
        'meshtype': 'hexagonal',
        'mesh positions': {
            'Si': {
                'u': np.r_[0.465],
                'x': None,
                'y': None,
                'z': None,
            },
            'O': {
                'u': np.r_[0.415, 0.272, 0.120],
                'x': None,
                'y': None,
                'z': None,
            },
        },
        'mesh positions sources': 'R.W.G. Wyckoff, Crystal Structures (1963)',
        'Inter-atomic distances': {
            'a0': 4.91304,
            'c0': 5.40463,
        },
        'Inter-atomic distances comments' :
            'at 25°C, unit = Angstroms, within the unit cell',
        'Inter-atomic distances sources': 'R.W.G. Wyckoff, Crystal Structures',
        'Thermal expansion coefs': {
            'alpha_a': 13.37e-6,
            'alpha_c': 7.97e-6,
        },
        'Thermal expansion coefs comments':
            'unit = [°C⁻1], in parallel directions to a0 and c0',
        'Thermal expansion coefs sources': 'R.W.G. Wyckoff, Crystal Structures',
        'Volume': None,
        'Inter-reticular spacing': None,
        'sin(theta)/lambda': {
            'Si': np.r_[
                0., 0.1, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7,
                0.8, 0.9, 1., 1.1, 1.2, 1.3, 1.4, 1.5,
            ],
            'O': np.r_[
                0., 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1., 1.1,
            ],
        },
        'sin(theta)/lambda sources':
            'Intern. Tables for X-Ray Crystallography, Vol.I,II,III,IV (1985)',
        'atomic scattering factor': {
            'Si': np.r_[
                12., 11., 9.5, 8.8, 8.3, 7.7, 7.27, 6.25, 5.3,
                4.45, 3.75, 3.15, 2.7, 2.35, 2.07, 1.87, 1.71, 1.6,
            ],
            'O': np.r_[
                9., 7.836, 5.756, 4.068, 2.968, 2.313, 1.934, 1.710, 1.566,
                1.462, 1.373, 1.294,
            ],
        },
        'atomic scattering factor sources':
            'Intern. Tables for X-Ray Crystallography, Vol.I,II,III,IV (1985)',
    },
    'Germanium': {
        'name': None,
        'symbol': None,
        'atoms': None,
        'atomic number': None,
        'number of atoms': None,
        'Miller indices (h,k,l)': None,
        'meshtype': None,
        'mesh positions': None,
        'mesh positions sources': None,
        'Inter-atomic distances': {
            'a0': None,
            'c0': None,
        },
        'Inter-atomic distances comments' : None,
        'Inter-atomic distances sources': None,
        'Thermal expansion coefs': {
            'a0': None,
            'c0': None,
        },
        'Thermal expansion coefs comments': None,
        'Thermal expansion coefs sources': None,
        'Volume': None,
        'Inter-reticular spacing': None,
        'sin(theta)/lambda': None,
        'sin(theta)/lambda sources': None,
        'atomic scattering factor': None,
        'atomic scattering factor sources': None,
    },
}

# #############################################################################
# #############################################################################
#                         Atoms positions in mesh
# #############################################################################
# #############################################################################

# Positions from literature
# -------------------------

# Si and O positions for alpha-Quartz crystal
# xsi = np.r_[-u, u, 0.]
# ysi = np.r_[-u, 0., u]
# zsi = np.r_[1./3., 0., 2./3.]
# xo = np.r_[x, y - x, -y, x - y, y, -x]
# yo = np.r_[y, -x, x - y, -y, x, y - x]
# zo = np.r_[z, z + 1./3., z + 2./3., -z, 2./3. - z, 1./3. - z]

# Atoms positions for Germanium crystal

# Attribution to alpha-Quartz
# ---------------------------

# Position of the 3 Si atoms in the unit cell
uSi = _DCRYST['alpha-Quartz']['mesh positions']['Si']['u'][0]
_DCRYST['alpha-Quartz']['mesh positions']['Si']['x'] = np.r_[
    -uSi,
    uSi,
    0.
]
_DCRYST['alpha-Quartz']['mesh positions']['Si']['y'] = np.r_[
    -uSi,
    0.,
    uSi
]
_DCRYST['alpha-Quartz']['mesh positions']['Si']['z'] = np.r_[
    1./3.,
    0.,
    2./3.
]

# Position of the 6 O atoms in the unit cell
uOx = _DCRYST['alpha-Quartz']['mesh positions']['O']['u'][0]
uOy = _DCRYST['alpha-Quartz']['mesh positions']['O']['u'][1]
uOz = _DCRYST['alpha-Quartz']['mesh positions']['O']['u'][2]
_DCRYST['alpha-Quartz']['mesh positions']['O']['x'] = np.r_[
    uOx,
    uOy - uOx,
    -uOy,
    uOx - uOy,
    uOy,
    -uOx
]
_DCRYST['alpha-Quartz']['mesh positions']['O']['y'] = np.r_[
    uOy,
    -uOx,
    uOx - uOy,
    -uOy,
    uOx,
    uOy - uOx
]
_DCRYST['alpha-Quartz']['mesh positions']['O']['z'] = np.r_[
    uOz,
    uOz + 1./3.,
    uOz + 2./3.,
    -uOz,
    2./3. - uOz,
    1./3. - uOz
]

# Attribution to Germanium
# ------------------------

# #############################################################################
# #############################################################################
#                         Elementary box volume and
#                       inter-reticular spacing d_hkl
# #############################################################################
# #############################################################################

# Definition of volume and inter-reticular spacing relations, f(meshtype)
# -----------------------------------------------------------------------

def hexa_volume(a, c):
    return (a**2)*c*(np.sqrt(3.)/2.)

def hexa_spacing(h, k, l, a, c):
    return np.sqrt(
        (3.*(a**2)*(c**2))/(4.*(h**2 + k**2 + h*k)*(c**2) + 3.*(l**2)*(a**2))
    )

# Attribution to alpha-Quartz
# ---------------------------

a = _DCRYST['alpha-Quartz']['Inter-atomic distances']['a0']
c = _DCRYST['alpha-Quartz']['Inter-atomic distances']['c0']
h = _DCRYST['alpha-Quartz']['Miller indices (h,k,l)'][0]
k = _DCRYST['alpha-Quartz']['Miller indices (h,k,l)'][1]
l = _DCRYST['alpha-Quartz']['Miller indices (h,k,l)'][2]

_DCRYST['alpha-Quartz']['Volume'] = hexa_volume(a=a, c=c)
_DCRYST['alpha-Quartz']['Inter-reticular spacing'] = hexa_spacing(
    h=h, k=k, l=l, a=a, c=c,
)

# Attribution to Germanium
# ------------------------

