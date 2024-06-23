from disassemble import Decoder, disassemble
from cartridge import get_cartridge_metadata
from cpu import *

from pathlib import Path

filename = 'pokemon red.gb'
print(get_cartridge_metadata(filename))
# decoder = Decoder('Opcodes.json', 'pokemon red.gb', address=0)
# disassemble(decoder, 0x100, 5)
cpu = CPU(filename)
cpu.run()
