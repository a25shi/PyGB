from disassemble import Decoder, disassemble
from cartridge import get_cartridge_metadata
from pathlib import Path

print(get_cartridge_metadata('pokemon red.gb'))
decoder = Decoder('Opcodes.json', 'pokemon red.gb', address=0)
disassemble(decoder, 0x150, 150)
