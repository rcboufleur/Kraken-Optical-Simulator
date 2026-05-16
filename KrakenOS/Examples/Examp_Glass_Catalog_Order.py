#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Glass catalog loading order.

Checks how KrakenOS prioritizes and loads glass catalogs when several catalog paths are available.

What to look at:
- the catalog search order.
- how repeated glass names are resolved.
- the printed diagnostic output.

Units are the KrakenOS example defaults: distances in millimeters and
wavelengths in micrometers unless the code states otherwise.
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
import KrakenOS as Kos


def catalog_name(path):
    return os.path.basename(path)


def catalogs_containing_glass(config, glass_name):
    matches = []

    for catalog_path in config.GlassCat:
        try:
            with open(catalog_path, "r", encoding="UTF8") as catalog:
                for line in catalog:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == "NM" and parts[1] == glass_name:
                        matches.append(catalog_name(catalog_path))
                        break
        except UnicodeError:
            with open(catalog_path, "r", encoding="UTF16") as catalog:
                for line in catalog:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == "NM" and parts[1] == glass_name:
                        matches.append(catalog_name(catalog_path))
                        break

    return matches


config = Kos.Setup()

print("\nFirst loaded glass catalogs:")
for catalog_path in config.GlassCat[:10]:
    print(" -", catalog_name(catalog_path))

glass = "LAF2"
matches = catalogs_containing_glass(config, glass)

print(f"\nGlass {glass} was found in {len(matches)} loaded catalogs:")
for catalog in matches:
    print(" -", catalog)

if matches:
    print(f"\nWith the current catalog order, the first matching source is: {matches[0]}")
    print("This example does not decide which catalog is best; it only shows that order matters.")

print(
    "\nKrakenOS uses a deterministic catalog order with SCHOTT.AGF first by default, "
    "similar to Zemax catalog priority. Future improvement: add a catalog manager "
    "or GUI so users can inspect duplicate glass names and choose catalog priority explicitly."
)
