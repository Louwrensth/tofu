import numpy as np
import tofu.geom._GG as GG

# VPoly
thet = np.linspace(0.,2.*np.pi,100)
VPoly = np.array([2.+1.*np.cos(thet), 0.+1.*np.sin(thet)])


RMinMax = np.array([np.min(VPoly[0,:]), np.max(VPoly[0,:])])
ZMinMax = np.array([np.min(VPoly[1,:]), np.max(VPoly[1,:])])
dR, dZ, dRPhi = 0.05, 0.05, 0.05
LDPhi = [None, [3.*np.pi/4.,5.*np.pi/4.], [-np.pi/4.,np.pi/4.]]

for ii in range(0,len(LDPhi)):
    print("ii  =================== ", ii)
    out = GG._Ves_Vmesh_Tor_SubFromD_cython(dR, dZ, dRPhi,
                                                             RMinMax,
                                                             ZMinMax,
                                                             DR=np.array([0.5,2.]),
                                                             DZ=np.array([0.,1.2]),
                                                             DPhi=LDPhi[ii],
                                                             VPoly=VPoly,
                                                             Out='(R,Z,Phi)',
                                                             num_threads=48,
                                                             margin=1.e-9)
    print("*******************subfrom D done*******************")
    Pts, dV, ind, dRr, dZr, dRPhir = out
    print("got the values..................................")
    assert Pts.ndim==2 and Pts.shape[0]==3
    assert np.all(Pts[0,:]>=1.) and np.all(Pts[0,:]<=2.) and \
        np.all(Pts[1,:]>=0.) and np.all(Pts[1,:]<=1.)
    marg = np.abs(np.arctan(np.mean(dRPhir)/np.min(VPoly[1,:])))
    if not LDPhi[ii] is None:
        LDPhi[ii][0] = np.arctan2(np.sin(LDPhi[ii][0]),np.cos(LDPhi[ii][0]))
        LDPhi[ii][1] = np.arctan2(np.sin(LDPhi[ii][1]),np.cos(LDPhi[ii][1]))
        if LDPhi[ii][0]<=LDPhi[ii][1]:
            assert np.all((Pts[2,:]>=LDPhi[ii][0]-marg) &
                          (Pts[2,:]<=LDPhi[ii][1]+marg))
        else:
            assert np.all( (Pts[2,:]>=LDPhi[ii][0]-marg) |
                           (Pts[2,:]<=LDPhi[ii][1]+marg))
    assert dV.shape==(Pts.shape[1],)
    assert all([ind.shape==(Pts.shape[1],),
                ind.dtype==int,
                np.unique(ind).size==ind.size,
                np.all(ind==np.unique(ind)),
                np.all(ind>=0)])
    assert dRPhir.ndim==1

    print(">>> about to do sub from ind")
    Ptsi, \
        dVi, dRri, dZri,\
        dRPhiri = GG._Ves_Vmesh_Tor_SubFromInd_cython(dR, dZ, dRPhi,
                                                      RMinMax, ZMinMax, ind,
                                                      Out='(R,Z,Phi)',
                                                      margin=1.e-9)
    print("<<< done sub from ind")
    assert np.allclose(Pts,Ptsi)
    assert np.allclose(dV,dVi)
    assert dRr==dRri and dZr==dZri
    assert np.allclose(dRPhir,dRPhiri)
