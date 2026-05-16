# KrakenOS Example Coverage Roadmap

This roadmap compares the current KrakenOS capabilities with the example set.
It is meant to guide future example work without changing the historical
example filenames.

## Well Covered

These areas already have useful examples and mostly need small maintenance over
time:

| Area | Current coverage |
| --- | --- |
| Basic sequential ray tracing | `Examp_Ray.py`, `Examp_Doublet_Lens.py` |
| Pupil-based ray generation | `Examp_Doublet_Lens_Pupil.py`, `Examp_Tel_2M_Pupila.py` |
| 2D and 3D visualization | `Examp_Doublet_Lens_3Dcolor.py`, `Examp_Tel_2M.py` |
| Tilted and decentered components | `Examp_Doublet_Lens_Tilt.py`, `Examp_Doublet_Lens_Tilt_non_sec.py` |
| Axicons, cylinders, Zernike surfaces, and custom shapes | `Examp_Axicon.py`, `Examp_Doublet_Lens_Cylinder.py`, `Examp_Doublet_Lens_Zernike.py`, `Examp_ExtraShape_*` |
| Diffraction gratings and spectrograph layouts | `Examp_Diffraction_Grating_*`, `Examp_CzernyTurner.py`, `Examp_Tel_2M_Echelle.py` |
| STL and solid-object tracing | `Examp_Prism_STL.py`, `Examp_Solid_Object_STL.py`, `Examp_Tel_2M-STL_ImageSlicer.py` |
| Telescope-level workflows | `Examp_Tel_2M*.py` |
| Atmospheric refraction correction | `Examp_Tel_2M_Atmospheric_Refraction_Corrector_*.py` |

## Partly Covered

These features exist and have examples, but the examples are either advanced,
large, or not ideal as first-contact tutorials:

| Area | Current state | Suggested improvement |
| --- | --- | --- |
| Coating tables and energy behavior | Covered in non-sequential examples, but mixed with tilted geometry or STL cases. | Add one small coating-only tutorial that prints/plots reflected and transmitted energy. |
| Metal coatings and polarization terms | `Examp_Sphere.py` loads `Gold.csv` and prints S/P reflection values. | Add a clearer metal-mirror example that compares dielectric mirror behavior with metal data. |
| PSF and MTF | PSF is shown through wavefront examples. MTF helpers exist in `PSFCalc.py`. | Add a compact `Examp_PSF_MTF_From_Zernike.py`. |
| RMS and best-focus tools | `Examp_RMS_BestFocus.py` now shows `Kos.RMS` and RMS minimization in a compact example. | Consider adding a deeper API note if `Kos.BestFocus` is revised in the future. |
| Zemax lens catalog conversion | Covered by the Spruce-tone user example. | Add a shorter lens-catalog example using one packaged ZMF entry and showing the converted surfaces. |
| Reverse tracing | `system.RvTrace` exists, but there is no obvious beginner example. | Add a minimal reverse-trace example from image plane back toward the object space. |
| Fast tracing | `FastTrace` exists in the system class, but is not presented as a workflow. | Add a performance-oriented example only after confirming the intended public API. |
| `SurfBlock` reusable assemblies | `SurfBlockClass.py` exposes reusable lens blocks. | Add a small example that builds, aligns, and reuses a lens block. |

## Missing First-Contact Examples

These are the best candidates for new examples because they would teach common
tasks in a focused way:

1. `Examp_RMS_BestFocus.py` - added

   Purpose: show how to trace a compact ray bundle, extract image-plane rays,
   calculate RMS, move to best focus, and report before/after RMS.

2. `Examp_PSF_MTF_From_Zernike.py`

   Purpose: show how to use a simple Zernike coefficient vector with the PSF
   and MTF helpers, independent of a large telescope model.

3. `Examp_Coating_Energy_Basics.py`

   Purpose: show the coating table format, trace one or a few rays, and inspect
   the resulting reflected/transmitted energy terms.

4. `Examp_Lens_Catalog_Basics.py`

   Purpose: load a packaged Zemax-style catalog file, list a few available lens
   entries, convert one entry to KrakenOS surfaces, and display the result.

5. `Examp_Reverse_Trace.py`

   Purpose: demonstrate `RvTrace` in a tiny system so users understand when
   reverse tracing is useful.

## Documentation Improvements Before Adding Many Examples

- Keep current historical example filenames stable for compatibility.
- Add aliases or new clean filenames only when the old names are confusing
  enough to hurt new users.
- Prefer short examples that teach one idea at a time.
- Put large instrument examples after basic examples in guides.
- Mark deliberately commented blocks with `Optional didactic ...` comments.
- Avoid requiring heavy data files for beginner examples.

## Suggested Next Batch

The next practical batch should add:

1. `Examp_PSF_MTF_From_Zernike.py`
2. `Examp_Coating_Energy_Basics.py`
3. `Examp_Lens_Catalog_Basics.py`

Then update:

- `docs/examples.md`
- `KrakenOS/Examples/README.md`
- `KrakenOS/Examples/EXAMPLES_INDEX.md`
- `tests/test_smoke.py` if the new examples add resources or important import
  assumptions
