"""Example: optimization variables in a 2 m telescope.

This example marks selected surface attributes as optimization variables,
builds a merit-function wrapper around Seidel aberrations, and solves for
mirror conic constants with SciPy.

What this example teaches:
- how the `surf.Var` list identifies variables to optimize
- how to collect variable names and surface indices from a `system`
- how to update surfaces, recompute data, and restore the original system state
- how a Seidel-based merit function can be passed to `fsolve`

Expected output:
- optimized variable values printed to the console

Didactic note:
- the commented starting values for `M1.k` and `M2.k` are intentionally left in
  the file so users can compare fixed conic constants with optimized ones.

Units:
- distances are in millimeters
- wavelengths are in micrometers
"""

# !/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import matplotlib.pyplot as plt
import numpy as np


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
# M1.k = -1.077310000000000E+000
M1.Glass = "MIRROR"
M1.Diameter = 1.059E+003 * 2.0
M1.InDiameter = 250 * 2.0
M1.TiltY = 0.0
M1.TiltX = 0.0
M1.Var = ["k"]


M1.AxisMove = 0
M2 = Kos.surf()
M2.Rc = -3.93E+003
M2.Thickness = Thickness + 1037.525880
# M2.k = -4.328100000000000E+000
M2.Glass = "MIRROR"
M2.Diameter = 3.365E+002 * 2.0
M2.TiltY = 0.0
M2.TiltX = 0.0
M2.DespY = 0.0
M2.DespX = 0.0
M2.AxisMove = 0
M2.Var = ["k"]


P_Ima = Kos.surf()
P_Ima.Diameter = 300.0
P_Ima.Glass = "AIR"
P_Ima.Name = "Image plane"


A = [P_Obj, M1, M2, P_Ima]
configuracion_1 = Kos.Setup()
Telescopio = Kos.system(A, configuracion_1)


def FunVar(system):
    L0 = dir(system.SDT[0])

    VarList = []
    SurfNum = []
    num = system.n

    for Atributo in L0:
        for i in range(0,num):
            s = system.SDT[i].Var
            for ss in s:
                if ss ==Atributo:
                    VarList.append(Atributo)
                    SurfNum.append(i)
    return(VarList, SurfNum)


class FunHandl:
    def __init__(self, fun):

        """Store optimization variable names, surface indices, and values."""

        self.obj = fun.SYSTEM
        self.attr_name = ""
        self.VarList, self.SurfNum = FunVar(self.obj)
        self.Vars = np.zeros_like(self.SurfNum)
        self.n = len(self.Vars)
        self.fun = fun

    def FunVar(system):
        L0 = dir(system.SDT[0])

        VarList = []
        SurfNum = []
        num = system.n

        for Atributo in L0:
            for i in range(0,num):
                s = system.SDT[i].Var
                for ss in s:
                    if ss ==Atributo:
                        VarList.append(Atributo)
                        SurfNum.append(i)
        return(VarList, SurfNum)


    def GetAtri(self, index, attr_name):
        return getattr(self.obj.SDT[index], attr_name)

    def SetAtri(self, index, attr_name, value):
        setattr(self.obj.SDT[index], attr_name, value)


    def Fun(self, K):

        self.SetVar(K)

        R = self.fun.calculate()

        self.obj.RestoreData()

        return R

    def SetVar(self, K):
        for i in range(0, self.n):
            index = self.SurfNum[i]
            attr_name = self.VarList[i]
            value = K[i]

            # value0 = self.GetAtri(index, attr_name)
            self.SetAtri(index, attr_name, value)

        self.obj.SetData()


Surf = 1
W = 0.5016
AperVal = 2000.
AperType = "EPD"
Pupil = Kos.PupilCalc(Telescopio, Surf, W, AperType, AperVal)
Pupil.Samp = 10
Pupil.Ptype = "hexapolar"
Pupil.FieldX = 0.1
Pupil.FieldType = "angle"


AB = Kos.Seidel(Pupil)


class Aberr:
    def __init__(self, ABER):
        self.ABER = ABER
        self.SYSTEM = self.ABER.SYSTEM
    def calculate(self):
        self.ABER.calculate()
        Sph = self.ABER.SAC_TOTAL[0]
        Coma = self.ABER.SAC_TOTAL[1]
        return [Sph, Coma]


MeritFun = Aberr(AB)

MFVI = FunHandl(MeritFun)


from scipy.optimize import fsolve

root = fsolve(MFVI.Fun, MFVI.Vars)
print(root)
