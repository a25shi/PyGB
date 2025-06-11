import pygame
import sys
class Screen:
    def __init__(self, cpu):
        self.VRAM = [0] * 8192
        self.OAM = [0] * 0xA0
        self.LCDC = LCDCRegister()  # ($FF40)
        self.STAT = STATRegister()  # ($FF41)
        self.SCY = 0  # BG scroll y
        self.SCX = 0  # BG scroll x
        self.WY = 0  # Window Y Position ($FF4A)
        self.WY_counter = 0 # Internal window counter
        self.WX = 0  # Window X Position ($FF4B)
        self.LY = 0  # LCDC Y-coordinate ($FF44)
        self.LYC = 0  # LY Compare (if equal to LY, it causes STAT to set coincident flag) ($FF45)
        self.scan_counter = 456
        self.BGP = Palette(0xFC)
        self.OBP0 = Palette(0xFF)
        self.OBP1 = Palette(0xFF)

        # store cpu
        self.cpu = cpu

        # screen buffer
        self.screenBuffer = [0] * 160 * 144 * 3
        self._screen = pygame.display.set_mode((160 * 2, 144 * 2))
        pygame.display.set_caption()
        self._screen.fill((0, 0, 0))

        # init pygame screen
        pygame.init()
        pygame.display.update()
        self._last_draw = pygame.time.get_ticks()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)

        # set up
        self.STAT.set_mode(0)
        self.next_mode = 2

    def update(self, cycles):
        if cycles == 0:
            return

        if self.LCDC.lcd_enable:
            self.scan_counter -= cycles
        else:
            return

        # next scanline
        if self.scan_counter <= 0:
            # If at the end, reset back to OAM scan (MODE 2)
            if self.LY == 153:
                self.LY = 0
                # OAM logic without inc (LY = 0 was our inc)
                self.setMode(2)
                self.scan_counter += 80
                self.next_mode = 3
                self.checkLYC()
            else:
                self.setMode(self.next_mode)
                # OAM (MODE 2)
                if self.STAT._mode == 2:
                    self.LY += 1
                    self.scan_counter += 80
                    self.next_mode = 3
                    self.checkLYC()

                # PIXEL DRAW (MODE 3)
                elif self.STAT._mode == 3:
                    self.scan_counter += 172
                    self.next_mode = 0

                # H-BLANK (MODE 0)
                elif self.STAT._mode == 0:
                    self.scan_counter += 204
                    self.drawScanline()
                    self.updatePyGame()
                    if self.LY < 143:
                        self.next_mode = 2
                    else:
                        self.next_mode = 1

                # V-BLANK (MODE 1)
                elif self.STAT._mode == 1:
                    self.scan_counter += 456
                    self.next_mode = 1
                    self.LY += 1
                    self.checkLYC()
                    # V-BLANK INTERRUPT
                    if self.LY == 144:
                        self.cpu.setInterrupt(0)
                        self.clock.tick()
    def checkLYC(self):
        interrupt = self.STAT.update_LYC(self.LYC, self.LY)
        if interrupt:
            self.cpu.setInterrupt(1)
    def setMode(self, newmode):
        interrupt = self.STAT.set_mode(newmode)
        if interrupt:
            self.cpu.setInterrupt(1)
    def drawScanline(self):
        # Tick window if we are within
        if self.LCDC.window_enable and self.WY <= self.LY and self.WX - 7 < 160:
            self.WY_counter += 1
        if self.LCDC.background_enable:
            self.renderBackground()
        else:
            self.renderBlank()
        if self.LCDC.sprite_enable:
            self.renderSprites()
        if self.LY == 143:
            self.WY_counter = -1
    def renderBlank(self):
        for x in range(0, 160):
            color = self.BGP.getcolor(0)
            self.setPixelColor(x, self.LY, color)
    def renderBackground(self):
        wx = self.WX - 7
        for x in range(0, 160):
            # If we are in range of the window
            if self.LCDC.window_enable and self.WY <= self.LY and x >= wx:
                xPos = x - wx
                yPos = self.WY_counter
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
                # If spriteheight is 16, ignore bit 0
                if spriteheight == 16:
                    tile_index &= 0b11111110
                attr = self.OAM[n + 3]
                yflip = (attr >> 6) & 1
                xflip = (attr >> 5) & 1

                line = self.LY - y
                if yflip:
                    line -= spriteheight
                    line *= -1
                    # no idea why this fixes yflip
                    line -= 1
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
    def setPixelColor(self, x, y, color):
        offset = (y * 160 + x) * 3
        self.screenBuffer[offset] = color
        self.screenBuffer[offset + 1] = color
        self.screenBuffer[offset + 2] = color
    def getTile(self, x, y, offset):
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
    def screenGet(self, address, counter = 1):
        if 0x8000 <= address < 0xA000:
            temp = address - 0x8000
            data = self.VRAM[temp: temp + counter]
            return int.from_bytes(data, sys.byteorder)
        elif 0xFE00 <= address < 0xFEA0:
            temp = address - 0xFE00
            data = self.OAM[temp : temp + counter]
            return int.from_bytes(data, sys.byteorder)
        elif address == 0xFF40:
            return self.LCDC.value
        elif address == 0xFF41:
            return self.STAT.value
        elif address == 0xFF42:
            return self.SCY
        elif address == 0xFF43:
            return self.SCX
        elif address == 0xFF44:
            return self.LY
            # return 0x90
        elif address == 0xFF45:
            return self.LYC
        elif address == 0xFF46:
            return 0x00
        elif address == 0xFF47:
            return self.BGP.get()
        elif address == 0xFF48:
            return self.OBP0.get()
        elif address == 0xFF49:
            return self.OBP1.get()
        elif address == 0xFF4A:
            return self.WY
        else:
            return self.WX
    def screenSet(self, address, value):
        if 0x8000 <= address < 0xA000:
            self.VRAM[address - 0x8000] = value
        elif 0xFE00 <= address < 0xFEA0:
            self.OAM[address - 0xFE00] = value
        elif address == 0xFF40:
            prev = self.LCDC.lcd_enable
            self.LCDC.set(value)
            if prev and not self.LCDC.lcd_enable:
                self.scan_counter = 0
                self.setMode(0)
                self.LY = 0
            elif not prev and self.LCDC.lcd_enable:
                pass
        elif address == 0xFF41:
            self.STAT.set(value)
        elif address == 0xFF42:
            self.SCY = value
        elif address == 0xFF43:
            self.SCX = value
        elif address == 0xFF44:
            # read only
            return
        elif address == 0xFF45:
            self.LYC = value
        elif address == 0xFF47:
            self.BGP.set(value)
        elif address == 0xFF48:
            self.OBP0.set(value)
        elif address == 0xFF49:
            self.OBP1.set(value)
        elif address == 0xFF4A:
            self.WY = value
        elif address == 0xFF4B:
            self.WX = value

class STATRegister:
    def __init__(self):
        self.value = 0b1000_0000
        self._mode = 0

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
        self.value = 0
        self.lcd_enable = 0
        self.windowmap_select = 0
        self.window_enable = 0
        self.tiledata_select = 0
        self.backgroundmap_select = 0
        self.sprite_height = 0
        self.sprite_enable = 0
        self.background_enable = 0
        self.backgroundmap_offset = 0x1800
        self.windowmap_offset = 0x1800

    def set(self, value):
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