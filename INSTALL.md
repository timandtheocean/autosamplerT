# Installation Guide

Quick installation instructions for AutosamplerT on Windows, Linux, and macOS.

## Automated Installation (Recommended)

We provide automated installation scripts that handle Python installation and all dependencies.

### Windows

1. **Open PowerShell** (right-click Start menu → "Windows PowerShell" or "Terminal")

2. **Navigate to AutosamplerT directory:**
   ```powershell
   cd path\to\autosamplerT
   ```

3. **Run installation script:**
   ```powershell
   .\install.ps1
   ```

   If you get a security error, run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Follow prompts** - the script will:
   - Check for Python 3.8+ (or install via winget)
   - Create virtual environment
   - Install all required packages
   - Verify installation

### Linux

1. **Open Terminal**

2. **Navigate to AutosamplerT directory:**
   ```bash
   cd path/to/autosamplerT
   ```

3. **Make script executable:**
   ```bash
   chmod +x install.sh
   ```

4. **Run installation script:**
   ```bash
   ./install.sh
   ```

5. **Follow prompts** - the script will:
   - Detect your distribution (Ubuntu, Fedora, Arch, etc.)
   - Install Python 3.8+ if needed
   - Install system audio libraries
   - Create virtual environment
   - Install all required packages
   - Verify installation

**Supported distributions:**
- Ubuntu / Debian / Linux Mint / Pop!_OS
- Fedora / RHEL / CentOS
- Arch Linux / Manjaro
- openSUSE

### macOS

1. **Open Terminal** (Applications → Utilities → Terminal)

2. **Navigate to AutosamplerT directory:**
   ```bash
   cd path/to/autosamplerT
   ```

3. **Make script executable:**
   ```bash
   chmod +x install-mac.sh
   ```

4. **Run installation script:**
   ```bash
   ./install-mac.sh
   ```

5. **Follow prompts** - the script will:
   - Check for Homebrew (or offer to install it)
   - Install Python 3.8+ if needed
   - Install audio libraries (PortAudio, JACK)
   - Create virtual environment
   - Install all required packages
   - Verify installation

**Note:** macOS may require microphone permissions. Grant access in:
`System Preferences > Security & Privacy > Privacy > Microphone`

---

## Manual Installation

If you prefer manual installation or the automated scripts don't work:

### Prerequisites

- **Python 3.8 or higher** (3.11 recommended)
- **pip** (Python package manager)
- **Audio libraries** (platform-dependent)

### Step 1: Install Python

#### Windows
Download from [python.org](https://www.python.org/downloads/)
- ✓ Check "Add Python to PATH" during installation

#### Linux
```bash
# Ubuntu/Debian
sudo apt install python3 python3-venv python3-pip

# Fedora
sudo dnf install python3 python3-pip

# Arch
sudo pacman -S python python-pip
```

#### macOS
```bash
# Using Homebrew (recommended)
brew install python@3.11

# Or download from python.org
```

### Step 2: Install Audio Libraries

#### Windows
No additional libraries needed (uses Windows audio API)

#### Linux
```bash
# Ubuntu/Debian
sudo apt install libasound2-dev libjack-dev portaudio19-dev

# Fedora
sudo dnf install alsa-lib-devel jack-audio-connection-kit-devel portaudio-devel

# Arch
sudo pacman -S alsa-lib jack2 portaudio
```

#### macOS
```bash
brew install portaudio jack
```

### Step 3: Create Virtual Environment

```bash
# Navigate to AutosamplerT directory
cd path/to/autosamplerT

# Create virtual environment
python -m venv .venv

# Activate it
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows Command Prompt:
.venv\Scripts\activate.bat

# Linux/Mac:
source .venv/bin/activate
```

### Step 4: Install Python Packages

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install packages
pip install numpy scipy sounddevice soundfile mido python-rtmidi pyyaml
```

### Step 5: Verify Installation

```bash
# Test import
python -c "import numpy, scipy, sounddevice, soundfile, mido, yaml; print('Success!')"

# Test AutosamplerT
python autosamplerT.py --help
```

---

## First Run

After installation, configure your audio and MIDI devices:

```bash
# Activate virtual environment (if not already active)
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# Configure devices
python autosamplerT.py --setup all

# Test with single sample
python autosamplerT.py --script conf/test/test_single_note.yaml
```

---

## Troubleshooting

### "Python not found"
- **Windows:** Ensure Python is in PATH, or reinstall with "Add to PATH" checked
- **Linux/Mac:** Install Python using your package manager

### "Permission denied" (Linux/Mac)
```bash
chmod +x install.sh
# or
chmod +x install-mac.sh
```

### "sounddevice import error"
- **Windows:** Reinstall Python with "Install for all users"
- **Linux:** Install audio libraries (see Step 2 above)
- **Mac:** Install PortAudio: `brew install portaudio`

### "mido import error"
```bash
pip install python-rtmidi
```

### Virtual environment activation issues
- **PowerShell:** Set execution policy (see Windows section above)
- **Windows:** Try Command Prompt instead of PowerShell
- **Linux/Mac:** Ensure you're in the correct directory

### "No audio devices found"
- **Windows:** Check Windows Sound settings
- **Linux:** Ensure user is in `audio` group: `sudo usermod -a -G audio $USER`
- **Mac:** Grant microphone permissions in System Preferences

---

## Requirements

**Minimum:**
- Python 3.8+
- 2 GB RAM
- Audio interface with input
- 100 MB disk space

**Recommended:**
- Python 3.11+
- 8 GB RAM
- Professional audio interface
- MIDI interface (for MIDI control features)
- SSD for faster sample writing
- 10+ GB disk space (for large sample libraries)

---

## Getting Help

- **Documentation:** [DOCUMENTATION.md](DOCUMENTATION.md)
- **Quick Start:** [doc/QUICKSTART.md](doc/QUICKSTART.md)
- **Setup Guide:** [doc/SETUP.md](doc/SETUP.md)
- **Issues:** [GitHub Issues](https://github.com/timandtheocean/autosamplerT/issues)

---

## Next Steps

After successful installation:

1. **Read documentation:** [DOCUMENTATION.md](DOCUMENTATION.md)
2. **Configure devices:** [doc/SETUP.md](doc/SETUP.md)
3. **Try examples:** [doc/SCRIPTING.md](doc/SCRIPTING.md)
4. **Explore MIDI control:** [doc/MIDI_CONTROL_FEATURE.md](doc/MIDI_CONTROL_FEATURE.md)

---

*Last updated: November 11, 2025*
