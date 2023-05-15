from disassemble import Decoder, disassemble
from pathlib import Path

decoder = Decoder('Opcodes.json', 'pokemon gold.gbc', address=0)
disassemble(decoder, 0x150, 500)
