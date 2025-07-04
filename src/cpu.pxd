from libc.stdint cimport int64_t, uint8_t, uint16_t, uint32_t, uint64_t

import cython
cimport disassemble
cimport timer
cimport screen
cimport joypad


cdef class InstructionError(Exception):
    pass

cdef class CPU:
    cdef public registers
    cdef public disassemble.Decoder decoder
    cdef public uint8_t i_master, i_enable, i_flag
    cdef public bint i_queue, halt
    cdef str blargg
    cdef public timer.Timer timer
    cdef public screen.Screen screen
    cdef public joypad.Joypad joypad
    cdef public uint8_t sync_cycles, cycles
    cdef uint64_t maxcycles
    cdef float cputime, screentime
    cpdef initVals(self)
    @cython.locals(val=uint16_t)
    cdef inline void POP(self, object)
    @cython.locals(val=uint16_t)
    cdef inline void PUSH(self, object)
    cdef inline void JP(self, uint16_t)
    @cython.locals(val=uint16_t,res=uint16_t)
    cdef inline void CP(self, object)
    @cython.locals(val=uint16_t,res=uint16_t)
    cdef inline void XOR(self, object)
    @cython.locals(val=uint16_t,res=uint16_t,carry=uint16_t)
    cdef inline void SBC(self, object)
    @cython.locals(val=uint16_t,res=uint16_t,carry=uint16_t)
    cdef inline void ADC(self, object)
    @cython.locals(val=uint16_t,res=uint16_t)
    cdef inline void OR(self, object)
    @cython.locals(val=uint16_t,res=uint16_t)
    cdef inline void AND(self, object)
    @cython.locals(val=uint16_t)
    cdef inline void DEC(self, object)
    @cython.locals(val=uint16_t)
    cdef inline void INC(self, object)
    @cython.locals(val=uint16_t,res=uint16_t)
    cdef inline void ADD(self, object, object)
    @cython.locals(val=uint16_t,res=uint16_t)
    cdef inline void SUB(self, object)
    @cython.locals(sp=uint16_t,pc=uint16_t)
    cdef inline void RET(self)
    @cython.locals(sp=uint16_t,pc=uint16_t)
    cdef inline void CALL(self, uint16_t)
    cdef inline void JR(self, object)
    @cython.locals(opcode=int, shift=int, reg=int, ptr=uint16_t, res=int, val=int)
    cdef uint8_t execute(self, object, bint)
    cpdef void run(self)
    cdef void generateLog(self, object)
    @cython.locals(timer_inter=bint, cycles=uint8_t)
    cdef void update(self)
    @cython.locals(address=uint16_t, wrapper=object, next_address=uint16_t, instruction=object, cb=bint, cycles=uint8_t)
    cdef uint8_t executeNextOp(self)
    @cython.locals(flag=uint8_t)
    cpdef void setInterrupt(self, uint8_t)
    @cython.locals(total=int)
    cdef bint checkInterrupt(self)
    cdef void handleInterrupt(self, uint8_t, uint16_t)
    @cython.locals(temp=bint)
    cdef void blargg_update(self)
    @cython.locals(updog=bint, interrupt=bint)
    cdef void handleEvents(self)