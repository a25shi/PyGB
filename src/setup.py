from setuptools import setup
from Cython.Build import cythonize
list = ["cartridge.py", "memory.py", "disassemble.py", "opcodes.py", "timer.py", "screen.py",
        "cpu.py", "registers.py", "joypad.py"]

setup(
    ext_modules=cythonize(list, language_level=3)
)
