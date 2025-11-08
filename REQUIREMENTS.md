# Requirements for autosamplerT

This document lists the dependencies and setup steps for each supported operating system.

---


## Windows
- Python 3.8+
- sounddevice (install via pip)
- numpy (install via pip)
- scipy (install via pip)
- mido (install via pip)
- python-rtmidi (install via pip)
- pyyaml (install via pip)
- PortAudio (included with sounddevice pip install)

### Installation
```powershell
pip install sounddevice numpy scipy mido python-rtmidi pyyaml
```

---


## Linux
- Python 3.8+
- sounddevice (install via pip)
- numpy (install via pip)
- scipy (install via pip)
- mido (install via pip)
- python-rtmidi (install via pip)
- pyyaml (install via pip)
- PortAudio (system package required)

### Installation
```bash
sudo apt-get install libportaudio2
pip install sounddevice numpy scipy mido python-rtmidi pyyaml
```

---


## MacOS
- Python 3.8+
- sounddevice (install via pip)
- numpy (install via pip)
- scipy (install via pip)
- mido (install via pip)
- python-rtmidi (install via pip)
- pyyaml (install via pip)
- PortAudio (system package recommended)

### Installation
```bash
brew install portaudio
pip install sounddevice numpy scipy mido python-rtmidi pyyaml
```

---


## Notes
- For all OSes, it is recommended to use a virtual environment.
- Configuration is stored in `autosamplerT_config.yaml`.
- All dependencies for audio, MIDI, and YAML configuration are included above.
