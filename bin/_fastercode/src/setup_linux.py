from setuptools import setup, Extension
from Cython.Build import cythonize

setup(ext_modules=cythonize([Extension("FasterCode", ["FasterCode.pyx"], libraries=["irina"], library_dirs=["."])]))
