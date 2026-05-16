"""Example: 2 m telescope wavefront fitting.

This example computes a wavefront phase over the telescope pupil, fits Zernike
coefficients to that phase, and uses those coefficients to generate a PSF.

What this example teaches:
- how `Phase2` samples the wavefront over a configured pupil
- how `Zernike_Fitting` returns coefficients, notation, RMS terms, and fit error
- how fitted wavefront coefficients can be sent to `psf`

Expected output:
- printed pupil and Zernike fitting information
- a PSF plot from the fitted coefficients

Didactic note:
- the long ray-tracing and interferogram block near the end is intentionally
  commented. It is an optional exploration path for comparing wavefront fitting
  with traced spot diagrams and interferogram-style plots.

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
P_Obj.Thickness = 1000*0 + 3452.2
P_Obj.Glass = "AIR"
P_Obj.Diameter = 1059. * 2.0
P_Obj.Drawing=0


Thickness = 3452.2
M1 = Kos.surf()
M1.Rc = -9638.0
M1.Thickness = -Thickness
M1.k = -1.07731
M1.Glass = "MIRROR"
M1.Diameter = 1.059E+003 * 2.0
M1.InDiameter = 250 * 2.0
M1.TiltY = 0.0
M1.TiltX = 0.0
M1.AxisMove = 0

M2 = Kos.surf()
M2.Rc = -3930.0
M2.Thickness = Thickness + 1037.525880
M2.k = -4.3281
M2.Glass = "MIRROR"
M2.Diameter = 336.5 * 2.0
M2.TiltY = 0.0
M2.TiltX = 0.0
M2.DespY = 0.0
# Secondary mirror tilt/decenter parameters can be changed here.
M2.DespX = 0.0
M2.AxisMove = 0


P_Ima = Kos.surf()
P_Ima.Diameter = 300.0
P_Ima.Glass = "AIR"
P_Ima.Name = "Image plane"


A = [P_Obj, M1, M2, P_Ima]
configuracion_1 = Kos.Setup()
Telescopio = Kos.system(A, configuracion_1)

# Define the system pupil on surface 1, corresponding to the primary mirror.
Surf = 1

# Wavelength in micrometers.
W = 0.50169

# The system aperture defines the pupil.
AperType = "EPD"

# Aperture diameter.
AperVal = 2000.
Pupil = Kos.PupilCalc(Telescopio, Surf, W, AperType, AperVal)


print("Input pupil radius:")
print(Pupil.RadPupInp)
print("Input pupil position:")
print(Pupil.PosPupInp)
print("Output pupil radius:")
print(Pupil.RadPupOut)
print("Output pupil position:")
print(Pupil.PosPupOut)
print("Output pupil position relative to focal plane:")
print(Pupil.PosPupOutFoc)
print("Output pupil orientation:")
print(Pupil.DirPupSal)

print("Airy disk radius focal distance (micrometers)")
print(Pupil.FocusAiryRadius)


print("Effective focal length")
print(Pupil.EFFL)


# Use a hexapolar sampling pattern for the internal wavefront phase calculation.
Pupil.Samp = 11
Pupil.Ptype = "hexapolar"

# Telescope fields are defined as angles for light arriving from infinity.
Pupil.FieldType = "angle"

# On-axis field.
Pupil.FieldX = 0.0
Pupil.FieldY = 0.0


# Calculate the wavefront phase on the pupil. X and Y are pupil coordinates,
# Z is the phase at each point, and P2V is the peak-to-valley value.
X, Y, Z, P2V = Kos.Phase2(Pupil)
print("Peak to valley: ", P2V)


# Number of Zernike terms to report.
NC = 15

# Request array for the Zernike expansion.
A = np.ones(NC)

# Fit Zernike polynomials to the calculated wavefront phase.
Zcoef, Mat, RMS2Chief, RMS2Centroid, FITTINGERROR = Kos.Zernike_Fitting(X, Y, Z, A)

# Print the fitted coefficients.
for i in range(0, NC):
    print("z", i + 1, "  ", "{0:.8f}".format(float(Zcoef[i])), ":", Mat[i])


print("(RMS) Fitting error: ", FITTINGERROR)
print(RMS2Chief, "RMS(to chief) From fitted coefficents")
print(RMS2Centroid, "RMS(to centroid) From fitted coefficents")


COEF = Zcoef
Focal = Pupil.EFFL
Diameter = 2.0 * Pupil.RadPupInp
Wave = W
I= Kos.psf(COEF, Focal, Diameter, Wave,pixels=265, plot=1, sqr = 1)

# Optional didactic ray-tracing and interferogram exploration:
# Uncomment this block to compare the fitted wavefront with traced rays,
# spot diagrams, RMS values, and an interferogram-style plot.

# """Se genera un contenedor de rayos"""

# RR = Kos.raykeeper(Telescopio)

# """Generate rays through the previously configured pupil."""
# x, y, z, L, M, N = Pupil.Pattern2Field()

# # ______________________________________#

# """ Se trazan esos rayos y se almacenan"""

# for i in range(0, len(x)):
#     pSource_0 = [x[i], y[i], z[i]]
#     dCos = [L[i], M[i], N[i]]
#     Telescopio.Trace(pSource_0, dCos, W)
#     RR.push()

# # ______________________________________#

# """ Se grafica el telescopio con los rayos almacenados"""

# Kos.display3d(Telescopio, RR, 1 )
# X, Y, Z, L, M, N = RR.pick(-1)

# # ______________________________________#

# """ Se grafica el diagrama de manchas """
# plt.figure(2)
# plt.plot(X, Y, 'x')
# plt.xlabel('X')
# plt.ylabel('Y')
# plt.title('spot Diagram')
# plt.axis('square')

# K = .100
# Lx = np.mean(X)
# Ly = np.mean(Y)
# left = (-K) + Lx
# right = (K) + Lx
# up = (K) + Ly
# down = (-K) + Ly

# plt.xlim([left, right])
# plt.ylim([up, down])


# plt.show()


# X = X - np.mean(X)
# Y = Y - np.mean(Y)

# R=np.sqrt(X**2 + Y**2)
# RMS = np.sqrt(np.mean(R**2))
# print("RMS Radius(mm): ", RMS)

# """ Se prepara una imagen con los coeficientes de 400x400"""
# # Zcoef[0]=0.
# # Zcoef[1]=0.
# # Zcoef[2]=0.
# ima = Kos.WavefrontData2Image(Zcoef, 400)

# print("Peak 2 valley. ", np.max(ima)-np.min(ima))


# """ Se grafica el interferograma """
# Type = "interferogram"

# # ima = np.flipud(ima)
# Kos.ZernikeDataImage2Plot(ima, Type)


# # """ Se calculan las sumas de Seidel """
# # AB = Kos.Seidel(Pupil)

# # print("--------------------------------------")
# # print(AB.SCW_AN)
# # print(AB.SCW_NM)
# # print(AB.SCW_TOTAL)
