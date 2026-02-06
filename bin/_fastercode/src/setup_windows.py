from setuptools import setup, Extension
from Cython.Build import cythonize
import sys
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IRINA_LIB_DIR = os.path.join(BASE_DIR, "irina")
IRINA_LIB = "irina"   # libirina.lib

extensions = [
    Extension(
        name="FasterCode",
        sources=["FasterCode.pyx"],
        libraries=[IRINA_LIB],
        library_dirs=[IRINA_LIB_DIR],
        include_dirs=[
            os.path.join(BASE_DIR, "source", "irina"),
        ],
        extra_compile_args=[
            "/O2",        # optimización segura
            "/DNDEBUG",
        ],
        language="c",
    )
]

setup(
    name="FasterCode",
    version="1.0.0",
    description="High-performance Cython bindings for Irina chess engine (Windows/MSVC)",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": "3",
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "cdivision": True,
        },
        annotate=False,
    ),
    zip_safe=False,
)
