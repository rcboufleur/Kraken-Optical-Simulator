#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: save and reload setup data before tracing a colored doublet.

This example serializes a KrakenOS setup object with `pickle`, reloads it, and
then uses it to build and trace a colored doublet lens.

What this example teaches:
- how a setup object can be saved and restored with Python pickle
- how the reloaded setup is passed to `system`
- how to combine serialization with a 3D visualization example

Expected output:
- a local file named `mi_objeto.pkl`
- an interactive or rendered 3D view, depending on the Python environment

Didactic note:
- the generated pickle file is only an example artifact. It is ignored by git
  and can be deleted after running the script.

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

import pickle
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


with open('mi_objeto.pkl', 'wb') as archivo_salida:
    # Save the setup object so it can be reloaded later in the example.
    pickle.dump(configuracion_1, archivo_salida)


with open('mi_objeto.pkl', 'rb') as archivo_entrada:
    configuracion_1 = pickle.load(archivo_entrada)


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
