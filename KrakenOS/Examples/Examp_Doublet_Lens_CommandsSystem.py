#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: inspect system data after tracing a doublet.

This example traces one ray through a doublet and prints the main arrays stored
by the `system` object after `Trace` is executed.

What this example teaches:
- how to inspect effective focal length and principal planes
- how KrakenOS records touched surfaces, glass names, coordinates, normals,
  optical path, indices, diffraction data, Fresnel coefficients, and energy
- how to connect printed diagnostic arrays with the plotted ray path

Expected output:
- a 3D view of the traced ray
- printed diagnostic arrays from the `system` object

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

import numpy as np


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos

P_Obj = Kos.surf()
P_Obj.Rc = 0.0
P_Obj.Thickness = 0.1
P_Obj.Glass = "AIR"
P_Obj.Diameter = 30.


P_Obj2 = Kos.surf()
P_Obj2.Rc = 0.0
P_Obj2.Thickness = 10
P_Obj2.Glass = "AIR"
P_Obj2.Diameter = 30.0


L1a = Kos.surf()
L1a.Rc = 9.284706570002484E+001
L1a.Thickness = 6.0
L1a.Glass = "BK7"
L1a.Diameter = 30.0
L1a.Axicon = 0


L1b = Kos.surf()
L1b.Rc = -3.071608670000159E+001
L1b.Thickness = 3.0
L1b.Glass = "F2"
L1b.Diameter = 30


L1c = Kos.surf()
L1c.Rc = -7.819730726078505E+001
L1c.Thickness = 9.737604742910693E+001
L1c.Glass = "AIR"
L1c.Diameter = 30


P_Ima = Kos.surf()
P_Ima.Rc = 0.0
P_Ima.Thickness = 0.0
P_Ima.Glass = "AIR"
P_Ima.Diameter = 18.0
P_Ima.Name = "Image plane"


A = [P_Obj, P_Obj2, L1a, L1b, L1c, P_Ima]
configuracion_1 = Kos.Setup()


Doblete = Kos.system(A, configuracion_1)
Rayos = Kos.raykeeper(Doblete)


pSource_0 = [0, 14, 0]
tet = 0.1
dCos = [0.0, np.sin(np.deg2rad(tet)), -np.cos(np.deg2rad(tet))]
W = 0.4
Doblete.Trace(pSource_0, dCos, W)
Rayos.push()


Kos.display3d(Doblete, Rayos, 2)


print("Effective focal length")
print(Doblete.EFFL)
print("Front principal plane")
print(Doblete.PPA)
print("Rear principal plane")
print(Doblete.PPP)
print("Surfaces touched by the ray")
print(Doblete.SURFACE)
print("Surface names")
print(Doblete.NAME)
print("Surface glass names")
print(Doblete.GLASS)
print("Ray coordinates at the surfaces")
print(Doblete.XYZ)
print("Additional traced-ray arrays")
print(Doblete.S_XYZ)
print(Doblete.T_XYZ)
print(Doblete.OST_XYZ)
print(Doblete.DISTANCE)
print(Doblete.OP)
print(Doblete.TOP)
print(Doblete.TOP_S)
print(Doblete.ALPHA)
print(Doblete.S_LMN)
print(Doblete.LMN)
print(Doblete.R_LMN)
print(Doblete.N0)
print(Doblete.N1)
print(Doblete.WAV)
print(Doblete.G_LMN)
print(Doblete.ORDER)
print(Doblete.GRATING)
print(Doblete.RP)
print(Doblete.RS)
print(Doblete.TP)
print(Doblete.TS)
print(Doblete.TTBE)
print(Doblete.TT)
print(Doblete.BULK_TRANS)
