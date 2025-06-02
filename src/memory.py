import sys
# from cpu import CPU
from cartridge import CartridgeMetadata
class Memory:
    def __init__(self, cartridge, cartridge_metadata: CartridgeMetadata , cpu):
        # TODO: fix ram
        self.ram = [0] * 0x8000  # cartridge ram, including banks (up to 4)
        self.hram = [0] * 128 # internal hram
        self.i_ram = [0] * 8192 # 8kb internal ram
        self.junk_rom = [0] * 0x10000 # all unimplemented features are stored here
        self.cartridge = cartridge
        self.rom_bank: int = 1  # rom banks for cartridge
        self.ram_bank: int = 0  # current ram bank
        self.ram_enabled: bool = False
        self.rom_enabled: bool = True
        self.total_ram_banks = 0

        # needs access to cpu
        self.cpu = cpu

        cartridge_type = cartridge_metadata.cartridge_type
        ram_size = cartridge_metadata.ram_size

        # Set mbc
        if cartridge_type == 0:
            self.mbc = 0
        elif 1 <= cartridge_type <= 3:
            self.mbc = 1
        elif 5 <= cartridge_type <= 6:
            self.mbc = 2
        else:
            raise ValueError(f"Unimplemented Cartridge Type of value: {cartridge_type}")

        # set RAM
        if ram_size in range(1, 3):
            self.total_ram_banks = 1
        elif ram_size == 3:
            self.total_ram_banks = 4
        elif ram_size == 4:
            self.total_ram_banks = 16
        elif ram_size == 5:
            self.total_ram_banks = 8

    def sync(self):
        # Timer tick
        if self.cpu.timer.tick(self.cpu.cycles):
            self.cpu.setInterrupt(2)

        # Screen tick
        self.cpu.screen.update(self.cpu.cycles)

        # Sync
        self.cpu.sync_cycles += self.cpu.cycles

        # Reset
        self.cpu.cycles = 0

    def set(self, address: int, value: int):
        value &= 0xFF
        if address < 0:
            raise ValueError(f"Trying to write negative address {hex(address)} (value:{value})")

        if value is None:
            raise ValueError(f"Trying to write None to {hex(address)}")
        self.sync()
        if address < 0x8000:
            self.handleROMSet(address, value)

        elif 0x8000 <= address < 0xA000:
            self.cpu.screen.VRAM[address - 0x8000] = value

        # writing to RAM
        elif 0xA000 <= address < 0xC000:
            if self.ram_enabled:
                temp = address - 0xA000
                offset = self.ram_bank * 0x2000
                self.ram[temp + offset] = value

        # internal ram
        elif 0xC000 <= address < 0xE000:
            self.i_ram[address - 0xC000] = value

        # echo ram
        elif 0xE000 <= address < 0xFE00:
            self.set(address - 0x2000, value)

        # OAM
        elif 0xFE00 <= address < 0xFEA0:
            self.cpu.screen.OAM[address - 0xFE00] = value

        # write to Timer
        elif 0xFF04 <= address <= 0xFF07:
            if address == 0xFF04:
                self.cpu.timer.reset()
            elif address == 0xFF05:
                self.cpu.timer.TIMA = value
            elif address == 0xFF06:
                self.cpu.timer.TMA = value
            elif address == 0xFF07:
                temp = self.cpu.timer.TAC
                self.cpu.timer.TAC = value & 0b111
                if temp != self.cpu.timer.TAC:
                    self.cpu.timer.resetCounter()

        elif address == 0xFF0F:
            self.cpu.i_flag = value

        # TODO: SCREEN
        elif 0xFF40 <= address <= 0xFF4B:
            if address == 0xFF40:
                self.cpu.screen.LCDC.set(value)
            elif address == 0xFF41:
                self.cpu.screen.STAT.set(value)
            elif address == 0xFF42:
                self.cpu.screen.SCY = value
            elif address == 0xFF43:
                self.cpu.screen.SCX = value
            elif address == 0xFF44:
                # read only
                return
            elif address == 0xFF45:
                self.cpu.screen.LYC = value
            elif address == 0xFF46:
                self.dma(value)
            # TODO implement
            elif address == 0xFF47:
                pass
            elif address == 0xFF48:
                pass
            elif address == 0xFF49:
                pass
            elif address == 0xFF4A:
                self.cpu.screen.WY = value
            elif address == 0xFF4B:
                self.cpu.screen.WX = value

            self.junk_rom[address] = value
        # Internal HRAM
        elif 0xFF80 <= address < 0xFFFF:
            self.hram[address - 0xFF80] = value

        # Interrupt enable register
        elif address == 0xFFFF:
            self.cpu.i_enable = value

        else:
            self.junk_rom[address] = value

    def get(self, address: int, counter: int = 1):
        if address < 0:
            raise ValueError(f"Trying to read negative address {hex(address)}")
        self.sync()
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

        # 8kB Video RAM
        elif 0x8000 <= address < 0xA000:
            temp = address - 0x8000
            data = self.cpu.screen.VRAM[temp: temp + counter]
            return int.from_bytes(data, sys.byteorder)

        # cartridge RAM access
        elif 0xA000 <= address < 0xC000:
            temp = address - 0xA000
            offset = self.ram_bank * 0x2000
            data = self.ram[temp + offset: temp + offset + counter]
            return int.from_bytes(data, sys.byteorder)

        # internal ram access
        elif 0xC000 <= address < 0xE000:
            temp = address - 0xC000
            data = self.i_ram[temp : temp + counter]
            return int.from_bytes(data, sys.byteorder)

        # echo internal ram
        elif 0xE000 <= address < 0xFE00:
            # Redirect to internal RAM
            return self.get(address - 0x2000, counter)

        # OAM
        elif 0xFE00 <= address < 0xFEA0:
            temp = address - 0xFEA0
            data = self.cpu.screen.OAM[temp : temp + counter]
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

        # interrupt flag
        elif address == 0xFF0F:
            return self.cpu.i_flag

        # TODO: screen
        elif 0xFF40 <= address <= 0xFF4B:
            if address == 0xFF40:
                return self.cpu.screen.LCDC.value
            elif address == 0xFF41:
                return self.cpu.screen.STAT.value
            elif address == 0xFF42:
                return self.cpu.screen.SCY
            elif address == 0xFF43:
                return self.cpu.screen.SCX
            elif address == 0xFF44:
                return self.cpu.screen.LY
                # return 0x90
            elif address == 0xFF45:
                return self.cpu.screen.LYC
            elif address == 0xFF46:
                return 0x00
            # TODO implement
            elif address == 0xFF47:
                pass
            elif address == 0xFF48:
                pass
            elif address == 0xFF49:
                pass
            elif address == 0xFF4A:
                return self.cpu.screen.WY
            elif address == 0xFF4B:
                return self.cpu.screen.WX

            data = self.junk_rom[address: address + counter]
            return int.from_bytes(data, sys.byteorder)

        # Internal HRAM
        elif 0xFF80 <= address < 0xFFFF:
            temp = address - 0xFF80
            data = self.hram[temp : temp + counter]
            return int.from_bytes(data, sys.byteorder)

            # Interrupt enable register
        elif address == 0xFFFF:
            return self.cpu.i_enable

        # return values for unimplemented stuff
        else:
            data = self.junk_rom[address : address + counter]
            return int.from_bytes(data, sys.byteorder)

    # handles writing to address < 0x8000, usually associated with ROM and RAM settings
    # only mbc1 and mbc2 so far
    def handleROMSet(self, address, value):
        # mbc1
        if self.mbc == 1:
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
                    self.ram_bank = (value & 0b11) % self.total_ram_banks


            elif 0x6000 <= address < 0x8000:
                # set rom/ram enable mode
                self.rom_enabled = (value & 0b1) == 0
                if self.rom_enabled:
                    self.ram_bank = 0
            # mbc2
        if self.mbc == 2:
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

    def dma(self, value):
        offset = value * 0x100
        for n in range(0xA0):
            self.set(0xFE00 + n, self.get(n + offset))

