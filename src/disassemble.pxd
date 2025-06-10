import cython
from libc.stdint cimport int64_t, uint8_t, uint16_t, uint32_t, uint64_t

cimport memory

cdef class Decoder:
    cdef memory.Memory memory
    cdef uint64_t address
    cdef list unprefixed, cbprefixed
    cpdef uint16_t getMem(self, uint16_t, uint8_t counter=*)
    cpdef void setMem(self, uint16_t, uint8_t)
    @cython.locals(opcode=int,cbbool=bint,oparr=list,operand=object)
    cdef Wrapper decode(self, uint16_t)

cdef class Wrapper:
    cdef public uint16_t address
    cdef public object instruction
    cdef public bint cbbool

cdef disassemble(Decoder, uint16_t, int)