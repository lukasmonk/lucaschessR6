# Lucas Chess Conversion Project

This project converts the Lucas Chess application from PySide2 to PySide6 and updates the Python version from 3.7 (32bits) to 3.12 (64 bits). The conversion process is automated using a script located in the `__Convert` subdirectory.

## Table of Contents
- Introduction
- Requirements
- Installation
- Usage
- License

## Introduction
Lucas Chess is an open-source chess program designed for training, playing, and competing. This project aims to modernize the application by upgrading its dependencies to more recent versions.

## Requirements
- Python 3.12
- PySide6

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
1. Run the conversion script:
    ```sh
    python convert.py
    ```

2. The script will copy all source files and convert them to use PySide6.

3. Navigate back to the main directory and run Lucas Chess:
    ```sh
    cd ..
    python LucasR.py
    ```

## License
This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
