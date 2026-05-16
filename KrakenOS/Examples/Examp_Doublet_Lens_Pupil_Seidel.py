#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: doublet pupil calculation with Seidel terms.

This example combines pupil setup, Seidel aberration calculations, and ray
tracing through a doublet lens.

What this example teaches:
- how to configure `PupilCalc` for Seidel analysis
- how to read spherical, coma, astigmatism, field curvature, and chromatic
  aberration outputs
- how changing Fraunhofer wavelengths affects chromatic aberration terms
- how to trace the pupil-generated rays after the aberration calculation

Expected output:
- printed Seidel and chromatic-aberration terms
- a 2D layout of the pupil-generated ray bundle

Didactic note:
- the commented print blocks are intentionally left in the file. They are
  optional inspection snippets for users who want to explore individual Seidel
  table entries and sums.

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos
import numpy as np


P_Obj = Kos.surf()
P_Obj.Rc = 0.0
P_Obj.Thickness = 100
P_Obj.Glass = "AIR"
P_Obj.Diameter = 30.0
P_Obj.Name = "P Obj"


L1a = Kos.surf()
L1a.Rc = 9.284706570002484E+001
L1a.Thickness = 6.0
L1a.Glass = "N-BK7"
L1a.Diameter = 30.0
L1a.Axicon = 0


L1b = Kos.surf()
L1b.Rc = -3.071608670000159E+001
L1b.Thickness = 3.0
L1b.Glass = "F2"
L1b.Diameter = 30


L1c = Kos.surf()
L1c.Rc = -7.819730726078505E+001
L1c.Thickness = 9.737604742910693E+001 - 40
L1c.Glass = "AIR"
L1c.Diameter = 30


pupila = Kos.surf()
pupila.Rc = 0
pupila.Thickness = 40.
pupila.Glass = "AIR"
pupila.Diameter = 15.0
pupila.Name = "Ap Stop"


P_Ima = Kos.surf()
P_Ima.Rc = 0.0
P_Ima.Thickness = 0.0
P_Ima.Glass = "AIR"
P_Ima.Diameter = 20.0


A = [P_Obj, L1a, L1b, L1c, pupila, P_Ima]
config_1 = Kos.Setup()


Doblete = Kos.system(A, config_1)


W = 0.6
Surf = 4
AperVal = 3
AperType = "EPD"
fieldType = "angle"

Pup = Kos.PupilCalc(Doblete, Surf, W, AperType, AperVal)
Pup.Samp = 25
Pup.Ptype = "fan"
Pup.FieldY = 3.25


AB = Kos.Seidel(Pup)

print("--------------------------------------")
print(AB.SAC_AN)
print(AB.SAC_NM)
print(AB.SAC_TOTAL)
print("--------------------------------------")
print(AB.SCW_AN)
print(AB.SCW_NM)
print(AB.SCW_TOTAL)
print("--------------------------------------")
print(AB.TAC_AN)
print(AB.TAC_NM)
print(AB.TAC_TOTAL)
print("--------------------------------------")
print(AB.LAC_AN)
print(AB.LAC_NM)
print(AB.LAC_TOTAL)
print("--------------------------------------")
print("Chromatic aberration")
print(AB.CL)
print(AB.CT)

print("--------------------------------------")

print("Where the Fraunhofer spectral lines are Wd (587.6 nm), Wf (486.1 nm), and Wc (656.3 nm)")


AB.Wc = 0.6563
AB.Wd = 0.5876
AB.Wf = 0.4861

print("If the wavelength is changed, the aberrations must be recalculated")
AB.calculate()

print("Chromatic aberration")
print(AB.CL)
print(AB.CT)


# Optional didactic inspection:
# Uncomment these blocks to inspect individual Seidel table rows and sums.
# They are disabled by default to keep the printed output compact.
# print( AB[0][0])
# print(np.sum(AB[1][0]), np.sum(AB[1][1]), np.sum(AB[1][2]), np.sum(AB[1][3]), np.sum(AB[1][4]))

# j=1
# print( AB[0][0+j])
# print(np.sum(AB[1+j][0]), np.sum(AB[1+j][1]), np.sum(AB[1+j][2]), np.sum(AB[1+j][3]), np.sum(AB[1+j][4]))

# j=2
# print( AB[0][0+j])
# print(np.sum(AB[1+j][0]), np.sum(AB[1+j][1]), np.sum(AB[1+j][2]), np.sum(AB[1+j][3]), np.sum(AB[1+j][4]))

# j=3
# print( AB[0][0+j])
# print(np.sum(AB[1+j][0]), np.sum(AB[1+j][1]), np.sum(AB[1+j][2]), np.sum(AB[1+j][3]), np.sum(AB[1+j][4]))

# #_________________________________________#


x, y, z, L, M, N = Pup.Pattern2Field()
Rayos = Kos.raykeeper(Doblete)


for i in range(0, len(x)):
    pSource_0 = [x[i], y[i], z[i]]
    dCos = [L[i], M[i], N[i]]
    Doblete.Trace(pSource_0, dCos, W)
    Rayos.push()


Kos.display2d(Doblete, Rayos, 0)
