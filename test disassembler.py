import disassemble
from pathlib import Path

decoder = disassemble.Decoder.create('Opcodes.json', Path('pokemon gold.gbc').read_bytes(), address=0)
disassemble.disassemble(decoder, 0x150, 16)


