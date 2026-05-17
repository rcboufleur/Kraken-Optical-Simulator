import copy


class MeshBlock(list):
    """Small list-like mesh container with PyVista-style block count."""

    @property
    def n_blocks(self):
        return len(self)

    def copy(self, deep=False):
        if not deep:
            return MeshBlock(self)

        copied = MeshBlock()
        for item in self:
            if hasattr(item, "copy"):
                try:
                    copied.append(item.copy(deep=True))
                    continue
                except TypeError:
                    pass
            copied.append(copy.deepcopy(item))
        return copied
