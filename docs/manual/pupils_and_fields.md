# Pupils and Fields

**Manual Navigation:** [Overview](README.md) | [Installation](installation.md) | [Core Concepts](core_concepts.md) | [First System](first_optical_system.md) | [Surfaces](surfaces.md) | [Materials](materials_and_catalogs.md) | [Ray Tracing](ray_tracing_and_ray_data.md) | [Visualization](visualization.md) | [Pupils](pupils_and_fields.md) | [Analysis](optical_analysis.md) | [Advanced](advanced_workflows.md) | [API](api_quick_reference.md)

Previous: [Visualization](visualization.md) | Next: [Optical Analysis](optical_analysis.md)

---

`PupilCalc` generates ray origins and direction cosines from a stop surface,
aperture definition, sampling pattern, and field definition.

## Basic Pattern

```python
pupil = Kos.PupilCalc(system, Surf=1, W=0.55, AperType="EPD", AperVal=20.0)
pupil.Samp = 5
pupil.Ptype = "hexapolar"
pupil.FieldType = "angle"
pupil.FieldX = 0.0
pupil.FieldY = 0.0

x, y, z, l, m, n = pupil.Pattern2Field()
```

The returned arrays can be traced in a loop or with `Kos.TraceLoop`:

```python
rays = Kos.raykeeper(system)
Kos.TraceLoop(x, y, z, l, m, n, 0.55, rays, clean=1)
```

![Pupil-generated ray bundle](../assets/examples/Examp_Doublet_Lens_Pupil_2d.png)

The pupil sampler defines ray origins and direction cosines before tracing.
The resulting bundle should fill the intended aperture and converge according
to the optical system.

## Common Aperture and Pattern Ideas

Typical pupil workflows define:

- the stop surface index
- wavelength
- aperture type, such as entrance pupil diameter
- aperture value
- field type and field coordinates
- sampling pattern

Common patterns include fans, rectangular grids, and hexapolar sampling. Use
small sample counts while learning, then increase sampling for analysis.

![Hexapolar spot diagram](assets/legacy_hexapolar_spot_diagram.png)

## Atmospheric Refraction

KrakenOS includes atmospheric tools through the `AstroAtmosphere` package and
telescope examples. These workflows are advanced because they combine wavelength
selection, field definition, observatory parameters, and telescope geometry.

Recommended examples:

- [`Examp_Doublet_Lens_Pupil.py`](../../KrakenOS/Examples/Examp_Doublet_Lens_Pupil.py)
- [`Examp_Tel_2M_Pupila.py`](../../KrakenOS/Examples/Examp_Tel_2M_Pupila.py)
- [`Examp_Tel_2M_Atmospheric_Refraction_Corrector_Static.py`](../../KrakenOS/Examples/Examp_Tel_2M_Atmospheric_Refraction_Corrector_Static.py)
- [`Examp_Tel_2M_Atmospheric_Refraction_Corrector_Adaptable.py`](../../KrakenOS/Examples/Examp_Tel_2M_Atmospheric_Refraction_Corrector_Adaptable.py)
