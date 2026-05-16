# KrakenOS Manual

**Manual Navigation:** [Overview](README.md) | [Installation](installation.md) | [Core Concepts](core_concepts.md) | [First System](first_optical_system.md) | [Surfaces](surfaces.md) | [Materials](materials_and_catalogs.md) | [Ray Tracing](ray_tracing_and_ray_data.md) | [Visualization](visualization.md) | [Pupils](pupils_and_fields.md) | [Analysis](optical_analysis.md) | [Advanced](advanced_workflows.md) | [API](api_quick_reference.md)

---

This is the primary learning manual for KrakenOS. It is written for users who
want to build optical systems, trace rays, inspect results, and move gradually
from simple sequential examples to advanced 3D, catalog, and instrument-level
workflows.

KrakenOS represents an optical system with two central ideas:

- `surf`: one optical interface, plane, stop, mirror, lens surface, grating,
  solid object, coordinate transform, or analysis plane.
- `system`: an ordered collection of surfaces plus the tracing and analysis
  methods that act on them.

The recommended learning path is:

1. [Installation](installation.md)
2. [Core Concepts](core_concepts.md)
3. [First Optical System](first_optical_system.md)
4. [Surfaces](surfaces.md)
5. [Materials and Catalogs](materials_and_catalogs.md)
6. [Ray Tracing and Ray Data](ray_tracing_and_ray_data.md)
7. [Visualization](visualization.md)
8. [Pupils and Fields](pupils_and_fields.md)
9. [Optical Analysis](optical_analysis.md)
10. [Advanced Workflows](advanced_workflows.md)
11. [API Quick Reference](api_quick_reference.md)

For runnable scripts, use the [Example Guide](../examples.md). For the visual
appendix generated from example docstrings, use the
[Generated Examples Appendix](../examples_manual.md). For the full documentation
map, see [KrakenOS Documentation](../README.md).

Selected historical figures have been migrated into this manual where they
still explain current KrakenOS concepts. New generated figures are used where
they better match the current examples and package behavior.
