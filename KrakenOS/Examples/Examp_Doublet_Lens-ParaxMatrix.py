#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: inspect the paraxial matrix of a doublet lens.

This example computes the paraxial matrix of a doublet, changes the first
surface curvature, updates the system data, and recomputes the effective focal
length.

What this example teaches:
- how to call `system.Parax`
- which values are returned by the paraxial calculation
- why `SetData` is needed after changing a surface parameter

Expected output:
- several effective focal length values as the curvature is changed
- the final paraxial matrices and related first-order quantities

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

import time


import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos

start_time = time.time()


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
P_Ima.Diameter = 3.0
P_Ima.Name = "Image plane"


A = [P_Obj, L1a, L1b, L1c, P_Ima]
config_1 = Kos.Setup()


Doblete = Kos.system(A, config_1)
Prx = Doblete.Parax(0.4)
SistemMatrix, S_Matrix, N_Matrix, a, b, c, d, EFFL, PPA, PPP, CC, N_Prec, DD = Prx
print(EFFL)


L1a.Rc = L1a.Rc + 1
Doblete.SetData()
Prx = Doblete.Parax(0.4)
SistemMatrix, S_Matrix, N_Matrix, a, b, c, d, EFFL, PPA, PPP, CC, N_Prec, DD = Prx
print(EFFL)


L1a.Rc = L1a.Rc + 1
Doblete.SetData()
Prx = Doblete.Parax(0.4)
SistemMatrix, S_Matrix, N_Matrix, a, b, c, d, EFFL, PPA, PPP, CC, N_Prec, DD = Prx
print(EFFL)


L1a.Rc = L1a.Rc + 1
Doblete.SetData()
Prx = Doblete.Parax(0.4)
SistemMatrix, S_Matrix, N_Matrix, a, b, c, d, EFFL, PPA, PPP, CC, N_Prec, DD = Prx
print(EFFL)

print("=======================================")

print(SistemMatrix)
print(S_Matrix)
print( N_Matrix)
print( a)
print( b )
print( c)
print( d)
print( EFFL)
print( PPA)
print( PPP)
print( CC)
print( N_Prec)
print( DD)
