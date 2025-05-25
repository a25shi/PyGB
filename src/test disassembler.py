from disassemble import Decoder, disassemble
from cartridge import get_cartridge_metadata
from cpu import *
from pathlib import Path

filename = '../test roms/super mario.gb'
metadata = get_cartridge_metadata(filename)
print(metadata)

# decoder = Decoder('Opcodes.json', filename, address=0, metadata=metadata)
# disassemble(decoder, 0x100, 30)
# cpu = CPU(filename, metadata)
# # Initial register values
# cpu.registers.__setitem__("AF", 0x01B0)
# cpu.registers.__setitem__("BC", 0x0013)
# cpu.registers.__setitem__("DE", 0x00D8)
# cpu.registers.__setitem__("HL", 0x014D)
# cpu.registers.__setitem__("SP", 0xFFFE)
# cpu.registers.__setitem__("PC", 0x0100)
# cpu.run()



