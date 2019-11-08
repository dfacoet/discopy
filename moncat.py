""" Implements free monoidal categories and monoidal functors.
Naturality needs to be computed explicitly with interchangers.
"""

from discopy.cat import FAST, Ob, Arrow, Generator, Functor

class Ty(list):
    """ Implements a type as a list of objects, used as dom and cod of diagrams.

    >>> x, y, z = Ty('x'), Ty('y'), Ty('z')
    >>> x
    Ty('x')
    >>> print(x)
    x
    >>> x + y
    Ty('x', 'y')
    >>> assert x + y != y + x
    >>> assert (x + y) + z == x + y + z == x + (y + z)
    """
    def __init__(self, *t):
        super().__init__(x if isinstance(x, Ob) else Ob(x) for x in t)

    def __add__(self, other):
        return Ty(*(super().__add__(other)))

    def __getitem__(self, key):  # allows to compute slices of types
        if isinstance(key, slice):
            return Ty(*super().__getitem__(key))
        return super().__getitem__(key)

    def __repr__(self):
        return "Ty({})".format(', '.join(repr(x.name) for x in self))

    def __str__(self):
        return ' + '.join(map(str, self)) or 'Ty()'

    def __hash__(self):
        return hash(repr(self))

class Diagram(Arrow):
    """ Implements a diagram with dom, cod, a list of boxes and offsets.

    >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
    >>> f0, f1 = Box('f0', x, y, params=[0.2]), Box('f1', z, w, params=[1])
    >>> assert Id(x) @ f1 >> f0 @ Id(w) == (f0 @ f1).interchange(0, 1)
    >>> assert (f0 @ f1).interchange(0, 1).interchange(0, 1) == f0 @ f1

    >>> s0, s1 = Box('s0', Ty(), Ty()), Box('s1', Ty(), Ty())
    >>> assert s0 @ s1 == s0 >> s1 == (s1 @ s0).interchange(0, 1)
    >>> assert s1 @ s0 == s1 >> s0 == (s0 @ s1).interchange(0, 1)
    """
    def __init__(self, dom, cod, boxes, offsets):
        assert isinstance(dom, Ty)
        assert isinstance(cod, Ty)
        assert isinstance(boxes, list)
        assert isinstance(offsets, list)
        assert len(boxes) == len(offsets)
        assert all(isinstance(f, Diagram) for f in boxes)
        assert all(isinstance(n, int) for n in offsets)
        self._dom, self._cod = dom, cod
        self._boxes, self._offsets = boxes, offsets
        self._data = list(zip(boxes, offsets))  # used by the Arrow class
        list.__init__(self, zip(boxes, offsets))
        if not FAST:
            scan = dom
            for f, n in zip(boxes, offsets):
                assert scan[n : n + len(f.dom)] == f.dom
                scan = scan[: n] + f.cod + scan[n + len(f.dom) :]
            assert scan == cod

    @property
    def boxes(self):
        return self._boxes

    @property
    def offsets(self):
        return self._offsets

    def __repr__(self):
        if not self:  # i.e. self is identity.
            return repr(Id(self.dom))
        return "Diagram(dom={}, cod={}, boxes={}, offsets={})".format(
            repr(self.dom), repr(self.cod),
            repr(self.boxes), repr(self.offsets))

    def __str__(self):
        if not self:  # i.e. self is identity.
            return str(self.id(self.dom))
        def line(scan, box, off):
            left = "{} @ ".format(self.id(scan[:off])) if scan[:off] else ""
            right = " @ {}".format(self.id(scan[off + len(box.dom):]))\
                                   if scan[off + len(box.dom):] else ""
            return left + str(box) + right
        box, off = self.boxes[0], self.offsets[0]
        result = line(self.dom, box, off)
        scan = self.dom[:off] + box.cod + self.dom[off + len(box.dom):]
        for box, off in zip(self.boxes[1:], self.offsets[1:]):
            result = "{} >> {}".format(result, line(scan, box, off))
            scan = scan[:off] + box.cod + scan[off + len(box.dom):]
        return result

    def tensor(self, other):
        assert isinstance(other, Diagram)
        dom, cod = self.dom + other.dom, self.cod + other.cod
        boxes = self.boxes + other.boxes
        offsets = self.offsets + [n + len(self.cod) for n in other.offsets]
        return Diagram(dom, cod, boxes, offsets)

    def __matmul__(self, other):
        return self.tensor(other)

    def then(self, other):
        assert isinstance(other, Diagram) and self.cod == other.dom
        dom, cod = self.dom, other.cod
        boxes = self.boxes + other.boxes
        offsets = self.offsets + other.offsets
        return Diagram(dom, cod, boxes, offsets)

    def dagger(self):
        return Diagram(self.cod, self.dom,
            [f.dagger() for f in self.boxes[::-1]], self.offsets[::-1])

    @staticmethod
    def id(x):
        return Id(x)

    def interchange(self, k0, k1):
        assert k0 + 1 == k1
        box0, box1 = self.boxes[k0], self.boxes[k1]
        off0, off1 = self.offsets[k0], self.offsets[k1]
        if off1 >= off0 + len(box0.cod):  # box0 left of box1
            off1 = off1 - len(box0.cod) + len(box0.dom)
        elif off0 >= off1 + len(box1.dom):  # box1 left of box0
            off0 = off0 - len(box1.dom) + len(box1.cod)
        else:
            raise Exception("Interchange not allowed."
                            "Boxes ({}, {}) are connected.".format(box0, box1))
        return Diagram(self.dom, self.cod,
                       self.boxes[:k0] + [box1, box0] + self.boxes[k0 + 2:],
                       self.offsets[:k0] + [off1, off0] + self.offsets[k0 + 2:])

