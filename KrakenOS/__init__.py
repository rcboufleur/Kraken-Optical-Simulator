#!/usr/bin/env Python3
"""KrakenOS: Python exact ray-tracing and optical simulation library.

KrakenOS provides tools for building optical systems from `surf` objects and
tracing rays through them with the `system` class. It supports sequential and
non-sequential exact ray tracing, 2D and 3D visualization, glass catalogs,
Zemax-style lens catalog parsing, STL solid objects, diffraction gratings,
coatings, wavefront and Zernike analysis, Seidel sums, pupil tools, PSF/MTF
calculations, and atmospheric-optics utilities.

Typical use starts with:

    import KrakenOS as Kos

    surface = Kos.surf()
    setup = Kos.Setup()
    optical_system = Kos.system([surface], setup)

The public API is intentionally kept compatible with earlier KrakenOS examples,
where the package is commonly imported as `Kos`.

Documentation:

- README.md: installation and first examples.
- docs/README.md: documentation index and recommended reading path.
- docs/manual/README.md: modern KrakenOS manual.
- docs/capabilities.md: overview of the main capabilities in the repository.
"""


# import inspect
from .UDA import *
from .Physics import *
from .Display import *
from .PhysicsClass import *
from .MeshBlock import *
from .SurfClass import *
from .PupilTool import *
from .RayKeeper import *
from .SystemTools import *
from .SetupClass import *
from .SurfTools import surface_tools as SUT
from .Prerequisites3D import *
from .HitOnSurf import *
from .InterNormalCalc import *
from .WavefrontFit import *
from .SeidelTool import *
from .SourceRand import *
from .LibRMS import *
from .TraceLoopTool import *
from .PhaseCalc import *
from .WavePlot import *
from .KrakenSys import *
from .PSFCalc import *
from .LensCat import *
from .SurfBlockClass import *
from .PSFMap import *
from .SphericalPSFCalc import *
