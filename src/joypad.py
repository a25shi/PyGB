

class Joypad:
    def __init__(self):
        # start with none selected
        self.value = 0b11001111
        # joypad is top 4 bits, directional is bottom 4
        self.joypad = 0xFF

    def reset_joypadbit(self, bit):
        prevbit = (self.joypad >> bit) & 1
        self.joypad = self.joypad & ~(1 << bit)

        # Going from 1 to 0
        if prevbit:
            # Test top bit
            if bit > 3 and not ((self.value >> 5) & 1):
                return True
            # Test directional
            elif bit <= 3 and not ((self.value >> 4) & 1):
                return True

        return False

    def set_joypadbit(self, bit):
        self.joypad = self.joypad | (1 << bit)
        return False

    def getJoypad(self):
        return self.value
    def setJoypad(self, value):
        buttons = (value >> 5) & 1
        dpad = (value >> 4) & 1

        # set top 2 and bottom 4 bits to 1, keep buttons and dpad select
        value |= 0b11001111

        # append our joypad values
        if not buttons:
            value &= self.joypad >> 4
        elif not dpad:
            value &= self.joypad & 0xF

        # store
        self.value = value

    # Bit corresponds to the appropriate bit key in self.joypad
    def handleInput(self, bit, updog):
        interrupt = False
        # If keyup
        if updog:
            return self.set_joypadbit(bit)
        # If keydown
        else:
            return self.reset_joypadbit(bit)
