from disassemble import Decoder, disassemble
from pathlib import Path

decoder = Decoder('Opcodes.json', Path('pokemon gold.gbc').read_bytes(), address=0)
disassemble(decoder, 0x150, 500)
print(hex(decoder.getSize()))

