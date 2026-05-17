
import numpy as np
import pyvista as pv
import matplotlib.pyplot as plt
# plt.rcParams["font.family"] = "Times New Roman"
import sys
from matplotlib import rc
from typing import Tuple, Optional, List
from dataclasses import dataclass

import matplotlib.pyplot as plt

def set_krakenos_fonts():
    """
    Fuerza una tipografía tipo Times si existe,
    pero sin warnings si no está instalada (Colab/Linux).
    """
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = [
        "Times New Roman",  # Windows/mac a veces
        "Times",            # alternativa
        "STIXGeneral",      # muy común en entornos científicos
        "DejaVu Serif",     # siempre existe en matplotlib/colab
    ]
    plt.rcParams["mathtext.fontset"] = "stix"

set_krakenos_fonts()


# =============================================================================
# Shared display options and helpers
# =============================================================================

@dataclass
class Display2DOptions:
    """Options used by display2d() and display2d_interactive()."""

    view: int = 0
    arrow: float = 0
    nrays: int = 0
    figsize: Tuple[float, float] = (10, 4)
    fs: int = 11
    show_surfaces: bool = True
    show_rays: bool = True
    equal_axis: bool = True
    grid: bool = False
    title: str = "System Plot"
    surface_line_width: float = 0.5
    ray_line_width: float = 0.5


@dataclass
class Display3DOptions:
    """Options used by display3d() and display3d_interactive()."""

    view: int = 0
    inline: bool = False
    background: str = "white"
    background_top: str = "white"
    grid_color: str = "black"
    nrays: int = 0
    opacity: float = 0.99
    ray_width: float = 1.0
    show_surfaces: bool = True
    show_rays: bool = True
    show_edges: bool = True
    show_masks: bool = True
    show_sides: bool = True
    show_grid: bool = True
    show_axes: bool = True
    text: str = "KrakenOS"
    window_size: Tuple[int, int] = (1200, 800)


