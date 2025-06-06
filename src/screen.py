import pygame

class Screen:
    def __init__(self, cpu):
        self.VRAM = [0] * 8192
        self.OAM = [0] * 0xA0
        self.LCDC = LCDCRegister()  # ($FF40)
        self.STAT = STATRegister()  # ($FF41)
        self.SCY: int = 0  # BG scroll y
        self.SCX: int = 0  # BG scroll x
        self.WY: int = 0  # Window Y Position ($FF4A)
        self.WX: int = 0  # Window X Position ($FF4B)
        self.LY: int = 0  # LCDC Y-coordinate ($FF44)
        self.LYC: int = 0  # LY Compare (if equal to LY, it causes STAT to set coincident flag) ($FF45)
        self.scan_counter: int = 456
        self.BGP = Palette(0xFC)
        self.OBP0 = Palette(0xFF)
        self.OBP1 = Palette(0xFF)

        # store cpu
        self.cpu = cpu
        self.WY_counter = 0

        # screen buffer
        self.screenBuffer = [0] * 160 * 144 * 3
        self._screen = pygame.display.set_mode((160 * 2, 144 * 2))
        self._screen.fill((0, 0, 0))

        # init pygame screen
        pygame.init()
        pygame.display.update()
        self._last_draw = pygame.time.get_ticks()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)


    def update(self, cycles):
        self.updateLCD()
        if self.LCDC.lcd_enable:
            self.scan_counter -= cycles
        else:
            return

        # next scanline
        if self.scan_counter <= 0:
            self.LY += 1
            self.scan_counter += 456

            # Trigger v-blank
            if self.LY == 144:
                self.cpu.setInterrupt(0)
                self.clock.tick()

            # Reset LY once we reach the end
            elif self.LY > 153:
                self.LY = 0

            elif self.LY < 144:
                self.drawScanline()
                self.updatePyGame()
    def drawScanline(self):
        if self.LCDC.background_enable:
            self.renderBackground()
        if self.LCDC.sprite_enable:
            self.renderSprites()

    def updateLCD(self):
        # reset if not enabled
        if not self.LCDC.lcd_enable:
            self.scan_counter = 456
            self.LY = 0
            self.STAT.set_mode(1)
            return

        mode2bounds: int = 376
        mode3bounds: int = 204
        interrupt = False
        prevmode = self.STAT.value & 0b11

        # mode 1
        if self.LY >= 144:
            newmode = 1
            self.STAT.set_mode(1)
            interrupt = self.STAT.value & (1 << 4)

        # mode 2
        elif self.scan_counter >= mode2bounds:
            newmode = 2
            self.STAT.set_mode(2)
            interrupt = self.STAT.value & (1 << 5)

        # mode 3
        elif self.scan_counter >= mode3bounds:
            newmode = 3
            self.STAT.set_mode(3)

        # mode 0
        else:
            newmode = 0
            self.STAT.set_mode(0)
            interrupt = self.STAT.value & (1 << 3)

        # new mode interrupt
        if interrupt & (prevmode != newmode):
            self.cpu.setInterrupt(1)

        # check coincidence flag
        interrupt = self.STAT.update_LYC(self.LYC, self.LY)
        if interrupt:
            self.cpu.setInterrupt(1)
    def renderBackground(self):
        wx = self.WX - 7

        for x in range(0, 160):
            # If we are in range of the window
            if self.LCDC.window_enable and self.WY <= self.LY and x >= wx:
                xPos = x - wx
                yPos = self.LY - self.WY
                offset = self.LCDC.windowmap_offset


            # Otherwise, default to background
            else:
                xPos = x + self.SCX
                yPos = self.SCY + self.LY
                offset = self.LCDC.backgroundmap_offset

            tile_index = self.getTile(xPos, yPos, offset)
            color = self.getTileColorBGP(tile_index, xPos, yPos)
            self.setPixelColor(x, self.LY, color)
    def renderSprites(self):
        spriteheight = 16 if self.LCDC.sprite_height else 8
        spritecount = 0

        # count which sprites to render
        for n in range(0x00, 0xA0, 4):
            y = self.OAM[n] - 16
            x = self.OAM[n + 1] - 8
            if y <= self.LY < y + spriteheight:
                # attributes
                tile_index = self.OAM[n + 2]
                attr = self.OAM[n + 3]
                yflip = (attr << 6) & 1
                xflip = (attr << 5) & 1

                line = self.LY - y
                if yflip:
                    line -= spriteheight
                    line *= -1
                line *= 2

                byte1 = self.VRAM[tile_index * 16 + line]
                byte2 = self.VRAM[tile_index * 16 + line + 1]

                for i in range(7, -1, -1):
                    index = i
                    if xflip:
                        index -= 7
                        index *= -1

                    color_index = ((byte2 >> index) & 1) << 1
                    color_index |= (byte1 >> index) & 1

                    if attr & 0b10000:
                        color = self.OBP1.getcolor(color_index)
                    else:
                        color = self.OBP0.getcolor(color_index)

                    # if sprite is transparent
                    if color == 0xFF:
                        continue

                    # TODO: implement sprite priority
                    # Set color
                    xpixel = 7 - i + x
                    self.setPixelColor(xpixel, self.LY, color)
                spritecount += 1

            if spritecount == 10:
                break
    def setPixelColor(self, x: int, y: int, color: int):
        offset = (y * 160 + x) * 3
        self.screenBuffer[offset] = color
        self.screenBuffer[offset + 1] = color
        self.screenBuffer[offset + 2] = color
    def getTile(self, x: int, y: int, offset: int):
        tile_addr = offset + y // 8 * 32 % 0x400 + x // 8 % 32 # tilemap offset + tileRow + tileCol
        tile_index = self.VRAM[tile_addr]
        # signed
        if not self.LCDC.tiledata_select:
            tile_index = (tile_index ^ 0x80) + 128
        return tile_index
    def getTileColorBGP(self, tile_index, x, y):
        line = 2 * (y % 8)
        # Rightmost bit is the leftmost pixel (bit 7 = pixel 0, bit 6 = pixel 1, etc.)
        pixel_index = ((x % 8) - 7) * -1

        byte1 = self.VRAM[tile_index * 16 + line]
        byte2 = self.VRAM[tile_index * 16 + line + 1]

        # byte 2 pixel is most significant, byte 1 is least
        col_index = ((byte2 >> pixel_index) & 1) << 1
        col_index |= (byte1 >> pixel_index) & 1
        return self.BGP.getcolor(col_index)
    def updatePyGame(self):
        try:
            current_time = pygame.time.get_ticks()
            # Here we limit FPS to get better performance
            if current_time > self._last_draw + 50:
                self._last_draw = current_time
                main_surface = pygame.image.frombuffer(bytearray(self.screenBuffer), (160, 144), "RGB")
                main_surface = pygame.transform.scale_by(main_surface, 2)
                self._screen.blit(main_surface, (0, 0))

                # Show fps
                fps = str(int(self.clock.get_fps()))
                fps_text = self.font.render(fps, False, pygame.Color("coral"))
                self._screen.blit(fps_text, (10, 10))

                # update
                pygame.display.update()

        except BaseException as e:
            raise Exception(f"Pygame frame error: {repr(e)}")

