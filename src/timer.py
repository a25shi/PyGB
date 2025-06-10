import cython
class Timer:
    def __init__(self):
        self.DIV = 0xAD
        self.DIV_counter = 0
        self.TAC = 0
        self.TMA = 0
        self.TIMA = 0
        self.counter = 1024 # default freq is 4096

    def timerGet(self, address):
        if address == 0xFF04:
            return self.DIV
        elif address == 0xFF05:
            return self.TIMA
        elif address == 0xFF06:
            return self.TMA
        else:
            return self.TAC
    def timerSet(self, address, value):
        if address == 0xFF04:
            self.reset()
        elif address == 0xFF05:
            self.TIMA = value
        elif address == 0xFF06:
            self.TMA = value
        elif address == 0xFF07:
            temp = self.TAC
            self.TAC = value & 0b111
            if temp != self.TAC:
                self.resetCounter()
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
        if cycles == 0:
            return False

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
        self.resetCounter()