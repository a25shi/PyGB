class Timer:
    def __init__(self):
        self.DIV: int = 0xabcc
        self.DIV_counter: int = 0
        self.TAC: int = 0
        self.TMA: int = 0
        self.TIMA: int = 0
        self.counter: int = 1024 # default freq is 4096

    def resetCounter(self):
        self.counter = self.getFreq()
    def getFreq(self):
        # get clock freq
        c_select = self.TAC & 0b11
        if c_select == 0:
            return 1024
        elif c_select == 1:
            return 16
        elif c_select == 2:
            return 64
        elif c_select == 3:
            return 256
        else:
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
            # reset timer counter while keeping overflow
            self.counter += self.getFreq()
            self.TIMA += 1

            if self.TIMA > 255:
                self.TIMA = self.TMA
                self.TIMA &= 0xFF
                # Return interrupt
                return True

        return False

    def reset(self):
        self.DIV_counter = 0
        self.DIV = 0