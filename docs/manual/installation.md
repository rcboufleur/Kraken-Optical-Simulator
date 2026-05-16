# Installation

**Manual Navigation:** [Overview](README.md) | [Installation](installation.md) | [Core Concepts](core_concepts.md) | [First System](first_optical_system.md) | [Surfaces](surfaces.md) | [Materials](materials_and_catalogs.md) | [Ray Tracing](ray_tracing_and_ray_data.md) | [Visualization](visualization.md) | [Pupils](pupils_and_fields.md) | [Analysis](optical_analysis.md) | [Advanced](advanced_workflows.md) | [API](api_quick_reference.md)

Previous: [Overview](README.md) | Next: [Core Concepts](core_concepts.md)

---

For regular use, install KrakenOS from PyPI:

```bash
python -m pip install KrakenOS
```

For development from a cloned repository, install it in editable mode from the
repository root:

```bash
python -m pip install -e .
```

Editable installation is the recommended mode when you are modifying examples,
documentation, packaging, or KrakenOS source files. It makes Python import the
local working copy instead of a separate installed copy.

To verify the active import:

```python
import KrakenOS as Kos

print(Kos.__file__)
print(Kos.surf())
```

The printed path should point to the repository you intend to use. If it points
to another directory, reinstall from the correct repository root with
`python -m pip install -e .`.

## Running Examples

Most examples can be run from the repository root:

```bash
python KrakenOS/Examples/Examp_Ray.py
```

Some advanced examples open interactive 3D windows, use larger data files, or
depend on graphics backends. Beginner examples are listed in the
[Example Guide](../examples.md).

## Regenerating Documentation Images

The generated examples manual can create its own curated 2D and 3D figures:

```bash
python tools/generate_example_images.py --all
```

This command updates `docs/assets/examples/` and regenerates
`docs/examples_manual.md`.
