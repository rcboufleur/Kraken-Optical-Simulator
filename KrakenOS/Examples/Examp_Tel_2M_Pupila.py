"""Example: pupil calculation in a 2 m telescope.

This example computes input and output pupil properties for the 2 m telescope,
generates a hexapolar pupil ray pattern, traces it, and plots the image-plane
spot positions.

What this example teaches:
- how to configure `PupilCalc` for a telescope
- how to inspect input and output pupil radius, position, and orientation
- how to derive approximate angular pupil orientation from direction cosines
- how to trace the pupil-generated ray set

Expected output:
- printed pupil properties
- a 2D telescope layout
- a spot diagram at the image plane

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import numpy as np

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos

P_Obj = Kos.surf()
P_Obj.Rc = 0
P_Obj.Thickness = 1000 + 3.452200000000000E+003
P_Obj.Glass = "AIR"
P_Obj.Diameter = 1.059E+003 * 2.0


Thickness = 3.452200000000000E+003
M1 = Kos.surf()
M1.Rc = -9.638000000004009E+003
M1.Thickness = -Thickness
M1.k = -1.077310000000000E+000
M1.Glass = "MIRROR"
M1.Diameter = 1.059E+003 * 2.0
M1.InDiameter = 250 * 2.0


M2 = Kos.surf()
M2.Rc = -3.93E+003
M2.Thickness = Thickness + 1.037525880125084E+003
M2.k = -4.328100000000000E+000
M2.Glass = "MIRROR"
M2.Diameter = 3.365E+002 * 2.0
M2.TiltY = 0.1
M2.TiltX = 0.1
M2.AxisMove = 0


P_Ima = Kos.surf()
P_Ima.Diameter = 300.0
P_Ima.Glass = "AIR"
P_Ima.Name = "Image plane"


A = [P_Obj, M1, M2, P_Ima]
configuracion_1 = Kos.Setup()
Telescopio = Kos.system(A, configuracion_1)


W = 0.4
sup = 1
AperVal = 2010
AperType = "EPD"  # "STOP"
Pup = Kos.PupilCalc(Telescopio, sup, W, AperType, AperVal)


print("Input pupil radius:")
print(Pup.RadPupInp)
print("Input pupil position:")
print(Pup.PosPupInp)
print("Output pupil radius:")
print(Pup.RadPupOut)
print("Output pupil position:")
print(Pup.PosPupOut)
print("Output pupil position relative to focal plane:")
print(Pup.PosPupOutFoc)
print("Output pupil orientation:")
print(Pup.DirPupSal)
[L, M, N] = Pup.DirPupSal
print(L, M, N)
TetX = np.rad2deg(np.arcsin(-M))
TetY = np.rad2deg(np.arcsin(L / np.cos(np.arcsin(-M))))
print(TetX, TetY)
print("---------------------------------------------------------------")


Pup.Samp = 10
Pup.Ptype = "hexapolar"
Pup.FieldY = 0.0
Pup.FieldType = "angle"
x, y, z, L, M, N = Pup.Pattern2Field()
Rayos = Kos.raykeeper(Telescopio)


for i in range(0, len(x)):
    pSource_0 = [x[i], y[i], z[i]]
    dCos = [L[i], M[i], N[i]]
    W = 0.4
    Telescopio.Trace(pSource_0, dCos, W)
    Rayos.push()


Kos.display2d(Telescopio, Rayos, 1, 1)


X, Y, Z, L, M, N = Rayos.pick(-1)
plt.figure(300)
plt.plot(X, Y, 'x')
plt.axis('square')
plt.show(block=False)
