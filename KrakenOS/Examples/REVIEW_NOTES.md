# Editorial Review Notes

This cleaned copy applies a documentation-focused pass to the original examples.

## What changed

- Rewrote or added module docstrings for all 62 Python examples.
- Removed decorative separator comments that did not explain the code.
- Replaced Spanish image-plane labels such as `Plano imagen` with `Image plane`.
- Added `README.md`, `STYLE_GUIDE.md`, and `EXAMPLES_INDEX.md`.
- Kept the original file names to avoid breaking existing references.

## What did not change

- Optical constants were not changed.
- Surface order was not changed.
- Ray-tracing calls were not changed.
- External data files and STL files were left in place.
- Variable names were left mostly untouched to avoid introducing accidental bugs.

## Suggested next pass

Once the examples are tested, a second pass could safely rename variables such as
`Doblete`, `Rayos`, and `configuracion_1` to English names.  That should be done
with execution tests, because those names are used throughout each script.
