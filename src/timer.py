class Timer:
    def __init__(self):
        self.DIV = 0
        self.DIV_counter = 0
        self.TAC = 0
        self.TMA = 0
        self.TIMA = 0
        self.counter = 1024 # default freq is 4096

    def resetCounter(self):
        # get clock freq
        c_select = self.TAC & 0b11
        match c_select:
            case 0: self.counter = 1024
            case 1: self.counter = 16
            case 2: self.counter = 64
            case 3: self.counter = 256
            case _:
                raise IndexError()
    def tick(self, cycles):

        # iterate timer div register
        self.DIV_counter += cycles
        self.DIV += self.DIV_counter >> 8  # Add overflown bits to DIV
        self.DIV_counter &= 0xFF  # Remove the overflown bits
        self.DIV &= 0xFF

        # check timer enabled
        if self.TAC & 0b100 == 0:
            return False

        self.counter -= cycles
        if self.counter <= 0:
            # reset timer counter
            self.resetCounter()
            if self.TIMA == 255:
                self.TIMA = self.TMA
                # Return interrupt
                return True
            else:
                self.TIMA += 1

        return False

    def reset(self):
        self.DIV_counter = 0
        self.DIV = 0