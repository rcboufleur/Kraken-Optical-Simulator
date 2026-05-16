#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single-ray reflection grating trace.

Traces one ray through a reflective diffraction grating so the sign conventions and diffraction order are easy to inspect.

What to look at:
- the ray source, direction cosines, and wavelength passed to Trace.
- the grating parameters and diffraction order.

Units are the KrakenOS example defaults: distances in millimeters and
wavelengths in micrometers unless the code states otherwise.
"""

import numpy as np


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos

P_Obj = Kos.surf()
P_Obj.Rc = 0.0
P_Obj.Thickness = 250
P_Obj.Glass = "AIR"
P_Obj.Diameter = 30.0


Dif_Obj = Kos.surf()
Dif_Obj.Rc = 0.0
Dif_Obj.Thickness = -250
Dif_Obj.Glass = "MIRROR"
Dif_Obj.Diameter = 30.0
Dif_Obj.Grating_D = 1000/600
Dif_Obj.Diff_Ord = 1
Dif_Obj.Grating_Angle = 0.0


P_Ima = Kos.surf()
P_Ima.Rc = 0.0
P_Ima.Name = "Image plane"
P_Ima.Thickness = 0.0
P_Ima.Glass = "AIR"
P_Ima.Diameter = 1000.0
P_Ima.Drawing = 0


A = [P_Obj, Dif_Obj, P_Ima]
configuracion_1 = Kos.Setup()


Doblete = Kos.system(A, configuracion_1)
Rayos = Kos.raykeeper(Doblete)


pSource_0 = [0, 0, 0.0]
tet = 0
dCos = [0.0, np.sin(np.deg2rad(tet)), np.cos(np.deg2rad(tet))]
w = np.linspace(.35, .90, 10)
for W in w:
    Doblete.Trace(pSource_0, dCos, W)
    print(Doblete.XYZ[-1])
    Rayos.push()


Kos.display3d(Doblete, Rayos, 1)
