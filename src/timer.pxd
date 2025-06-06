from libc.stdint cimport int64_t, uint8_t, uint16_t, uint32_t, uint64_t

import cython

cdef class Timer:
    cdef uint64_t DIV, DIV_counter, TIMA, TMA, TAC, counter

    cdef void resetCounter(self)

    cdef void reset(self)

    @cython.locals(c_select=uint8_t)
    cdef uint64_t getFreq(self)

    cdef bint tick(self, uint64_t)