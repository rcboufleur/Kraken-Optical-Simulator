#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tilted doublet built with deferred system construction.

Defines a tilted doublet and delays the system build so null or pickled configurations can be tested.

What to look at:
- the ray source, direction cosines, and wavelength passed to Trace.

Units are the KrakenOS example defaults: distances in millimeters and
wavelengths in micrometers unless the code states otherwise.
"""

import numpy as np


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos
import pickle


P_Obj = Kos.surf()
P_Obj.Rc = 0.0
P_Obj.Thickness = 1
P_Obj.Glass = "AIR"
P_Obj.Diameter = 30.0


L1a = Kos.surf()
L1a.Rc = 5.513435044607768E+001
L1a.Thickness = 6.0
L1a.Glass = "BK7"
L1a.Diameter = 30.0
L1a.TiltX = 4


Null1_L1a = Kos.surf()
Null1_L1a.Thickness = -L1a.Thickness
Null1_L1a.Glass = "NULL"
Null1_L1a.Diameter = L1a.Diameter
Null1_L1a.TiltX = -L1a.TiltX
Null1_L1a.Order = 1


Null2_L1a = Kos.surf()
Null2_L1a.Thickness = L1a.Thickness
Null2_L1a.Glass = "NULL"
Null2_L1a.Diameter = L1a.Diameter


L1b = Kos.surf()
L1b.Rc = -4.408716526030626E+001
L1b.Thickness = 3.0
L1b.Glass = "F2"
L1b.Diameter = 30


L1c = Kos.surf()
L1c.Rc = -2.246906271406796E+002
L1c.Thickness = 9.737871661422000E+001
L1c.Glass = "AIR"
L1c.Diameter = 30


P_Ima = Kos.surf()
P_Ima.Rc = 0.0
P_Ima.Thickness = 0.0
P_Ima.Glass = "AIR"
P_Ima.Diameter = 10.0
P_Ima.Name = "Image plane"


A = [P_Obj, L1a, Null1_L1a, Null2_L1a, L1b, L1c, P_Ima]
configuracion_1 = Kos.Setup()


Doblete = Kos.system(A, configuracion_1, build = 0)


# with open('mi_objeto.pkl', 'wb') as archivo_salida:
#     # Usa pickle.dump para serializar y guardar el objeto en el archivo.
#     pickle.dump(Doblete, archivo_salida)


# with open('mi_objeto.pkl', 'rb') as archivo_entrada:
#     Doblete = pickle.load(archivo_entrada)


Doblete.build()

Rayos = Kos.raykeeper(Doblete)


tam = 5
rad = 10.0
tsis = 6
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


Kos.display3d(Doblete, Rayos, 2)
