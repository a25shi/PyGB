import sys


class Memory:
    def __init__(self, cartridge, cartridge_type, cpu):
        self.ram = [0] * 0x8000  # cartridge ram, including banks (up to 4)
        self.hram = [0] * 128
        self.cartridge = cartridge
        self.rom_bank = 1  # rom banks for cartridge
        self.ram_bank = 0  # current ram bank
        self.ram_enabled = False
        self.rom_enabled = True

        # needs access to cpu
        self.cpu = cpu

        match cartridge_type:
            case num if 1 <= num <= 3:
                self.mbc = 1
            case num if 5 <= num <= 6:
                self.mbc = 2
            case _:
                raise ValueError(f"Unimplemented Cartridge Type of value: {cartridge_type}")

    def set(self, address, value):
        if address < 0:
            raise ValueError(f"Trying to write negative address {hex(address)} (value:{value})")

        if value is None:
            raise ValueError(f"Trying to write None to {hex(address)}")

        if address < 0x8000:
            self.handleROMSet(address, value)

        # writing to RAM
        elif 0xA000 <= address < 0xC000:
            if self.ram_enabled:
                temp = address - 0xA000
                offset = self.ram_bank * 0x2000
                self.ram[temp + offset] = value

        # write to Timer
        elif 0xFF04 <= address <= 0xFF07:
            if address == 0xFF04:
                self.cpu.timer.reset()
            elif address == 0xFF05:
                self.cpu.timer.TIMA = value
            elif address == 0xFF06:
                self.cpu.timer.TMA = value
            elif address == 0xFF07:
                self.cpu.timer.TAC = value & 0b111
                self.cpu.timer.resetCounter()

        # Internal HRAM
        elif 0xFF80 <= address < 0xFFFF:
            self.hram[address - 0xFF80] = value

        # Interrupt enable register
        elif address == 0xFFFF:
            self.cpu.i_enable = value


        else:
            raise ValueError(f"Disallowed write ({value}) to {hex(address)}")

    def get(self, address: int, counter: int = 1):
        if address < 0:
            raise ValueError(f"Trying to read negative address {hex(address)}")

        # Cartridge ROM
        if address < 0x4000:
            data = self.cartridge[address: address + counter]
            return int.from_bytes(data, sys.byteorder)

        # Cartridge ROM with memory map
        elif 0x4000 <= address < 0x8000:
            temp = address - 0x4000
            offset = self.rom_bank * 0x4000
            data = self.cartridge[temp + offset: temp + offset + counter]
            return int.from_bytes(data, sys.byteorder)

        # RAM access
        elif 0xA000 <= address < 0xC000:
            temp = address - 0xA000
            offset = self.ram_bank * 0x2000
            data = self.ram[temp + offset: temp + offset + counter]
            return int.from_bytes(data, sys.byteorder)

        # Timer
        elif 0xFF04 <= address <= 0xFF07:
            if address == 0xFF04:
                return self.cpu.timer.DIV
            elif address == 0xFF05:
                return self.cpu.timer.TIMA
            elif address == 0xFF06:
                return self.cpu.timer.TMA
            elif address == 0xFF07:
                return self.cpu.timer.TAC
            # does nothing, but makes the ide stop complaining
            return None

        # Internal HRAM
        elif 0xFF80 <= address < 0xFFFF:
            return self.hram[address - 0xFF80]

        # Interrupt enable register
        elif address == 0xFFFF:
            return self.cpu.i_enable

        else:
            raise ValueError(f"Disallowed read from {hex(address)}")

    # handles writing to address < 0x8000, usually associated with ROM and RAM settings
    # only mbc1 and mbc2 so far
    def handleROMSet(self, address, value):
        match self.mbc:
            # mbc1
            case 1:
                # ram control
                if address < 0x2000:
                    temp = value & 0b00001111
                    if temp == 0xA:
                        self.ram_enabled = True
                    else:
                        self.ram_enabled = False

                elif 0x2000 <= address < 0x4000:
                    # take lower 5 bits of value
                    temp = value & 0b00011111
                    # take upper 3 bits of rom_bank
                    self.rom_bank &= 0b11100000
                    # combine
                    self.rom_bank |= temp
                    # if selected register is 0, set to 1
                    if self.rom_bank == 0:
                        self.rom_bank = 1

                elif 0x4000 <= address < 0x6000:
                    # if on rom mode
                    if self.rom_enabled:
                        # take lower 5 bits of rom bank
                        self.rom_bank &= 0b00011111
                        # take upper 3 bits of value
                        temp = value & 0b11100000
                        # combine
                        self.rom_bank |= temp
                        if self.rom_bank == 0:
                            self.rom_bank = 1
                    # if on ram mode
                    else:
                        self.ram_bank = value & 0b11

                elif 0x6000 <= address < 0x8000:
                    # set rom/ram enable mode
                    self.rom_enabled = (value & 0b1) == 0
                    if self.rom_enabled:
                        self.ram_bank = 0
            # mbc2
            case 2:
                if address < 0x4000:
                    temp = value & 0b00001111
                    if (address & 0x100) == 0:
                        if temp == 0xA:
                            self.ram_enabled = True
                        else:
                            self.ram_enabled = False
                    else:
                        if temp == 0:
                            temp = 1
                        self.rom_bank = temp
