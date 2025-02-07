# ES Dummy

## About

A tool for Emulation Station that allows users to populate all specified console libraries with dummy ROM titles. Subsequently all generated dummy ROM titles are Python scripts capable of downloading and extracting their respective ROM titles from a user-provided archive source.

This is intended to be used on a Steam Deck with EmuDeck installed. Additional capabilities for running on Windows also exist but currently require some changes to the configuration file.

## Installation

### Steam Deck:
1. Enter Desktop mode
2. Open Konsole
3. Check that Python is installed:
```
python -V
```
5. Create a virtual environment for PIP:
```
python -m venv .venv
```
6. Activate newly created virtual environment:
```
source .venv/bin/activate
```
7. Install PIP:
```
python -m pip install --upgrade pip
python -m pip --version
```
8. Install all required dependencies with PIP:
```
pip install click pyyaml requests internetarchive pugixml bs4 py7zr
```
9. Clone this repository:
```
git clone https://github.com/uxiebl/ES-Dummy.git
```
10. Add ROM sources to config.yaml (archive URLs or Internet Archive identifies are accepted)
11. Run the script to populate library:
```
.venv/bin/python ES-Dummy/ES-Dummy.py populate-all
```

PAGE UNDER CONSTRUCTION 
