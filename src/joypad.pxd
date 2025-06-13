from libc.stdint cimport int64_t, uint8_t, uint16_t, uint32_t, uint64_t

import cython

cdef class Joypad:
    cdef uint8_t value
    cdef uint8_t joypad

    @cython.locals(prevbit=bint)
    cdef bint reset_joypadbit(self, uint8_t)
    cdef bint set_joypadbit(self, uint8_t)
    cpdef uint8_t getJoypad(self)
    @cython.locals(buttons=bint,dpad=bint)
    cpdef void setJoypad(self, uint8_t)
    @cython.locals(interrupt=bint)
    cpdef bint handleInput(self, uint8_t, bint)
