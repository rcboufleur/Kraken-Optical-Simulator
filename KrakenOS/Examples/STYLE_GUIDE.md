# Example Style Guide

These examples are meant to teach KrakenOS by showing complete, runnable cases.
Keep them direct and technical.

## Good example structure

Each script should have:

1. A short module docstring with the purpose of the example.
2. A short list of things the reader should notice.
3. Any required local files, if the script depends on them.
4. A compact surface definition section.
5. A ray-tracing section.
6. A plotting or diagnostic section.

## Writing style

- Use clear English comments and docstrings.
- Explain optical choices, not obvious Python syntax.
- Avoid decorative separators made only of underscores or equal signs.
- Prefer short comments near the code they explain.
- State units when they are not obvious.
- Keep variable names stable unless you are also testing the example.

## What not to do

Avoid comments like:

```python
A.append(surface)  # append surface
```

They repeat the code and do not help the reader.  Prefer comments like:

```python
# Keep the image plane as the last surface so spot data are collected there.
A.append(image_plane)
```

## Compatibility note

This documentation pass intentionally avoids changing optical constants,
coordinate signs, tracing calls, or surface order.  Those should only be edited
when a test case is being deliberately redesigned.
