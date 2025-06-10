from setuptools import setup
from Cython.Build import cythonize
list = ["cartridge.py", "memory.py", "disassemble.py", "opcodes.py", "timer.py", "screen.py", "cpu.py", "registers.py"]

setup(
    ext_modules=cythonize(list, compiler_directives={'language_level': "3"})
)
