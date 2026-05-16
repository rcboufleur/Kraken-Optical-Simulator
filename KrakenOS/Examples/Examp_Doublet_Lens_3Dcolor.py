#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: doublet lens with colored 3D visualization.

This example builds the standard doublet, assigns colors to the lens surfaces,
traces a small multi-wavelength ray bundle, and displays the result in 3D.

What this example teaches:
- how to set surface colors for visualization
- how to trace several wavelengths through the same system
- how to use `display3d` for a compact 3D view

Expected output:
- an interactive or rendered 3D view, depending on the Python environment

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
P_Obj.Thickness = 10
P_Obj.Glass = "AIR"
P_Obj.Diameter = 30.0


L1a = Kos.surf()
L1a.Rc = 9.284706570002484E+001
L1a.Thickness = 6.0
L1a.Glass = "BK7"
L1a.Diameter = 30.0
L1a.Axicon = 0
L1a.Color = [.8, .7, .4]


L1b = Kos.surf()
L1b.Rc = -3.071608670000159E+001
L1b.Thickness = 3.0
L1b.Glass = "F2"
L1b.Diameter = 30
L1b.Color = [.7, .4, .4]


L1c = Kos.surf()
L1c.Rc = -7.819730726078505E+001
L1c.Thickness = 9.737604742910693E+001
L1c.Glass = "AIR"
L1c.Diameter = 30


P_Ima = Kos.surf()
P_Ima.Rc = 0.0
P_Ima.Thickness = 0.0
P_Ima.Glass = "AIR"
P_Ima.Diameter = 100.0
P_Ima.Name = "Image plane"


A = [P_Obj, L1a, L1b, L1c, P_Ima]
configuracion_1 = Kos.Setup()


Doblete = Kos.system(A, configuracion_1)
Rayos = Kos.raykeeper(Doblete)


tam = 5
rad = 10.0
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
            W = 0.4
            Doblete.Trace(pSource_0, dCos, W)
            Rayos.push()
            W = 0.5
            Doblete.Trace(pSource_0, dCos, W)
            Rayos.push()
            W = 0.6
            Doblete.Trace(pSource_0, dCos, W)
            Rayos.push()


Kos.display3d(Doblete, Rayos, 1,BackgCol="Blue")
