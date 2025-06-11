from libc.stdint cimport int64_t, uint8_t, uint16_t, uint32_t, uint64_t

import cython

cdef class Joypad:
    cdef uint8_t value
    cdef uint8_t joypad

    cpdef uint8_t getJoypad(self)
    @cython.locals(buttons=bint,dpad=bint)
    cpdef void setJoypad(self, uint8_t)
