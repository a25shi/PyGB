class Screen:
    def __init__(self, cpu):
        self.VRAM = [0] * 8192
        self.OAM = [0] * 0xA0
        self.LCDC = LCDCRegister()  # ($FF40)
        self.STAT = STATRegister()  # ($FF41)
        self.SCY = 0  # BG scroll y
        self.SCX = 0  # BG scroll x
        self.WY = 0  # Window Y Position ($FF4A)
        self.WX = 0  # Window X Position ($FF4B)
        self.LY = 0  # LCDC Y-coordinate ($FF44)
        self.LYC = 0  # LY Compare (if equal to LY, it causes STAT to set coincident flag) ($FF45)
        self.scan_counter = 456

        # store cpu
        self.cpu = cpu

    def update(self, cycles):
        # TODO: add lcd update

        if self.LCDC.lcd_enable:
            self.scan_counter -= cycles
        else:
            return

        # next scanline
        if self.scan_counter <= 0:
            self.LY += 1
            self.scan_counter = 456

            # Trigger v-blank
            if self.LY == 144:
                self.cpu.setInterrupt(0)

            # Reset LY once we reach the end
            elif self.LY > 153:
                self.LY = 0

            elif self.LY < 144:
                # TODO: add scanline render
                pass
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
