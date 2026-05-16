#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: 2 m telescope spider spot diagram.

This example adds a spider/support mask to the 2 m telescope and traces rays to
show how the obstruction appears in the spot diagram.

What this example teaches:
- how to build a mask from PyVista planes and discs
- how `Mask_Shape` and `Mask_Type` represent an obstruction
- how a small focus shift can make the spider signature visible

Expected output:
- a 3D telescope view with the masked ray bundle
- a Matplotlib spot diagram

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos

P_Obj = Kos.surf()
P_Obj.Rc = 0
P_Obj.Thickness = 1000
P_Obj.Glass = "AIR"
P_Obj.Diameter = 1.059E+003 * 2.0
P_Obj.Drawing = 0


Spider = Kos.surf()
Spider.Rc = 999999999999.0
Spider.Thickness = 3.452229924716749E+003 + 100.0
Spider.Glass = "AIR"
Spider.Diameter = 1.059E+003 * 2.0
plane1 = pv.Plane(center=[0, 0, 0], direction=[0, 0, 1], i_size=30, j_size=2100, i_resolution=10, j_resolution=10)
plane2 = pv.Plane(center=[0, 0, 0], direction=[0, 0, 1], i_size=2100, j_size=30, i_resolution=10, j_resolution=10)
Baffle1 = pv.Disc(center=[0.0, 0.0, 0.0], inner=0, outer=875 / 2.0, normal=[0, 0, 1], r_res=1, c_res=100)
Baffle2 = Baffle1.merge(plane1)
Baffle3 = Baffle2.merge(plane2)
AAA = pv.MultiBlock()
AAA.append(plane1)
AAA.append(plane2)
AAA.append(Baffle1)
Spider.Mask_Shape = AAA
Spider.Mask_Type = 2
Spider.TiltZ = 0


Thickness = 3.452229924716749E+003
M1 = Kos.surf()
M1.Rc = -9.638000000004009E+003
M1.Thickness = -Thickness
M1.k = -1.077310000000000E+000
M1.Glass = "MIRROR"
M1.Diameter = 1.059E+003 * 2.0
M1.InDiameter = 250 * 2.0


M2 = Kos.surf()
M2.Rc = -3.93E+003
focusShift = 1.0  # Set to 0 for focus; 1 makes the spider visible in the spot diagram.
M2.Thickness = Thickness + 1.037179115116706E+003 + focusShift
M2.k = -4.328100000000000E+000
M2.Glass = "MIRROR"
M2.Diameter = 3.365E+002 * 2.0


P_Ima = Kos.surf()
P_Ima.Diameter = 100.0
P_Ima.Glass = "AIR"
P_Ima.Name = "Image plane"


A = [P_Obj, Spider, M1, M2, P_Ima]
configuracion_1 = Kos.Setup()


Telescopio = Kos.system(A, configuracion_1)
Rayos = Kos.raykeeper(Telescopio)


tam = 7
rad = 2200 / 2
tsis = len(A) - 1
for i in range(-tam, tam + 1):
    for j in range(-tam, tam + 1):
        x_0 = (i / tam) * rad
        y_0 = (j / tam) * rad
        r = np.sqrt((x_0 * x_0) + (y_0 * y_0))
        if r < rad:
            tet = 0.0
            pSource_0 = [x_0, y_0, 0.0]
            dCos = [0.0, np.sin(np.deg2rad(tet)), np.cos(np.deg2rad(tet))]
            W = 0.6
            Telescopio.Trace(pSource_0, dCos, W)
            Rayos.push()


Kos.display3d(Telescopio, Rayos, 2)
X, Y, Z, L, M, N = Rayos.pick(-1)


plt.plot(X, Y, 'x')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Spot Diagram')
plt.axis('square')
plt.show()
