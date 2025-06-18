# Lucas Chess Conversion Project

This project converts the Lucas Chess application from PySide2 to PySide6 and updates the Python version from 3.7 (32bits) to 3.13 (64 bits). The conversion process is automated using a script located in the `__Convert` subdirectory.

## Table of Contents
- Introduction
- Requirements
- Installation
- Usage
- License

## Introduction
Lucas Chess is an open-source chess program designed for training, playing, and competing. This project aims to modernize the application by upgrading its dependencies to more recent versions.

## Requirements
- Python 3.13
- PySide6
- chardet
- sortedcontainers
- python-chess
- pillow
- cython
- psutil
- polib
- deep_translator
- requests
- urllib3
- idna
- certifi
- bs4


## Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/lukasmonk/lucaschessR6.git
    cd lucaschessR6
    ```

2. Navigate to the `__Convert` directory:
    ```sh
    cd __Convert
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage
1. Create FasterCode library
    ```sh
    cd _fastercode
    ```
    windows:
        edit the first 8 lines of runVC64.bat, indicating the python version and the path to mingw
    ```
   runVC64.bat
    ```

    linux:
    ```
   linux64.sh
    ```

2. Run the conversion script, the script will copy all source files and convert them to use PySide6:
    ```sh
    python convert.py
    ```

3. Navigate back to the main directory:
    ```sh
    cd ../bin
    ```

4. If the OS is Linux:
    ```sh
    cd OS/linux
    sh ./RunEngines
    cd ../..
    ```

5. Launch of the programme:
    ```sh
    python LucasR.py
    ```

## License
This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
