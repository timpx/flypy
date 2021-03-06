# -*- coding: utf-8 -*-

"""
Buffer objects.
"""

from __future__ import print_function, division, absolute_import

from flypy import sjit, jit
import flypy
import flypy.runtime
from .core import Type, Pointer, Slice, counting_iterator
from .sliceobject import normalize

# NOTE: There is a problem with the GC when Buffer is @jit, causing it it
#       segfault (e.g. when building a list literal)
#       Marking this sjit is incorrect however

@sjit('Buffer[a]')
class Buffer(object):
    layout = [
        ('p', 'Pointer[a]'),
        ('size', 'int64'),
        ('free', 'bool'),
    ]

    @jit('Buffer[a] -> Pointer[a] -> int64 -> bool -> void')
    def __init__(self, p, size, free=False):
        self.p = p
        self.size = size
        self.free = free # TODO: make this a function !

    @jit('a -> a -> bool')
    def __eq__(self, other):
        if self.p == other.p:
            return True
        elif self.size != other.size:
            return False
        else:
            return flypy.runtime.ffi.memcmp(self.p, other.p, self.size)

    @jit('a -> b -> bool')
    def __eq__(self, other):
        return False

    @jit('Buffer[a] -> int64 -> a')
    def __getitem__(self, item):
        return self.p[item]

    @jit('Buffer[a] -> int64 -> a -> void')
    def __setitem__(self, item, value):
        self.p[item] = value

    @jit('Buffer[a] -> Slice[x, y, z] -> a -> void')
    def __setitem__(self, s, value):
        domain = normalize(s, len(self))
        for i in range(*domain):
            self.p[i] = value

    @jit
    def __iter__(self):
        return counting_iterator(self)

    @jit('a -> int64')
    def __len__(self):
        return self.size

    #@jit
    #def __del__(self):
    #    if self.free:
    #        flypy.runtime.ffi.free(self.p)

    # ----------------------------------

    @jit('a -> int64 -> void')
    def resize(self, n):
        flypy.runtime.ffi.realloc(self.p, n)
        self.size = n

    @jit('Buffer[a] -> Pointer[a]')
    def pointer(self): # TODO: Properties
        return self.p

    def __str__(self):
        return "buffer(%s)" % list(self)

#===------------------------------------------------------------------===
# Buffer utils
#===------------------------------------------------------------------===

@jit('Type[a] -> int64 -> Buffer[a]')
def newbuffer(basetype, size):
    p = flypy.runtime.ffi.malloc(size, basetype)
    return Buffer(p, size, True)

# @jit('Sequence[a] -> Type[a] -> Buffer[a]') # TODO: <--
def fromseq(seq, basetype):
    n = len(seq)
    buf = newbuffer(basetype, n)
    for i, item in enumerate(seq):
        buf[i] = item
    return buf

@jit('Buffer[a] -> Buffer[a] -> int64 -> void')
def copyto(src, dst, offset):
    p_src = src.pointer()
    p_dst = dst.pointer() + offset

    # TODO: bounds-check

    for i in range(len(src)):
        p_dst[i] = p_src[i]