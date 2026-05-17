import pyvista as pv


def make_disc(center, inner, outer, normal, r_res, c_res):
    return pv.Disc(
        center=center,
        inner=inner,
        outer=outer,
        normal=normal,
        r_res=r_res,
        c_res=c_res,
    )


def make_polydata(points, faces=None, force_float=False):
    if faces is None:
        return pv.PolyData(points, force_float=force_float)
    return pv.PolyData(points, faces, force_float=force_float)


def read_mesh(path):
    return pv.read(path)


def is_polydata(mesh):
    return isinstance(mesh, pv.core.pointset.PolyData)