class Id(Diagram):
    """ Implements the identity diagram of a given type.

    >>> assert Id(Ty('x')) == Diagram(Ty('x'), Ty('x'), [], [])
    """
    def __init__(self, x):
        super().__init__(x, x, [], [])

    def __repr__(self):
        return "Id({})".format(repr(self.dom))

    def __str__(self):
        return "Id({})".format(str(self.dom))

class Box(Generator, Diagram):
    """ Implements a box as a generator for diagrams.

    >>> f = Box('f', Ty('x', 'y'), Ty('z'), params=[0.2, 0.3])
    >>> f
    Box(name='f', dom=Ty('x', 'y'), cod=Ty('z'), params=[0.2, 0.3])
    >>> f.dagger()
    Box(name='f', dom=Ty('x', 'y'), cod=Ty('z'), params=[0.2, 0.3]).dagger()
    >>> assert f == Diagram(Ty('x', 'y'), Ty('z'), [f], [0])
    >>> f.params
    [0.2, 0.3]
    >>> f.params = [0.5, 0.3, 1]
    >>> f.params
    [0.5, 0.3, 1]
    """
    def __init__(self, name, dom, cod, dagger=False, params=None):
        assert isinstance(dom, Ty)
        assert isinstance(cod, Ty)
        self._dom, self._cod, self._boxes, self._offsets = dom, cod, [self], [0]
        self._name, self._dagger, self._params = name, dagger, params
        Diagram.__init__(self, dom, cod, [self], [0])

    def dagger(self):
        return Box(self.name, self.cod, self.dom, dagger=not self._dagger,
                                                  params=self.params)

    def __repr__(self):
        if self._dagger:
            return "Box(name={}, dom={}, cod={}, params={}).dagger()".format(
                *map(repr, [self.name, self.cod, self.dom, self.params]))
        return "Box(name={}, dom={}, cod={}, params={})".format(
            *map(repr, [self.name, self.dom, self.cod, self.params]))

    def __hash__(self):
        return hash(repr(self))

    def __eq__(self, other):
        if isinstance(other, Box):
            return repr(self) == repr(other)
        elif isinstance(other, Diagram):
            return len(other) == 1 and other.boxes[0] == self

    def __copy__(self):
        return Box(self._name, self._dom, self._cod, dagger=self._dagger,
                                                        params=self._params)

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, new_params):
        self._params = new_params

class ArDict:
    """Takes a python function and gives a getitem method on it

    >>> func = lambda x: x + 2
    >>> ar = ArDict(func)
    >>> ar[3]
    5
    """
    def __init__(self, func):
        self._func = func

    def __getitem__(self, box):
        return self._func(box)

    def __repr__(self):
        return "ArDict({})".format(self._func)

class MonoidalFunctor(Functor):
    """ Implements a monoidal functor given its image on objects and arrows.

    >>> x, y, z, w = Ty('x'), Ty('y'), Ty('z'), Ty('w')
    >>> f0, f1 = Box('f0', x, y, params=[0.1]), Box('f1', z, w, params=[1.1])
    >>> ob = {x: z, y: w, z: x, w: y}
    >>> ar = ArDict(lambda f: f1 if f == f0 else f0 if f == f1 else None)
    >>> F = MonoidalFunctor(ob, ar)
    >>> assert F(f0) == f1 and F(f1) == f0
    >>> assert F(F(f0)) == f0
    >>> F(f0)
    Box(name='f1', dom=Ty('z'), cod=Ty('w'), params=[1.1])
    >>> f1.params = [2, 3]
    >>> F(f0)
    Box(name='f1', dom=Ty('z'), cod=Ty('w'), params=[2, 3])
    >>> assert F(f0 @ f1) == f1 @ f0
    >>> assert F(f0 >> f0.dagger()) == f1 >> f1.dagger()
    >>> def ar_func(box):
    ...    newbox = box.copy()
    ...    newbox.params = [2*box.params[i] for i in range(len(box.params))]
    ...    return newbox
    >>> ar1 = ArDict(ar_func)
    >>> F1 = MonoidalFunctor(ob, ar1)
    """
    def __init__(self, ob, ar):
        assert all(isinstance(x, Ty) and len(x) == 1 for x in ob.keys())
        self._objects, self._arrows = ob, ar
        self._ob, self._ar = {x[0]: y for x, y in ob.items()}, ar

    def __repr__(self):
        return "MonoidalFunctor(ob={}, ar={})".format(self._objects, self._arrows)

    def __call__(self, d):
        if isinstance(d, Ty):
            return sum([self.ob[x] for x in d], Ty())
        elif isinstance(d, Box):
            return self.ar[d.dagger()].dagger() if d._dagger else self.ar[d]
        scan, result = d.dom, Id(self(d.dom))
        for f, n in d:
            result = result >> Id(self(scan[:n])) @ self(f)\
                             @ Id(self(scan[n + len(f.dom):]))
            scan = scan[:n] + f.cod + scan[n + len(f.dom):]
        return result