class STATRegister:
    def __init__(self):
        self.value: int = 0b1000_0000
        self._mode: int = 0

    def set(self, value):
        value &= 0b0111_1000  # Bit 7 is always set, and bit 0-2 are read-only
        self.value &= 0b1000_0111  # Preserve read-only bits and clear the rest
        self.value |= value  # Combine the two

    def update_LYC(self, LYC, LY):
        if LYC == LY:
            self.value |= 0b100  # Sets the LYC flag
            if self.value & 0b0100_0000:  # LYC interrupt enabled flag
                return True
        else:
            # Clear LYC flag
            self.value &= 0b1111_1011
        return False

    def set_mode(self, mode):
        if self._mode == mode:
            # Mode already set
            return False

        self._mode = mode
        self.value &= 0b11111100  # Clearing 2 LSB
        self.value |= mode  # Apply mode to LSB

        # Check if interrupt is enabled for this mode
        # Mode "3" is not interruptable
        if mode != 3 and self.value & (1 << (mode + 3)):
            return True

        return False

class LCDCRegister:
    def __init__(self):
        self.value: int = 0
        self.lcd_enable: int = 0
        self.windowmap_select: int = 0
        self.window_enable: int = 0
        self.tiledata_select: int = 0
        self.backgroundmap_select: int = 0
        self.sprite_height: int = 0
        self.sprite_enable: int = 0
        self.background_enable: int = 0
        self.backgroundmap_offset: int = 0x1800
        self.windowmap_offset: int = 0x1800

    def set(self, value: int):
        self.value = value

        self.lcd_enable = value & (1 << 7)
        self.windowmap_select = value & (1 << 6)
        self.window_enable = value & (1 << 5)
        self.tiledata_select = value & (1 << 4)
        self.backgroundmap_select = value & (1 << 3)
        self.sprite_height = value & (1 << 2)
        self.sprite_enable = value & (1 << 1)
        self.background_enable = value & (1 << 0)

        # All VRAM addresses are offset by 0x8000
        # Following addresses are 0x9800 and 0x9C00
        self.backgroundmap_offset = 0x1800 if self.backgroundmap_select == 0 else 0x1C00
        self.windowmap_offset = 0x1800 if self.windowmap_select == 0 else 0x1C00

class Palette:
    def __init__(self, value):
        self.value = 0
        self.lookup = [0] * 4
        self.palette_mem_rgb = [0xFF, 0x99, 0x55, 0x00]
        self.set(value)

    def set(self, value):
        if self.value == value:
            return False

        self.value = value
        for x in range(4):
            self.lookup[x] = self.palette_mem_rgb[(value >> x * 2) & 0b11]
        return True

    def get(self):
        return self.value

    def getcolor(self, i):
        return self.lookup[i]