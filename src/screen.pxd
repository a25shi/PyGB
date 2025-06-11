import cython

from libc.stdint cimport int16_t, int64_t, uint8_t, uint16_t, uint32_t, uint64_t

cdef class Screen:
    cdef uint8_t[8192] VRAM
    cdef uint8_t[0xA0] OAM
    cdef uint8_t SCY
    cdef uint8_t SCX
    cdef uint8_t WY
    cdef uint8_t WY_counter
    cdef uint8_t WX
    cdef uint8_t LY
    cdef uint8_t LYC
    cdef LCDCRegister LCDC
    cdef STATRegister STAT
    cdef Palette BGP
    cdef Palette OBP0
    cdef Palette OBP1
    cdef int scan_counter
    cdef uint8_t next_mode
    cdef cpu
    cdef int[160 * 144 * 3] screenBuffer
    cdef _screen
    cdef _last_draw
    cdef clock
    cdef font

    cpdef void update(self, uint64_t)
    cdef void drawScanline(self)
    @cython.locals(wx=int,x=int,xPos=int,yPos=int,offset=uint16_t,tile_index=int,color=uint32_t)
    cdef void renderBackground(self)
    @cython.locals(spriteheight=int,spritecount=int,n=int,x=int,y=int,attr=int,
    yflip=bint,xflip=bint,line=int,byte1=uint8_t,byte2=uint8_t,i=int,index=int,
    color_index=uint8_t,color=uint32_t,xpixel=int)
    cdef void renderSprites(self)
    @cython.locals(x=int,color=uint32_t)
    cdef void renderBlank(self)
    @cython.locals(offset=int)
    cdef inline void setPixelColor(self,int,int,uint32_t)
    @cython.locals(tile_addr=uint64_t, tile_index=int)
    cdef inline int getTile(self,int,int,uint16_t)
    @cython.locals(line=int,pixel_index=int,byte1=uint8_t,byte2=uint8_t,col_index=uint8_t)
    cdef inline uint32_t getTileColorBGP(self,int,int,int)
    cdef void updatePyGame(self)
    @cython.locals(prev=bint)
    cpdef void screenSet(self, uint16_t, uint8_t)
    cpdef uint16_t screenGet(self, uint16_t, uint8_t counter=*)
    @cython.locals(interrupt=bint)
    cdef inline checkLYC(self)
    @cython.locals(interrupt=bint)
    cdef inline setMode(self, uint8_t)


cdef class LCDCRegister:
    cdef uint8_t value
    cdef void set(self, uint64_t)
    cdef bint lcd_enable
    cdef bint windowmap_select
    cdef bint window_enable
    cdef bint tiledata_select
    cdef bint backgroundmap_select
    cdef readonly bint sprite_height
    cdef bint sprite_enable
    cdef bint background_enable
    cdef bint cgb_master_priority

    cdef uint16_t backgroundmap_offset
    cdef uint16_t windowmap_offset


cdef class STATRegister:
    cdef uint8_t value
    cdef uint8_t _mode
    cdef uint8_t set_mode(self, uint8_t)
    cdef uint8_t update_LYC(self, uint8_t, uint8_t)
    cdef void set(self, uint64_t)

cdef class Palette:
    cdef uint8_t value
    cdef uint32_t[4] lookup
    cdef uint32_t[4] palette_mem_rgb

    @cython.locals(x=uint16_t)
    cdef bint set(self, uint64_t)
    cdef uint8_t get(self)
    cdef inline uint32_t getcolor(self, uint8_t)