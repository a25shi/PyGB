class Memory:

    def __init__(self):
        self.ram = [0] * 8192  # 8kB
        self.hram = [0] * 127  # idk

    def set(self, address, value):
        if address < 0:
            raise ValueError(f"Trying to write negative address {address} (value:{value})")

        if value is None:
            raise ValueError(f"Trying to write None to {hex(address)}")

        if 0x0000 <= address < 0x8000:
            # Cartridge ROM or memory bank
            pass
        elif 0x8000 <= address < 0xA000:
            pass
        elif 0xA000 <= address < 0xC000:
            # Switchable RAM bank
            pass
        elif 0xC000 <= address < 0xE000:
            self.ram[address - 0xC000] = value
        elif 0xFE00 <= address < 0xFEA0:
            pass
        elif 0xFEA0 <= address < 0xFF00:
            # Unused area
            pass
        elif address == 0xFF00:
            pass
            return
        elif 0xFF01 <= address <= 0xFF02:
            # Serial transfer IO registers
            pass
        elif 0xFF04 <= address <= 0xFF07:
            pass
        elif address == 0xFF0F:
            pass
        elif 0xFF10 <= address <= 0xFF26:
            pass
            # info("Writing to sound register")
        elif 0xFF30 <= address <= 0xFF3F:
            pass
            # info("Writing to Waveform RAM")
        elif 0xFF40 <= address <= 0xFF45:
            pass
        elif address == 0xFF46:
            pass
        elif 0xFF47 <= address <= 0xFF4B:
            pass
        elif 0xFF4C <= address < 0xFF50:
            # unused memory area
            pass
        elif address == 0xFF50:
            raise Exception("TODO: disable boot rom")
        elif 0xFF51 <= address < 0xFF80:
            # unused memory area
            pass
        elif 0xFF80 <= address < 0xFFFF:
            self.hram[address - 0xFF80] = value
        elif address == 0xFFFF:
            pass
        else:
            raise ValueError(f"Disallowed write ({value}) to {hex(address)}")

    def get(self, address):
        if address < 0x8000:
            # Cartridge ROM or memory bank
            pass
        elif address < 0xA000:
            pass
        elif address < 0xC000:
            # Switchable RAM bank
            pass
        elif address < 0xE000:
            # info("Read from internal RAM")
            return self.ram[address - 0xC000]
        elif address < 0xFE00:
            # Echo of internal RAM. Not supported
            pass
        elif address < 0xFEA0:
            pass
        elif address < 0xFF00:
            # Empty unusable area
            pass
        elif address == 0xFF00:
            pass
        elif 0xFF04 <= address <= 0xFF07:
            pass
        elif address == 0xFF0F:
            pass
        elif 0xFF10 <= address <= 0xFF26:
            # info(f"Reading from sound register {hex(address)}")
            return 0
        elif 0xFF40 <= address <= 0xFF4B:
            pass
        elif 0xFF80 <= address < 0xFFFF:
            return self.hram[address - 0xFF80]
        elif address == 0xFFFF:
            pass
        else:
            raise ValueError(f"Disallowed read from {hex(address)}")
