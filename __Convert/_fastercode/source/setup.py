from setuptools import setup
from Cython.Build import cythonize
import os
from setuptools import setup, Extension


# Configurar las variables de entorno para MinGW
os.environ["CC"] = "gcc"
os.environ["CXX"] = "g++"
os.environ["LDSHARED"] = "gcc -shared"
os.environ["CFLAGS"] = "-O3 -Wall -Wstrict-prototypes"
os.environ["LDFLAGS"] = ""

# Configurar la extens
extensions = [
    Extension(
        "FasterCode",
        ["FasterCode.pyx"],
        library_dirs=["."],      # Directorios de la biblioteca
        libraries=["irina"],     # Nombre de la biblioteca (sin 'lib' y sin extension)
        extra_compile_args=["-O3"],
        extra_link_args=[],
    )
]

setup(

    ext_modules=cythonize(extensions),
)