def _as_list(value):
    """Return value as a list, preserving existing list inputs."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _empty_polydata():
    """Small empty mesh used as a safe merge seed for PyVista operations."""
    return pv.PolyData(np.array([[0.0, 0.0, 0.0]]), force_float=False)


def ensure_display_geometry(system):
    """Build full display geometry on demand.

    KrakenOS systems may be created with build=0 for lightweight sequential
    tracing. Display functions require the full geometry blocks (AAA, BBB, DDD),
    so this helper temporarily rebuilds with BUILD=1 and restores the previous
    BUILD value afterwards.
    """
    for sys_ in _as_list(system):
        try:
            pr3d = getattr(sys_, "Pr3D", None)
            if pr3d is not None and getattr(pr3d, "ExistSolid", 1) == 0:
                previous_build = getattr(sys_, "BUILD", None)
                try:
                    sys_.BUILD = 1
                    sys_.build()
                finally:
                    if previous_build is not None:
                        sys_.BUILD = previous_build
        except Exception:
            # Display should not fail here for partially initialized objects.
            # The actual plotting call will expose missing attributes if needed.
            pass


def _surface_display_color(surface):
    """Return the default display color for a KrakenOS surface."""
    absorb_color = np.array([(10 / 256), (23 / 256), (24 / 256)])
    mirror_color = np.array([(189 / 256), (189 / 256), (189 / 256)])
    glass_color = np.array([12 / 256, 238 / 256, 246 / 256])

    if surface.Color != [0, 0, 0]:
        return surface.Color
    if surface.Glass == "MIRROR":
        return mirror_color
    if surface.Glass == "ABSORB":
        return absorb_color
    return glass_color


def _safe_ray_count(ray_container, nrays=0):
    """Return the number of rays to draw, clamped to available ray data."""
    if not hasattr(ray_container, "RayWave") or len(ray_container.RayWave) == 0:
        return 0
    total = int(np.shape(np.asarray(ray_container.RayWave))[0])
    if nrays == 0:
        return total
    return min(int(nrays), total)



def rgba2rgb(rgba, background=[255, 255, 255]):
    return (
        ((1 - rgba[3]) * background[0]) + (rgba[3] * rgba[0]),
        ((1 - rgba[3]) * background[1]) + (rgba[3] * rgba[1]),
        ((1 - rgba[3]) * background[2]) + (rgba[3] * rgba[2]),
    )

def get_cmap(n, name='hot', show_colors=False):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    if show_colors:
        print(plt.cm.datad.keys())
    return plt.cm.get_cmap(name, n)

def add_arrow(line, position=None, direction='right', size=15, color=None):
    """
    add an arrow to a line.

    line:       Line2D object
    position:   x-position of the arrow. If None, mean of xdata is taken
    direction:  'left' or 'right'
    size:       size of the arrow in fontsize points
    color:      if None, line color is taken.
    """
    if color is None:
        color = line.get_color()

    xdata = line.get_xdata()
    ydata = line.get_ydata()

    if position is None:
        position = xdata.mean()
    # find closest index
    start_ind = 0
    if direction == 'right':
        end_ind = start_ind + 1
    else:
        end_ind = start_ind - 1

    Px = xdata[end_ind] - (xdata[end_ind] - xdata[start_ind]) / 2.0
    Py = ydata[end_ind] - (ydata[end_ind] - ydata[start_ind]) / 2.0
    PPx = xdata[start_ind] + (xdata[end_ind] - xdata[start_ind]) / 2.01
    PPy = ydata[start_ind] + (ydata[end_ind] - ydata[start_ind]) / 2.01
    line.axes.annotate('',
        xytext=(PPx,PPy),
        xy=(Px, Py),
        arrowprops=dict(arrowstyle="->", color=color),
        size=size)

###############################################################################

def wavelength_to_rgb(wavelength, gamma=1.0):
    """wavelength_to_rgb.

    Parameters
    ----------
    wavelength :
        wavelength
    gamma :
        gamma
    """
    wavelength = float(wavelength)
    if (380 <= wavelength <= 440):
        attenuation = (0.3 + ((0.7 * (wavelength - 380)) / (440 - 380)))
        R = ((((- (wavelength - 440)) / (440 - 380)) * attenuation) ** gamma)
        G = 0.0
        B = ((1.0 * attenuation) ** gamma)
    elif (440 <= wavelength <= 490):
        R = 0.0
        G = (((wavelength - 440) / (490 - 440)) ** gamma)
        B = 1.0
    elif (490 <= wavelength <= 510):
        R = 0.0
        G = 1.0
        B = (((- (wavelength - 510)) / (510 - 490)) ** gamma)
    elif (510 <= wavelength <= 580):
        R = (((wavelength - 510) / (580 - 510)) ** gamma)
        G = 1.0
        B = 0.0
    elif (580 <= wavelength <= 645):
        R = 1.0
        G = (((- (wavelength - 645)) / (645 - 580)) ** gamma)
        B = 0.0
    elif (645 <= wavelength <= 750):
        attenuation = (0.3 + ((0.7 * (750 - wavelength)) / (750 - 645)))
        R = ((1.0 * attenuation) ** gamma)
        G = 0.0
        B = 0.0
    else:
        R = 0.0
        G = 0.0
        B = 0.0
    R *= 255
    G *= 255
    B *= 255
    return [(int(R) / 255.0), (int(G) / 255.0), (int(B) / 255.0)]

###############################################################################

def _add_mesh_or_blocks(plotter, mesh, **kwargs):
    if mesh is None or (isinstance(mesh, str) and mesh == "None"):
        return

    try:
        plotter.add_mesh(mesh, **kwargs)
        return
    except (TypeError, NotImplementedError):
        pass

    for block in mesh:
        _add_mesh_or_blocks(plotter, block, **kwargs)


def _ray_points_to_polyline(points):
    return pv.lines_from_points(np.asarray(points))


###############################################################################

def display3d_old(SYSTEM, RAYS, view=0, inline=False,     BackgCol= 'white', BackgColTop = 'white', GridCol="black"):

    """display3d.

    Parameters
    ----------
    SYSTEM :
        SYSTEM
    RAYS :
        RAYS
    view :
        view
    """

    ST1="KrakenOS v0.1. Executing Script: " + sys.argv[0]
    OPA = 0.95

    CCC = []
    INST = isinstance(RAYS, list)
    if INST == True:
        for R in RAYS:
            for rays in R.CC:
                CCC.append(_ray_points_to_polyline(rays))
    else:
        for rays in RAYS.CC:
            CCC.append(_ray_points_to_polyline(rays))


    p = pv.Plotter(shape=(1, 1), title=ST1,notebook=inline)
    Absorb_color = np.array([(10 / 256), (23 / 256), (24 / 256)])
    Mirror_color = np.array([(189 / 256), (189 / 256), (189 / 256)])
    Glass_color=np.array([12/256, 238/256, 246/256])
    recorte = view
    NN = SYSTEM.AAA.n_blocks
    if (SYSTEM.SDT_0[0].Drawing == 0):
        points2 = np.c_[0.0, 0.0, 0.0]
        c = pv.PolyData(points2)
        cc = pv.PolyData(points2)
    if (SYSTEM.SDT_0[0].Drawing == 1):
        c = SYSTEM.AAA[0]
        cc = SYSTEM.AAA[0]
    for n in range(1, NN):
        if (SYSTEM.SDT_0[n].Drawing == 1):
            AAAA = SYSTEM.AAA[n]
            if (SYSTEM.SDT_0[n].Glass != 'NULL'):
                if (SYSTEM.SDT_0[n].Color == [0, 0, 0]):
                    if (SYSTEM.SDT_0[n].Glass == 'MIRROR'):
                        color = Mirror_color
                    else:
                        color = Glass_color
                    if (SYSTEM.SDT_0[n].Glass == 'ABSORB'):
                        color = Absorb_color
                else:
                    color = SYSTEM.SDT_0[n].Color
                cc = cc.merge(AAAA)
                if (recorte == 1):
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, 1, 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip(((- 1), 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (- 1), 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (- 1), 0), invert=False)
                    c = c.merge(clippedy)
                if (recorte == 0):
                    c = cc
                if (recorte == 2):
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    c = c.merge(clippedx)
                p.add_mesh(c, color, opacity=OPA, specular=1, specular_power=15, smooth_shading=True, show_edges=False)
                edges = c.extract_feature_edges(feature_angle=10, boundary_edges=True, feature_edges=False, manifold_edges=False)
                if SYSTEM.SDT_0[n].Solid_3d_stl != "None" and recorte ==0:
                    print(" ") # No edges
                else:
                    p.add_mesh(edges, 'red')
                points2 = np.c_[0.0, 0.0, 0.0]
                c = pv.PolyData(points2)
    _add_mesh_or_blocks(p, SYSTEM.DDD, color=[0.5, 0.5, 0.5], opacity=OPA, show_edges=None)
    NN = SYSTEM.AAA.n_blocks
    n = 0
    for g in SYSTEM.side_number:
        if (SYSTEM.SDT_0[g].Drawing == 1):
            if (SYSTEM.SDT_0[g].Color == [0, 0, 0]):
                if (SYSTEM.SDT_0[g].Glass == 'MIRROR'):
                    LL_color = Mirror_color
                else:
                    LL_color = Glass_color
                if (SYSTEM.SDT_0[g].Glass == 'ABSORB'):
                    LL_color = Absorb_color
                color = LL_color
            else:
                color = SYSTEM.SDT_0[g].Color
            if (recorte == 1):
                clippedx = SYSTEM.BBB[n].clip('x', invert=False)
                p.add_mesh(clippedx, color ,opacity=OPA, smooth_shading=True, show_edges=None)
                clippedy = SYSTEM.BBB[n].clip('-y', invert=False)
                p.add_mesh(clippedy, color,opacity=OPA, smooth_shading=True, show_edges=None)
            if (recorte == 0):
                No_clipped = SYSTEM.BBB[n]
                p.add_mesh(No_clipped, color,opacity=OPA, smooth_shading=False, show_edges=None)
            if (recorte == 2):
                BBBB = SYSTEM.BBB[n]
                clippedx = BBBB.clip((1, 0, 0), invert=False)
                p.add_mesh(clippedx, color,opacity=OPA, smooth_shading=True, show_edges=None)
        n = (n + 1)

    if INST == True:
       for R in RAYS:
            if (len(R.RayWave) != 0):
                RW = np.asarray(R.RayWave)
                for i in range(0, np.shape(RW)[0]):
                    RGB = wavelength_to_rgb((RW[i] * 1000.0))
                    p.add_mesh(CCC[i], color=RGB, opacity=OPA, smooth_shading=True, line_width=1.0, show_edges=None)

    else:
        if (len(RAYS.RayWave) != 0):
            RW = np.asarray(RAYS.RayWave)
            for i in range(0, np.shape(RW)[0]):
                RGB = wavelength_to_rgb((RW[i] * 1000.0))
                p.add_mesh(CCC[i], color=RGB, opacity=OPA, smooth_shading=True, line_width=1.0, show_edges=None)

    p.add_axes(line_width=4)

    [cx,cy,cz]=p.center
    p.set_focus([cx,cy,cz])
    p.camera_position=[-1.0, 0.5, 1.0]

    p.set_viewup([0, 1.0, 0])
    p.enable_anti_aliasing()
    p.enable_eye_dome_lighting()
    p.disable_eye_dome_lighting()
    p.set_background(BackgCol, top=BackgColTop)

    p.add_text('KrakenOS',position="upper_left" ,font_size=20,color="royalblue")
    p.show_grid(font_size=6,color=GridCol)
    p.show(auto_close=False, interactive=True, interactive_update=False)

    [cpx,cpy,cpz]=p.camera_position


###############################################################################

def display3d_colab_plus(
    SYSTEM,
    RAYS,
    view=0,
    inline=True,                 # lo dejo por compatibilidad con tu API
    BackgCol="white",
    BackgColTop="white",
    GridCol="black",
    nrays=0,
    window_size=(1200, 700),
    show_grid=True,
    show_axes=True,
    text="KrakenOS (Colab interactive)",
    html_filename=None,          # si lo pones, guarda también el html
    close=True,                  # cierra el plotter al final (recomendado)
):
    """
    display3d_colab_plus: versión INTERACTIVA para Google Colab (HTML embebido).

    - Reutiliza plot3d() y rayplot3d() (misma escena que display3d()).
    - NO usa pv.start_xvfb().
    - NO llama p.show() (en Colab puede destruir el render window).
    - Genera un HTML interactivo con p.export_html(None) y lo muestra.

    Requisitos típicos en Colab:
        pip install "pyvista[jupyter]"
    """

    import pyvista as pv

    # Mostrar HTML en notebook
    try:
        from IPython.display import HTML, display
        _HAS_IPY = True
    except Exception:
        _HAS_IPY = False

    # --- Normaliza inputs a listas (como en tu display3d_colab) ---
    SYSTEM_list = SYSTEM if isinstance(SYSTEM, list) else [SYSTEM]
    RAYS_list   = RAYS if isinstance(RAYS, list) else [RAYS]

    # --- Asegura sólidos (misma filosofía que display3d / display3d_colab) ---
    for sys_ in SYSTEM_list:
        try:
            if hasattr(sys_, "Pr3D") and getattr(sys_.Pr3D, "ExistSolid", 1) == 0:
                bld0 = getattr(sys_, "BUILD", None)
                sys_.BUILD = 1
                sys_.build()
                if bld0 is not None:
                    sys_.BUILD = bld0
        except Exception:
            pass

    # --- Plotter (sin Xvfb, sin off_screen) ---
    ST1 = "KrakenOS Colab Interactive"
    OPA = 0.99

    p = pv.Plotter(
        shape=(1, 1),
        title=ST1,
        notebook=True,
        window_size=window_size,
    )

    # --- Dibuja escena KrakenOS (IGUAL que tu display3d) ---
    for sys_ in SYSTEM_list:
        plot3d(sys_, view, p, OPA)

    for rays_ in RAYS_list:
        rayplot3d(rays_, view, p, OPA, nrays)

    # --- Estética (muy similar a display3d) ---
    if show_axes:
        try:
            p.add_axes(line_width=4)
        except Exception:
            pass

    try:
        cx, cy, cz = p.center
        p.set_focus([cx, cy, cz])
        p.camera_position = [-1.0, 0.5, 1.0]
        p.set_viewup([0, 1.0, 0])
    except Exception:
        pass

    try:
        p.enable_anti_aliasing()
    except Exception:
        pass

    try:
        p.set_background(BackgCol, top=BackgColTop)
    except Exception:
        pass

    if text:
        try:
            p.add_text(text, position="upper_left", font_size=20, color="royalblue")
        except Exception:
            pass

    if show_grid:
        try:
            p.show_grid(font_size=6, color=GridCol)
        except Exception:
            pass

    # Render “suave” sin show()
    try:
        p.render()
    except Exception:
        pass

    # --- Exporta HTML interactivo ---
    # OJO: export_html(None) regresa un buffer; NO llames p.show() antes.
    buf = p.export_html(None)
    html_str = buf.getvalue()

    if html_filename:
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_str)

    if _HAS_IPY:
        display(HTML(html_str))

    if close:
        try:
            p.close()
        except Exception:
            pass

    return html_str

###############################################################################
def display3d_colab(
    SYSTEM,
    RAYS,
    view=0,
    BackgCol="white",
    BackgColTop="white",
    GridCol="black",
    nrays=0,
    filename="/content/krakenos_display3d.png",
    window_size=(1200, 700),
    show_grid=True,
    show_axes=True,
    text="KrakenOS (Colab static)",
):
    """
    display3d_colab: versión especial para Google Colab (render estático a PNG)

    - Usa pv.start_xvfb() + off_screen=True para que funcione sin display.
    - Renderiza la escena y la muestra como imagen (screenshot).
    - No es interactiva (pero es confiable y estable para clase).
    """

    import numpy as np
    import pyvista as pv

    # Para mostrar imagen en notebook
    try:
        from IPython.display import Image, display
        _HAS_IPY = True
    except Exception:
        _HAS_IPY = False

    # 1) Asegura Xvfb (headless render) en Colab
    # Si no estás en colab igual funciona en modo off_screen si hay soporte
    try:
        pv.start_xvfb()
    except Exception:
        pass

    # 2) Asegurar sólidos
    # (tu lógica actual)
    if not isinstance(SYSTEM, list):
        SYSTEM_list = [SYSTEM]
    else:
        SYSTEM_list = SYSTEM

    BLD0 = None
    for sys_ in SYSTEM_list:
        try:
            if sys_.Pr3D.ExistSolid == 0:
                BLD0 = sys_.BUILD
                sys_.BUILD = 1
                sys_.build()
                sys_.BUILD = BLD0
        except Exception:
            # Si algo no existe, no truena aquí
            pass

    # RAYS como lista
    if not isinstance(RAYS, list):
        RAYS_list = [RAYS]
    else:
        RAYS_list = RAYS

    # 3) Plotter OFFSCREEN
    ST1 = "KrakenOS Colab Static"
    OPA = 0.95

    p = pv.Plotter(
        shape=(1, 1),
        title=ST1,
        notebook=True,
        off_screen=True,
        window_size=window_size,
    )

    # 4) Dibuja sistemas y rayos usando TUS funciones
    # (Estas ya existen en tu módulo)
    for sys_ in SYSTEM_list:
        plot3d(sys_, view, p, OPA)

    for rays_ in RAYS_list:
        rayplot3d(rays_, view, p, OPA, nrays)

    # 5) Estética
    if show_axes:
        p.add_axes(line_width=3)

    # Centrado / cámara (tus defaults)
    try:
        cx, cy, cz = p.center
        p.set_focus([cx, cy, cz])
        p.camera_position = [-1.0, 0.5, 1.0]
        p.set_viewup([0, 1.0, 0])
    except Exception:
        pass

    p.set_background(BackgCol, top=BackgColTop)

    if text:
        try:
            p.add_text(text, position="upper_left", font_size=18, color="royalblue")
        except Exception:
            pass

    if show_grid:
        try:
            p.show_grid(font_size=8, color=GridCol)
        except Exception:
            pass

    # 6) Render a PNG
    # Nota: screenshot funciona bien en off_screen
    try:
        p.show(screenshot=filename, auto_close=True)
    except Exception:
        # fallback
        p.screenshot(filename)
        p.close()

    # 7) Mostrar la imagen en Colab
    if _HAS_IPY:
        display(Image(filename))

    return filename

###############################################################################
def display3d(SYSTEM, RAYS, view=0, inline=False,     BackgCol= 'white', BackgColTop = 'white', GridCol="black", nrays = 0):

    """display3d.

    Parameters
    ----------
    SYSTEM :
        SYSTEM
    RAYS :
        RAYS
    view :
        view
    """

    SYSTEM_list = _as_list(SYSTEM)
    RAYS_list = _as_list(RAYS)

    for system in SYSTEM_list:
        ensure_display_geometry(system)

    ST1="KrakenOS v0.1. Executing Script: " + sys.argv[0]
    OPA = 0.99
    p = pv.Plotter(shape=(1, 1), title=ST1,notebook=inline)

    for system in SYSTEM_list:
        plot3d(system, view, p, OPA)
    for rays in RAYS_list:
        rayplot3d(rays, view, p, OPA, nrays)

    p.add_axes(line_width=4)

    [cx,cy,cz]=p.center
    p.set_focus([cx,cy,cz])
    p.camera_position=[-1.0, 0.5, 1.0]

    p.set_viewup([0, 1.0, 0])
    p.enable_anti_aliasing()
    p.enable_eye_dome_lighting()
    p.disable_eye_dome_lighting()
    p.set_background(BackgCol, top=BackgColTop)
    p.add_text('KrakenOS',position="upper_left" ,font_size=20,color="royalblue")
    p.show_grid(font_size=6,color=GridCol)
    p.show(auto_close=False, interactive=True, interactive_update=False)
    [cpx,cpy,cpz]=p.camera_position

    return



###############################################################################

def rayplot3d(RAYS, view, p, OPA, nrays ):
    if RAYS is None or not hasattr(RAYS, "CC"):
        return

    CCC = [_ray_points_to_polyline(rays) for rays in RAYS.CC]

    if (len(RAYS.RayWave) != 0):
        RW = np.asarray(RAYS.RayWave)
        total = min(np.shape(RW)[0], len(CCC))
        if nrays == 0:
            NR = total
        else:
            NR = min(int(nrays), total)

        for i in range(0, NR):
            RGB = wavelength_to_rgb((RW[i] * 1000.0))
            p.add_mesh(CCC[i], color=RGB, opacity=OPA, smooth_shading=True, line_width=1.0, show_edges=None)
            #TTT.append(CCC[i])
    return #TTT

###############################################################################


def plot3d(SYSTEM, view, p, OPA):
   # TTT = pv.MultiBlock()


    Absorb_color = np.array([(10 / 256), (23 / 256), (24 / 256)])
    Mirror_color = np.array([(189 / 256), (189 / 256), (189 / 256)])
    Glass_color=np.array([12/256, 238/256, 246/256])
    recorte = view
    NN = SYSTEM.AAA.n_blocks
    if (SYSTEM.SDT_0[0].Drawing == 0):
        points2 = np.c_[0.0, 0.0, 0.0]
        c = pv.PolyData(points2)
        cc = pv.PolyData(points2)
    if (SYSTEM.SDT_0[0].Drawing == 1):
        c = SYSTEM.AAA[0]
        cc = SYSTEM.AAA[0]
    for n in range(1, NN):
        if (SYSTEM.SDT_0[n].Drawing == 1):
            AAAA = SYSTEM.AAA[n]
            if (SYSTEM.SDT_0[n].Glass != 'NULL'):
                if (SYSTEM.SDT_0[n].Color == [0, 0, 0]):
                    if (SYSTEM.SDT_0[n].Glass == 'MIRROR'):
                        color = Mirror_color
                    else:
                        color = Glass_color
                    if (SYSTEM.SDT_0[n].Glass == 'ABSORB'):
                        color = Absorb_color
                else:
                    color = SYSTEM.SDT_0[n].Color


                cc = cc.merge(AAAA)
                if (recorte == 1):
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, 1, 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip(((- 1), 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (- 1), 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (- 1), 0), invert=False)
                    c = c.merge(clippedy)
                # if (recorte == 0):
                #     c = cc

                if (recorte == 0):
                    clippedx = AAAA
                    c = c.merge(clippedx)



                if (recorte == 2):
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    c = c.merge(clippedx)

                p.add_mesh(c, color, opacity=OPA, specular=1, specular_power=15, smooth_shading=True, show_edges=False)
                edges = c.extract_feature_edges(feature_angle=10, boundary_edges=True, feature_edges=False, manifold_edges=False)

               # TTT.append(c)
                if SYSTEM.SDT_0[n].Solid_3d_stl != "None" and recorte ==0:
                    print(" ") # No edges
                else:
                    p.add_mesh(edges, 'red')
                points2 = np.c_[0.0, 0.0, 0.0]
                c = pv.PolyData(points2)
    _add_mesh_or_blocks(p, SYSTEM.DDD, color=[0.5, 0.5, 0.5], opacity=OPA, show_edges=None)
    NN = SYSTEM.AAA.n_blocks
    n = 0

    for g in SYSTEM.side_number:
        if (SYSTEM.SDT_0[g].Drawing == 1):
            if (SYSTEM.SDT_0[g].Color == [0, 0, 0]):
                if (SYSTEM.SDT_0[g].Glass == 'MIRROR'):
                    LL_color = Mirror_color
                else:
                    LL_color = Glass_color
                if (SYSTEM.SDT_0[g].Glass == 'ABSORB'):
                    LL_color = Absorb_color
                color = LL_color
            else:
                color = SYSTEM.SDT_0[g].Color
            if (recorte == 1):
                clippedx = SYSTEM.BBB[n].clip('x', invert=False)
                p.add_mesh(clippedx, color ,opacity=OPA, smooth_shading=True, show_edges=None)
                clippedy = SYSTEM.BBB[n].clip('-y', invert=False)
                p.add_mesh(clippedy, color,opacity=OPA, smooth_shading=True, show_edges=None)


            if (recorte == 0):
                No_clipped = SYSTEM.BBB[n]
                p.add_mesh(No_clipped, color,opacity=OPA, smooth_shading=False, show_edges=None)

            if (recorte == 2):
                BBBB = SYSTEM.BBB[n]
                clippedx = BBBB.clip((1, 0, 0), invert=False)
                p.add_mesh(clippedx, color,opacity=OPA, smooth_shading=True, show_edges=None)

        n = (n + 1)


    return #TTT
###############################################################################
def display2d_colab(
    SYSTEM,
    RAYS=None,
    view=0,
    nrays=0,
    title="KrakenOS 2D (Plotly - Colab)",
    show=True,
    width=1100,
    height=450,
    line_width_surfaces=1.0,
    line_width_rays=1.0,
    surface_color="black",
    axis_equal=True,
):
    """
    display2d_colab()
    Alternativa a display2d() para Google Colab usando Plotly (zoom/pan nativo).

    Parámetros
    ----------
    SYSTEM : object o list[object]
        Tu sistema óptico (o lista de sistemas). Debe ser compatible con Plot2DSurf logic.
        Aquí NO usamos pyvista, solo datos ya calculados para 2D.

    RAYS : object o list[object] o None
        Rayos (o lista). Debe tener .CC y opcionalmente .RayWave como en KrakenOS.

    view : int
        0 => Y vs Z
        1 => X vs Z

    nrays : int
        0 => usa todos
        >0 => limita a N rayos

    axis_equal : bool
        True => igual escala en X/Y (más “óptico”, sin deformar)
        False => escala libre
    """

    import numpy as np
    import plotly.graph_objects as go

    # --- helpers internos (copiados/adaptados de tu estilo KrakenOS) ---
    def wavelength_to_rgb(wavelength, gamma=1.0):
        wavelength = float(wavelength)
        if 380 <= wavelength <= 440:
            attenuation = 0.3 + (0.7 * (wavelength - 380) / (440 - 380))
            R = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma
            G = 0.0
            B = (1.0 * attenuation) ** gamma
        elif 440 <= wavelength <= 490:
            R = 0.0
            G = ((wavelength - 440) / (490 - 440)) ** gamma
            B = 1.0
        elif 490 <= wavelength <= 510:
            R = 0.0
            G = 1.0
            B = (-(wavelength - 510) / (510 - 490)) ** gamma
        elif 510 <= wavelength <= 580:
            R = ((wavelength - 510) / (580 - 510)) ** gamma
            G = 1.0
            B = 0.0
        elif 580 <= wavelength <= 645:
            R = 1.0
            G = (-(wavelength - 645) / (645 - 580)) ** gamma
            B = 0.0
        elif 645 <= wavelength <= 750:
            attenuation = 0.3 + (0.7 * (750 - wavelength) / (750 - 645))
            R = (1.0 * attenuation) ** gamma
            G = 0.0
            B = 0.0
        else:
            R = G = B = 0.0

        R = int(R * 255) / 255.0
        G = int(G * 255) / 255.0
        B = int(B * 255) / 255.0
        return (R, G, B)

    def rgb_to_hex(rgb):
        r, g, b = rgb
        return f"rgb({int(255*r)},{int(255*g)},{int(255*b)})"

    # --- Normaliza inputs a lista ---
    if not isinstance(SYSTEM, list):
        SYSTEMS = [SYSTEM]
    else:
        SYSTEMS = SYSTEM

    if RAYS is None:
        RLIST = []
    elif not isinstance(RAYS, list):
        RLIST = [RAYS]
    else:
        RLIST = RAYS

    fig = go.Figure()

    # ==============================================================
    # 1) DIBUJAR SUPERFICIES 2D
    # ==============================================================
    # Nota: En tu KrakenOS original, Plot2DSurf usa PyVista para sacar bordes 2D.
    # Aquí hacemos un enfoque "minimal": usamos SYSTEM.AAA (si existe como PolyData)
    # pero si no existe, no rompemos. La idea es que puedas extenderlo fácilmente.

    for SYS in SYSTEMS:
        # Si tu SYSTEM tiene un objeto ya construido con puntos 3D de superficies:
        # intentamos graficar contornos en corte.
        # Lo más robusto: si existe SYS.AAA (MultiBlock) con .points
        if hasattr(SYS, "AAA"):
            try:
                blocks = SYS.AAA
                # MultiBlock: iterable
                for obj in blocks:
                    if obj is None:
                        continue
                    pts = obj.points
                    if pts is None or len(pts) == 0:
                        continue

                    z = pts[:, 2]
                    if view == 0:
                        y = pts[:, 1]  # Y vs Z
                        fig.add_trace(go.Scatter(
                            x=z,
                            y=y,
                            mode="lines",
                            line=dict(color=surface_color, width=line_width_surfaces),
                            name="Surface",
                            showlegend=False,
                        ))
                    else:
                        x = pts[:, 0]  # X vs Z
                        fig.add_trace(go.Scatter(
                            x=z,
                            y=x,
                            mode="lines",
                            line=dict(color=surface_color, width=line_width_surfaces),
                            name="Surface",
                            showlegend=False,
                        ))
            except Exception as e:
                print("⚠️ No pude graficar superficies desde SYSTEM.AAA:", e)

    # ==============================================================
    # 2) DIBUJAR RAYOS 2D
    # ==============================================================
    for R in RLIST:
        if not hasattr(R, "CC"):
            continue

        CC = R.CC
        if CC is None:
            continue

        # Número de rayos
        NR = len(CC)
        if hasattr(R, "RayWave") and len(getattr(R, "RayWave", [])) == NR:
            waves = np.asarray(R.RayWave)
        else:
            waves = None

        if nrays and nrays > 0:
            NR = min(NR, nrays)

        for i in range(NR):
            ray_pts = np.asarray(CC[i])
            if ray_pts.ndim != 2 or ray_pts.shape[1] < 3:
                continue

            z = ray_pts[:, 2]
            if view == 0:
                yy = ray_pts[:, 1]
                ylab = "Y (mm)"
            else:
                yy = ray_pts[:, 0]
                ylab = "X (mm)"

            # color por longitud de onda si existe
            if waves is not None:
                col = rgb_to_hex(wavelength_to_rgb(waves[i] * 1000.0))
            else:
                col = "royalblue"

            fig.add_trace(go.Scatter(
                x=z,
                y=yy,
                mode="lines",
                line=dict(width=line_width_rays, color=col),
                name="Rays",
                showlegend=False,
            ))

    # ==============================================================
    # 3) Layout + Zoom
    # ==============================================================
    fig.update_layout(
        title=title,
        width=width,
        height=height,
        template="plotly_white",
        xaxis_title="Z (mm)",
        yaxis_title="Y (mm)" if view == 0 else "X (mm)",
        dragmode="pan",  # pan por default (zoom con rueda)
    )

    # Zoom/pan + botones
    fig.update_layout(
        xaxis=dict(
            showgrid=True,
            zeroline=True,
        ),
        yaxis=dict(
            showgrid=True,
            zeroline=True,
            scaleanchor="x" if axis_equal else None,  # relación 1:1 tipo óptico
            scaleratio=1 if axis_equal else None,
        ),
        margin=dict(l=40, r=20, t=60, b=40),
    )

    #if show:
     #   fig.show()

    #return fig

    if show:
        fig.show()
        return None
    return fig
    


###############################################################################
def display2d(SYSTEM, RAYS, view=0, arrow=0, nrays = 0, figsize: Tuple=(10, 4), fs: int=11):
    """display2d.

    Parameters
    ----------
    SYSTEM :
        SYSTEM
    RAYS :
        RAYS
    view :
        view
    """
    SYSTEM_list = _as_list(SYSTEM)
    RAYS_list = _as_list(RAYS)

    for system in SYSTEM_list:
        ensure_display_geometry(system)

    fs=fs # font size
    fig = plt.figure(figsize=figsize)

    ax1 = fig.add_subplot(111)

    for SYS in SYSTEM_list:
        Plot2DSurf(SYS, view, ax1)

    for R in RAYS_list:
        Plot2DRays(R, view, arrow, ax1, nrays)

    plt.title('System Plot')
    plt.xlabel('Z (mm)')
    if (view == 0):
        plt.ylabel('Y (mm)')
    if (view == 1):
        plt.ylabel('X (mm)')
    plt.axis('equal')
    plt.show()

###############################################################################

def Plot2DSurf(SYSTEM, view, ax1):
    fs = 11
    NN = SYSTEM.AAA.n_blocks
    if (SYSTEM.SDT_0[0].Drawing == 0):
        points2 = np.c_[0.0, 0.0, 0.0]
        c = pv.PolyData(points2, force_float=False)
    if (SYSTEM.SDT_0[0].Drawing == 1):
        c = SYSTEM.AAA[0]
    sign=-1.0
    sn=0.65
    mx = []
    mn = []
    for n in range(0, NN):
        if SYSTEM.SDT_0[n].Solid_3d_stl != "None":
            solid = 1
        else:
            solid = 0

        sn = sn * sign
        if (SYSTEM.SDT_0[n].Drawing == 1):
            AAAA = SYSTEM.AAA[n]
            if (SYSTEM.SDT_0[n].Glass != 'NULL'):
                (PosX, PosY) = SYSTEM.SDT_0[n].Nm_Pos
                s = SYSTEM.SDT_0[n].Name
                ss = SYSTEM.Object_Num[n]
                if (view == 0):
                    LT = ''
                    (ax, ay, az) = edge_3d(AAAA, 1, 0, 0, solid)
                    (az, ay) = filter_face_2dplot(az, ay, solid)
                    ax1.plot(az, ay, LT, c='black', linewidth=0.5)
                    (ax, ay, az) = edge_3d(AAAA, (- 1), 0, 0, solid)
                    (az, ay) = filter_face_2dplot(az, ay, solid)
                    ax1.plot(az, ay, LT, c='black', linewidth=0.5)
                    ax1.text(((np.max(az) + PosX) + 1), ((np.max(ay) + PosY) - 1), s, fontsize=fs)
                    delta = ((np.max(ay) - np.min(ay)) / 10)


                    ABC=int(0.5*(np.argmin(ay) - np.argmax(ay)))
                    CordABC = az[ABC]


                    if SYSTEM.SDT_0[n].NumLabel == 1:

                        ax1.text(CordABC, sn*1.5*(np.min(ay) - (1.5 * delta)), (('[' + str(ss)) + ']'), fontsize=fs)
                        ax1.plot([CordABC, CordABC], [np.mean(ay), sn*1.5*(np.min(ay) - delta)], '-.', c='red', linewidth=0.5)
                    if ((PosX != 0) or (PosY != 0)):
                        ax1.arrow((np.max(az) + PosX), (np.max(ay) + PosY/2), (- PosX), (- PosY/2.0), head_width=0.5, head_length=1.0, fc='k', ec='k', length_includes_head=True)
                        ax1.arrow((np.max(az) + PosX), (np.max(ay) + PosY), (- PosX)*0, (- PosY)/2.0, head_width=0.1, head_length=0.0, fc='k', ec='k', length_includes_head=True)

                if (view == 1):

                    LT = ''
                    (ax, ay, az) = edge_3d(AAAA, 0, 1, 0, solid)
                    (az, ax) = filter_face_2dplot(az, ax, solid)
                    ax1.plot(az, ax, LT, c='black', linewidth=0.5)
                    (ax, ay, az) = edge_3d(AAAA, 0, (- 1), 0, solid)
                    (az, ax) = filter_face_2dplot(az, ax, solid)
                    ax1.plot(az, ax, LT, c='black', linewidth=0.5)
                    ax1.text(((np.max(az) + PosX) + 1), ((np.max(ax) + PosY) - 1), s, fontsize=fs)
                    delta = ((np.max(ax) - np.min(ax)) / 10)

                    ABC=int(0.5*(np.argmin(ax) - np.argmax(ax)))
                    CordABC = az[ABC]


                    if SYSTEM.SDT_0[n].NumLabel == 1:
                        ax1.text(CordABC, sn*1.5*(np.min(ax) - (1.5 * delta)), (('[' + str(ss)) + ']'), fontsize=fs)
                        ax1.plot([CordABC, CordABC], [np.mean(ax), sn*1.5*(np.min(ax) - delta)], '-.', c='red', linewidth=0.5)

                    if ((PosX != 0) or (PosY != 0)):
                        ax1.arrow((np.max(az) + PosX), (np.max(ax) + PosY/2), (- PosX), (- PosY/2.0), head_width=0.5, head_length=1.0, fc='k', ec='k', length_includes_head=True)
                        ax1.arrow((np.max(az) + PosX), (np.max(ax) + PosY), (- PosX)*0, (- PosY)/2.0, head_width=0.1, head_length=0.0, fc='k', ec='k', length_includes_head=True)

            mx.append(np.max(az))
            mn.append(np.min(az))

    NN = SYSTEM.BBB.n_blocks
    for n in range(0, NN):
        if SYSTEM.SDT_0[n].Solid_3d_stl != "None":
            solid = 1
        else:
            solid = 0

        TT = SYSTEM.BBB[n]


        sim = '-.'

# Grin

        if (view == 0):
            (ax, ay, az) = edge_3d(TT, 1, 0, 0, solid)
            ax1.plot(az, ay, sim, c='black', linewidth=0.5)
            (ax, ay, az) = edge_3d(TT, (- 1), 0, 0, solid)
            ax1.plot(az, ay, sim, c='black', linewidth=0.5)
        if (view == 1):
            (ax, ay, az) = edge_3d(TT, 0, 1, 0, solid)
            ax1.plot(az, ax, sim, c='black', linewidth=0.5)
            (ax, ay, az) = edge_3d(TT, 0, (- 1), 0, solid)
            ax1.plot(az, ax, sim, c='black', linewidth=0.5)

    mx = np.asarray(mx)
    mn = np.asarray(mn)

    m1=np.min(mn)
    m2=np.max(mx)
    m3=(m2-m1)/20.0
    ax1.plot([m1-m3 , m2+m3],[0,0],'--', color="black", linewidth=1)

###############################################################################
def Plot2DRays(RAYS, view, arrow, ax1, nrays):

    if RAYS is None or not hasattr(RAYS, "CC"):
        return

    CCC = [np.asarray(rays) for rays in RAYS.CC]

    if (len(RAYS.RayWave) != 0):
        RW = np.asarray(RAYS.RayWave)
        total = min(np.shape(RW)[0], len(CCC))
        if nrays == 0:
            NR = total
        else:
            NR = min(int(nrays), total)
        for i in range(0, NR):
            RGB = wavelength_to_rgb((RW[i] * 1000.0))
            RRR = CCC[i]
            if RRR.ndim != 2 or RRR.shape[1] < 3:
                continue
            Ax = RRR[:, 0]
            Ay = RRR[:, 1]
            Az = RRR[:, 2]
            for f in range(1,len(Ax)):
                if (view == 0):
                    line = ax1.plot([Az[f-1],Az[f]], [Ay[f-1],Ay[f]], color=RGB, linewidth=0.5)[0]
                if (view == 1):
                    line = ax1.plot([Az[f-1],Az[f]], [Ax[f-1],Ax[f]], color=RGB, linewidth=0.5)[0]
                if arrow != 0:
                    add_arrow(line, size=5*arrow)

###############################################################################

def edge_3d(MeshObject, cx, cy, xz, solid):
    """edge_3d.

    Parameters
    ----------
    MeshObject :
        MeshObject
    cx :
        cx
    cy :
        cy
    xz :
        xz
    """
    c = MeshObject.clip((cx, cy, xz), invert=False)
    edges = c.extract_feature_edges(boundary_edges=True, feature_edges=False, manifold_edges=False)

    if solid ==0:
        Ax = edges.points[:, 0]
        Ay = edges.points[:, 1]
        Az = edges.points[:, 2]

    else:
        Ax = c.points[:, 0]
        Ay = c.points[:, 1]
        Az = c.points[:, 2]

    Ax = np.asarray(Ax)
    Ay = np.asarray(Ay)
    Az = np.asarray(Az)
    Xe = []
    Ye = []
    Ze = []
    if (cx == 1):
        i = np.argmin(Ax)
    if (cx == (- 1)):
        i = np.argmax(Ax)
    if (cy == 1):
        i = np.argmin(Ay)
    if (cy == (- 1)):
        i = np.argmax(Ay)
    x0 = Ax[i]
    y0 = Ay[i]
    z0 = Az[i]
    for j in range(0, (np.shape(Ax)[0] - 1)):
        AAx = Ax[i]
        AAy = Ay[i]
        AAz = Az[i]
        Xe.append(AAx)
        Ye.append(AAy)
        Ze.append(AAz)
        Ax = np.delete(Ax, i)
        Ay = np.delete(Ay, i)
        Az = np.delete(Az, i)
        X = (Ax - AAx)
        Y = (Ay - AAy)
        Z = (Az - AAz)
        R = np.sqrt((((X * X) + (Y * Y)) + (Z * Z)))
        i = np.argmin(R)
    Xe.append(x0)
    Ye.append(y0)
    Ze.append(z0)
    Xe = np.asarray(Xe)
    Ye = np.asarray(Ye)
    Ze = np.asarray(Ze)
    return (Xe, Ye, Ze)

def filter_face_2dplot(v1, v2, solid):
    """filter_face_2dplot.

    Parameters
    ----------
    v1 :
        v1
    v2 :
        v2
    """
    if solid == 0:
        av1 = np.copy(v1)
        av2 = np.copy(v2)
        av1 = np.roll(av1, (- 1))
        av2 = np.roll(av2, (- 1))
        yy = (v1 - av1)
        zz = (v2 - av2)
        R = np.sqrt(((yy * yy) + (zz * zz)))
        M = np.mean(R)
        AW = np.argwhere((R < M))
        v1 = v1[AW]
        v2 = v2[AW]
        av1 = np.copy(v1)
        av2 = np.copy(v2)
        av1 = np.roll(av1, 1)
        av2 = np.roll(av2, 1)
        yy = (v1 - av1)
        zz = (v2 - av2)
        R = np.sqrt(((yy * yy) + (zz * zz)))
        AW = np.argmax(R)
        v1 = np.roll(v1, (- AW))
        v2 = np.roll(v2, (- AW))

    return (v1, v2)

#####################################


# =============================================================================
# Interactive display tools
# =============================================================================

class Display2DViewer:
    """Interactive Matplotlib 2D viewer for KrakenOS systems.

    This viewer keeps the classic Plot2DSurf/Plot2DRays drawing logic, but adds
    in-window controls for the most common visualization options.
    """

    def __init__(self, SYSTEM, RAYS=None, options: Optional[Display2DOptions] = None):
        self.systems = _as_list(SYSTEM)
        self.rays_list = _as_list(RAYS)
        self.options = options or Display2DOptions()

        for system in self.systems:
            ensure_display_geometry(system)

        self.fig = None
        self.ax = None
        self._widgets = {}

    def _redraw(self):
        self.ax.clear()
        opt = self.options

        if opt.show_surfaces:
            for system in self.systems:
                Plot2DSurf(system, opt.view, self.ax)

        if opt.show_rays:
            for rays in self.rays_list:
                Plot2DRays(rays, opt.view, opt.arrow, self.ax, opt.nrays)

        self.ax.set_title(opt.title)
        self.ax.set_xlabel("Z (mm)")
        self.ax.set_ylabel("Y (mm)" if opt.view == 0 else "X (mm)")
        if opt.equal_axis:
            self.ax.axis("equal")
        if opt.grid:
            self.ax.grid(True, alpha=0.25)
        self.fig.canvas.draw_idle()

    def show(self):
        from matplotlib.widgets import CheckButtons, RadioButtons, Slider, Button

        self.fig = plt.figure(figsize=self.options.figsize)
        self.ax = self.fig.add_axes([0.08, 0.12, 0.68, 0.80])

        # Control panel
        ax_checks = self.fig.add_axes([0.80, 0.62, 0.17, 0.22])
        checks = CheckButtons(
            ax_checks,
            ["Surfaces", "Rays", "Equal", "Grid"],
            [
                self.options.show_surfaces,
                self.options.show_rays,
                self.options.equal_axis,
                self.options.grid,
            ],
        )

        def on_check(label):
            if label == "Surfaces":
                self.options.show_surfaces = not self.options.show_surfaces
            elif label == "Rays":
                self.options.show_rays = not self.options.show_rays
            elif label == "Equal":
                self.options.equal_axis = not self.options.equal_axis
            elif label == "Grid":
                self.options.grid = not self.options.grid
            self._redraw()

        checks.on_clicked(on_check)
        self._widgets["checks"] = checks

        ax_radio = self.fig.add_axes([0.80, 0.48, 0.17, 0.10])
        radio = RadioButtons(ax_radio, ("Y-Z", "X-Z"), active=self.options.view)

        def on_radio(label):
            self.options.view = 0 if label == "Y-Z" else 1
            self._redraw()

        radio.on_clicked(on_radio)
        self._widgets["radio"] = radio

        max_rays = 0
        for rays in self.rays_list:
            if hasattr(rays, "RayWave"):
                max_rays = max(max_rays, len(rays.RayWave))
        max_rays = max(max_rays, 1)

        ax_nrays = self.fig.add_axes([0.80, 0.37, 0.17, 0.03])
        nrays_slider = Slider(ax_nrays, "nrays", 0, max_rays, valinit=self.options.nrays, valstep=1)

        def on_nrays(value):
            self.options.nrays = int(value)
            self._redraw()

        nrays_slider.on_changed(on_nrays)
        self._widgets["nrays"] = nrays_slider

        ax_arrow = self.fig.add_axes([0.80, 0.29, 0.17, 0.03])
        arrow_slider = Slider(ax_arrow, "arrow", 0, 4, valinit=self.options.arrow, valstep=1)

        def on_arrow(value):
            self.options.arrow = int(value)
            self._redraw()

        arrow_slider.on_changed(on_arrow)
        self._widgets["arrow"] = arrow_slider

        ax_save = self.fig.add_axes([0.80, 0.18, 0.17, 0.06])
        save_button = Button(ax_save, "Save PNG")

        def on_save(_event):
            self.fig.savefig("krakenos_display2d.png", dpi=200, bbox_inches="tight")

        save_button.on_clicked(on_save)
        self._widgets["save"] = save_button

        self._redraw()
        plt.show()
        return self


class Display3DViewer:
    """Interactive PyVista 3D viewer for KrakenOS systems.

    PyVista remains the rendering backend. The viewer adds a small in-window
    control layer that lets users change common display options without editing
    the function call.
    """

    def __init__(self, SYSTEM, RAYS=None, options: Optional[Display3DOptions] = None):
        self.systems = _as_list(SYSTEM)
        self.rays_list = _as_list(RAYS)
        self.options = options or Display3DOptions()
        for system in self.systems:
            ensure_display_geometry(system)
        self.plotter = None
        self._actors = []

    def _add_actor(self, actor):
        if actor is not None:
            self._actors.append(actor)
        return actor

    def _remove_scene_actors(self):
        if self.plotter is None:
            return
        for actor in list(self._actors):
            try:
                self.plotter.remove_actor(actor, reset_camera=False, render=False)
            except Exception:
                pass
        self._actors.clear()

    def _add_mesh_or_blocks_actor(self, mesh, **kwargs):
        if mesh is None or (isinstance(mesh, str) and mesh == "None"):
            return
        try:
            self._add_actor(self.plotter.add_mesh(mesh, **kwargs))
            return
        except (TypeError, NotImplementedError):
            pass
        for block in mesh:
            self._add_mesh_or_blocks_actor(block, **kwargs)

    def _draw_system(self, system):
        opt = self.options
        if not opt.show_surfaces and not opt.show_masks and not opt.show_sides:
            return

        recorte = opt.view
        NN = system.AAA.n_blocks
        c = _empty_polydata()
        cc = _empty_polydata()
        if NN > 0 and system.SDT_0[0].Drawing == 1:
            c = system.AAA[0]
            cc = system.AAA[0]

        if opt.show_surfaces:
            for n in range(1, NN):
                if system.SDT_0[n].Drawing != 1:
                    continue
                AAAA = system.AAA[n]
                if system.SDT_0[n].Glass == "NULL":
                    continue

                color = _surface_display_color(system.SDT_0[n])
                cc = cc.merge(AAAA)

                if recorte == 1:
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, 1, 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip(((-1), 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (-1), 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (-1), 0), invert=False)
                    c = c.merge(clippedy)
                elif recorte == 2:
                    c = c.merge(AAAA.clip((1, 0, 0), invert=False))
                else:
                    c = c.merge(AAAA)

                self._add_actor(
                    self.plotter.add_mesh(
                        c,
                        color,
                        opacity=opt.opacity,
                        specular=1,
                        specular_power=15,
                        smooth_shading=True,
                        show_edges=False,
                    )
                )

                if opt.show_edges and not (system.SDT_0[n].Solid_3d_stl != "None" and recorte == 0):
                    try:
                        edges = c.extract_feature_edges(
                            feature_angle=10,
                            boundary_edges=True,
                            feature_edges=False,
                            manifold_edges=False,
                        )
                        self._add_actor(self.plotter.add_mesh(edges, "red"))
                    except Exception:
                        pass

                c = _empty_polydata()

        if opt.show_masks:
            self._add_mesh_or_blocks_actor(
                system.DDD,
                color=[0.5, 0.5, 0.5],
                opacity=opt.opacity,
                show_edges=None,
            )

        if opt.show_sides:
            for n, g in enumerate(system.side_number):
                if n >= system.BBB.n_blocks:
                    break
                if system.SDT_0[g].Drawing != 1:
                    continue
                color = _surface_display_color(system.SDT_0[g])
                side = system.BBB[n]
                if recorte == 1:
                    self._add_actor(self.plotter.add_mesh(side.clip('x', invert=False), color, opacity=opt.opacity, smooth_shading=True, show_edges=None))
                    self._add_actor(self.plotter.add_mesh(side.clip('-y', invert=False), color, opacity=opt.opacity, smooth_shading=True, show_edges=None))
                elif recorte == 2:
                    self._add_actor(self.plotter.add_mesh(side.clip((1, 0, 0), invert=False), color, opacity=opt.opacity, smooth_shading=True, show_edges=None))
                else:
                    self._add_actor(self.plotter.add_mesh(side, color, opacity=opt.opacity, smooth_shading=False, show_edges=None))

    def _draw_rays(self, rays):
        if not self.options.show_rays:
            return
        NR = _safe_ray_count(rays, self.options.nrays)
        if NR == 0:
            return
        RW = np.asarray(rays.RayWave)
        for i in range(NR):
            if i >= len(rays.CC):
                break
            RGB = wavelength_to_rgb(RW[i] * 1000.0)
            line = _ray_points_to_polyline(rays.CC[i])
            self._add_actor(
                self.plotter.add_mesh(
                    line,
                    color=RGB,
                    opacity=self.options.opacity,
                    smooth_shading=True,
                    line_width=self.options.ray_width,
                    show_edges=None,
                )
            )

    def redraw(self):
        self._remove_scene_actors()
        for system in self.systems:
            self._draw_system(system)
        for rays in self.rays_list:
            self._draw_rays(rays)
        try:
            self.plotter.render()
        except Exception:
            pass

    def _set_flag(self, name, value):
        setattr(self.options, name, bool(value))
        self.redraw()

    def _set_view(self, view):
        self.options.view = int(view)
        self.redraw()

    def _set_opacity(self, value):
        self.options.opacity = float(value)
        self.redraw()

    def _set_ray_width(self, value):
        self.options.ray_width = float(value)
        self.redraw()

    def _set_nrays(self, value):
        self.options.nrays = int(value)
        self.redraw()

    def show(self):
        opt = self.options
        self.plotter = pv.Plotter(
            shape=(1, 1),
            title="KrakenOS interactive display",
            notebook=opt.inline,
            window_size=opt.window_size,
        )
        self.redraw()

        if opt.show_axes:
            try:
                self.plotter.add_axes(line_width=4)
            except Exception:
                pass

        try:
            cx, cy, cz = self.plotter.center
            self.plotter.set_focus([cx, cy, cz])
            self.plotter.camera_position = [-1.0, 0.5, 1.0]
            self.plotter.set_viewup([0, 1.0, 0])
        except Exception:
            pass

        try:
            self.plotter.enable_anti_aliasing()
        except Exception:
            pass
        try:
            self.plotter.set_background(opt.background, top=opt.background_top)
        except Exception:
            pass
        if opt.text:
            try:
                self.plotter.add_text(opt.text, position="upper_left", font_size=20, color="royalblue")
            except Exception:
                pass
        if opt.show_grid:
            try:
                self.plotter.show_grid(font_size=6, color=opt.grid_color)
            except Exception:
                pass

        # Keyboard shortcuts are robust across PyVista versions.
        self.plotter.add_key_event("0", lambda: self._set_view(0))
        self.plotter.add_key_event("1", lambda: self._set_view(1))
        self.plotter.add_key_event("2", lambda: self._set_view(2))
        self.plotter.add_key_event("r", lambda: self._set_flag("show_rays", not self.options.show_rays))
        self.plotter.add_key_event("s", lambda: self._set_flag("show_surfaces", not self.options.show_surfaces))
        self.plotter.add_key_event("e", lambda: self._set_flag("show_edges", not self.options.show_edges))
        self.plotter.add_key_event("m", lambda: self._set_flag("show_masks", not self.options.show_masks))
        self.plotter.add_key_event("l", lambda: self._set_flag("show_sides", not self.options.show_sides))
        self.plotter.add_key_event("p", lambda: self.plotter.screenshot("krakenos_display3d.png"))

        # Sliders are optional controls; if a backend lacks widgets, the display still works.
        try:
            max_rays = 1
            for rays in self.rays_list:
                if hasattr(rays, "RayWave"):
                    max_rays = max(max_rays, len(rays.RayWave))
            self.plotter.add_slider_widget(
                lambda value: self._set_opacity(value),
                [0.05, 1.0],
                value=opt.opacity,
                title="opacity",
                pointa=(0.02, 0.10),
                pointb=(0.30, 0.10),
            )
            self.plotter.add_slider_widget(
                lambda value: self._set_ray_width(value),
                [1.0, 8.0],
                value=opt.ray_width,
                title="ray width",
                pointa=(0.02, 0.16),
                pointb=(0.30, 0.16),
            )
            self.plotter.add_slider_widget(
                lambda value: self._set_nrays(value),
                [0, max_rays],
                value=opt.nrays,
                title="nrays",
                pointa=(0.02, 0.22),
                pointb=(0.30, 0.22),
            )
        except Exception:
            pass

        shortcut_text = (
            "Keys: 0 full | 1 quarter | 2 half | r rays | s surfaces | "
            "e edges | m masks | l sides | p screenshot"
        )
        try:
            self.plotter.add_text(shortcut_text, position="lower_left", font_size=9, color="black")
        except Exception:
            pass

        self.plotter.show(auto_close=False, interactive=True, interactive_update=False)
        return self


def display2d_interactive(SYSTEM, RAYS=None, options: Optional[Display2DOptions] = None, **kwargs):
    """Open an interactive 2D display window.

    Keyword arguments may be used to override fields in Display2DOptions.
    Example: display2d_interactive(system, rays, nrays=20, view=1)
    """
    opt = options or Display2DOptions()
    for key, value in kwargs.items():
        if hasattr(opt, key):
            setattr(opt, key, value)
    return Display2DViewer(SYSTEM, RAYS, opt).show()


def display3d_interactive(SYSTEM, RAYS=None, options: Optional[Display3DOptions] = None, **kwargs):
    """Open an interactive 3D display window.

    Keyword arguments may be used to override fields in Display3DOptions.
    Example: display3d_interactive(system, rays, nrays=50, opacity=0.6)
    """
    opt = options or Display3DOptions()
    for key, value in kwargs.items():
        if hasattr(opt, key):
            setattr(opt, key, value)
    return Display3DViewer(SYSTEM, RAYS, opt).show()


# Backward-compatible aliases used by older documentation.
Display2D = display2d
Display3D = display3d

# Optional aliases with capitalized names for users who prefer class-like naming.
NewDisplay2D = display2d_interactive
NewDisplay3D = display3d_interactive


class display3d_OB():
    def __init__(self):


        self.view=0
        self.inline=False
        self.BackgCol= 'white'
        self.BackgColTop = 'white'
        self.GridCol="black"
        self.ST1 = " "
        self.p = pv.Plotter(shape=(1, 1), title=self.ST1,notebook = self.inline)
        self.SYSTEM = []
        self.RAYS = []

    def plot(self):
        display3d_4OB(self.SYSTEM, self.RAYS, self.view, self.inline, self.BackgCol, self.BackgColTop, self.GridCol, self.p)

def display3d_4OB(SYSTEM, RAYS, view, inline, BackgCol, BackgColTop, GridCol, p):


    """display3d.

    Parameters
    ----------
    SYSTEM :
        SYSTEM
    RAYS :
        RAYS
    view :
        view
    """

    OPA = 0.95

    CCC = []
    INST = isinstance(RAYS, list)
    if INST == True:
        for R in RAYS:
            for rays in R.CC:
                CCC.append(_ray_points_to_polyline(rays))
    else:
        for rays in RAYS.CC:
            CCC.append(_ray_points_to_polyline(rays))

    Absorb_color = np.array([(10 / 256), (23 / 256), (24 / 256)])
    Mirror_color = np.array([(189 / 256), (189 / 256), (189 / 256)])
    Glass_color=np.array([12/256, 238/256, 246/256])
    recorte = view
    NN = SYSTEM.AAA.n_blocks
    if (SYSTEM.SDT_0[0].Drawing == 0):
        points2 = np.c_[0.0, 0.0, 0.0]
        c = pv.PolyData(points2)
        cc = pv.PolyData(points2)
    if (SYSTEM.SDT_0[0].Drawing == 1):
        c = SYSTEM.AAA[0]
        cc = SYSTEM.AAA[0]

    for n in range(1, NN):
        if (SYSTEM.SDT_0[n].Drawing == 1):
            AAAA = SYSTEM.AAA[n]
            if (SYSTEM.SDT_0[n].Glass != 'NULL'):
                if (SYSTEM.SDT_0[n].Color == [0, 0, 0]):
                    if (SYSTEM.SDT_0[n].Glass == 'MIRROR'):
                        color = Mirror_color
                    else:
                        color = Glass_color
                    if (SYSTEM.SDT_0[n].Glass == 'ABSORB'):
                        color = Absorb_color
                else:
                    color = SYSTEM.SDT_0[n].Color

                cc = cc.merge(AAAA)
                if (recorte == 1):
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, 1, 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip(((- 1), 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (- 1), 0), invert=False)
                    c = c.merge(clippedy)
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    clippedy = clippedx.clip((0, (- 1), 0), invert=False)
                    c = c.merge(clippedy)
                if (recorte == 0):
                    c = cc

                if (recorte == 2):
                    clippedx = AAAA.clip((1, 0, 0), invert=False)
                    c = c.merge(clippedx)
                p.add_mesh(c, color, opacity=OPA, specular=1, specular_power=15, smooth_shading=True, show_edges=False)
                edges = c.extract_feature_edges(feature_angle=10, boundary_edges=True, feature_edges=False, manifold_edges=False)
                if SYSTEM.SDT_0[n].Solid_3d_stl != "None" and recorte ==0:
                    print(" ") # No edges
                else:
                    p.add_mesh(edges, 'red')
                points2 = np.c_[0.0, 0.0, 0.0]
                c = pv.PolyData(points2)
    _add_mesh_or_blocks(p, SYSTEM.DDD, color=[0.5, 0.5, 0.5], opacity=OPA, show_edges=None)
    NN = SYSTEM.AAA.n_blocks
    n = 0
    for g in SYSTEM.side_number:
        if (SYSTEM.SDT_0[g].Drawing == 1):
            if (SYSTEM.SDT_0[g].Color == [0, 0, 0]):
                if (SYSTEM.SDT_0[g].Glass == 'MIRROR'):
                    LL_color = Mirror_color
                else:
                    LL_color = Glass_color
                if (SYSTEM.SDT_0[g].Glass == 'ABSORB'):
                    LL_color = Absorb_color
                color = LL_color
            else:
                color = SYSTEM.SDT_0[g].Color
            if (recorte == 1):
                clippedx = SYSTEM.BBB[n].clip('x', invert=False)
                p.add_mesh(clippedx, color ,opacity=OPA, smooth_shading=True, show_edges=None)
                clippedy = SYSTEM.BBB[n].clip('-y', invert=False)
                p.add_mesh(clippedy, color,opacity=OPA, smooth_shading=True, show_edges=None)
            if (recorte == 0):
                No_clipped = SYSTEM.BBB[n]
                p.add_mesh(No_clipped, color,opacity=OPA, smooth_shading=False, show_edges=None)
            if (recorte == 2):
                BBBB = SYSTEM.BBB[n]
                clippedx = BBBB.clip((1, 0, 0), invert=False)
                p.add_mesh(clippedx, color,opacity=OPA, smooth_shading=True, show_edges=None)
        n = (n + 1)

    if INST == True:
       for R in RAYS:
            if (len(R.RayWave) != 0):
                RW = np.asarray(R.RayWave)
                for i in range(0, np.shape(RW)[0]):
                    RGB = wavelength_to_rgb((RW[i] * 1000.0))
                    p.add_mesh(CCC[i], color=RGB, opacity=OPA, smooth_shading=True, line_width=1.0, show_edges=None)

    else:
        if (len(RAYS.RayWave) != 0):
            RW = np.asarray(RAYS.RayWave)
            for i in range(0, np.shape(RW)[0]):
                RGB = wavelength_to_rgb((RW[i] * 1000.0))
                p.add_mesh(CCC[i], color=RGB, opacity=OPA, smooth_shading=True, line_width=1.0, show_edges=None)

    p.add_axes(line_width=4)
    [cx,cy,cz]=p.center
    p.set_focus([cx,cy,cz])
    p.camera_position=[-1.0, 0.5, 1.0]
    p.set_viewup([0, 1.0, 0])
    p.enable_anti_aliasing()
    p.enable_eye_dome_lighting()
    p.disable_eye_dome_lighting()
    p.set_background(BackgCol, top=BackgColTop)
    p.add_text('KrakenOS',position="upper_left" ,font_size=20,color="royalblue")
    p.show_grid(font_size=6,color=GridCol)
    p.show(auto_close=False, interactive=True, interactive_update=True)
    [cpx,cpy,cpz]=p.camera_position
