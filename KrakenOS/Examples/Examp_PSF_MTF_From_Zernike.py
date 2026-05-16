#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example: PSF and MTF from Zernike coefficients.

This example calculates a diffraction PSF and an MTF array directly from a
small vector of Zernike coefficients. It does not build a full optical system;
that keeps the example focused on the analysis helpers in `PSFCalc.py`.

What this example teaches:
- how to represent a wavefront with a Zernike coefficient vector
- how to call `Kos.psf` without opening a plot
- how to call `Kos.calculate_mtf`
- how to extract simple scalar diagnostics from the PSF and MTF arrays

Expected output:
- normalized PSF peak for an ideal wavefront
- normalized PSF peak for a mildly aberrated wavefront
- MTF value near the center and at an off-axis sample point

Didactic note:
- plotting calls are intentionally commented. Uncomment them if you want to
  inspect the PSF image or MTF curves interactively.

Units:
- focal length and aperture diameter are in millimeters
- wavelength is in micrometers
- Zernike coefficients are expressed in waves
"""

import sys
from pathlib import Path

import numpy as np


sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos


def normalized_peak(psf_image):
    """Return the PSF peak after normalizing total energy to one."""
    return np.max(psf_image / np.sum(psf_image))


focal_length = 100.0
diameter = 20.0
wavelength = 0.55

# `Kos.psf` expects the evaluated wavefront to be an array. A tiny piston term
# keeps the ideal reference numerically array-like without changing the PSF in a
# meaningful way.
ideal_coefficients = np.zeros(12)
ideal_coefficients[0] = 1e-12

aberrated_coefficients = np.zeros(12)
aberrated_coefficients[4] = 0.10   # A small defocus-like term in Noll order.
aberrated_coefficients[5] = 0.03   # A small astigmatism-like term.

ideal_psf = Kos.psf(
    ideal_coefficients,
    focal_length,
    diameter,
    wavelength,
    pixels=128,
    PupilSample=4,
    plot=0,
)
aberrated_psf = Kos.psf(
    aberrated_coefficients,
    focal_length,
    diameter,
    wavelength,
    pixels=128,
    PupilSample=4,
    plot=0,
)

ideal_peak = normalized_peak(ideal_psf)
aberrated_peak = normalized_peak(aberrated_psf)

mtf = Kos.calculate_mtf(
    aberrated_coefficients,
    focal_length,
    diameter,
    wavelength,
)
center = mtf.shape[0] // 2
mtf_center = mtf[center, center]
mtf_sample = mtf[center, center + 50]

print("Ideal normalized PSF peak:", f"{ideal_peak:.6f}")
print("Aberrated normalized PSF peak:", f"{aberrated_peak:.6f}")
print("Peak ratio aberrated/ideal:", f"{aberrated_peak / ideal_peak:.6f}")
print("MTF at zero spatial frequency:", f"{mtf_center:.6f}")
print("MTF sample 50 pixels from center:", f"{mtf_sample:.6f}")

# Optional didactic plots:
# import matplotlib.pyplot as plt
# plt.figure("Aberrated PSF")
# plt.imshow(aberrated_psf, cmap=plt.cm.bone)
# plt.colorbar()
# Kos.plot_mtf(mtf, diameter, wavelength)
# plt.show()
