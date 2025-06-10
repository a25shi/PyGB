import cython
from libc.stdint cimport int64_t, uint8_t, uint16_t, uint32_t, uint64_t

cdef class Memory:
    cdef uint8_t[0x8000] ram
    cdef uint8_t[128] hram
    cdef uint8_t[8192] i_ram
    cdef uint8_t[0x10000] junk_rom
    cdef cartridge
    cdef uint16_t rom_bank
    cdef uint16_t ram_bank
    cdef bint ram_enabled
    cdef bint rom_enabled
    cdef uint16_t total_ram_banks
    cdef uint16_t total_rom_banks
    cdef uint16_t bank_bits
    cdef cpu
    cdef int cartridge_type
    cdef uint8_t mbc
    cdef void sync(self)
    @cython.locals(temp=uint16_t,offset=cython.int)
    cdef void set(self, uint16_t, uint8_t)
    @cython.locals(temp=uint16_t,offset=cython.int)
    cdef uint16_t get(self, uint16_t, uint8_t counter=*)
    @cython.locals(temp=uint8_t)
    cdef void handleROMSet(self, uint16_t, uint8_t)
    @cython.locals(offset=cython.int,n=cython.int)
    cdef void dma(self, uint8_t)
