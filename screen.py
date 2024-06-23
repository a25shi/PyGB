class Screen:
    def __init__(self):
        self.VRAM = [0] * 8192
        self.OAM = [0] * 0xA0
        self.LCDC = 0
        self.STAT = 0  # LCDC status
        self.SCY = 0  # BG scroll y
        self.SCX = 0  # BG scroll x
        self.LY = 0  # LCDC Y-coordinate
        self.LYC = 0  # LY Compare (if equal to LY, it causes STAT to set coincident flag)
        self.BGP = 0  # BG & Window Palette data
        self.OBP0 = 0  # Object (sprite) Palette 0 data
        self.OBP1 = 0  # Object (sprite) Palette 1 data
        self.WY = 0  # Window Y Position ($FF4A)
        self.WX = 0  # Window X Position ($FF4B)
        self.IE = 0  # Interrupt Enable ($FFFF)



