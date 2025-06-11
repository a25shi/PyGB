class Joypad:
    def __init__(self):
        # start with none selected
        self.value = 0b11001111
        # joypad is top 4 bits, directional is bottom 4
        self.joypad = 0xFF

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

    # def handleInput(self, key):
    #     pass