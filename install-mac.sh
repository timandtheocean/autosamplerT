#!/bin/bash
# AutosamplerT Installation Script for macOS
# Supports: macOS 10.15 (Catalina) and later

set -e

MIN_PYTHON_VERSION="3.8"
RECOMMENDED_PYTHON_VERSION="3.11"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== AutosamplerT Installation Script for macOS ===${NC}"
echo ""

# Function to compare version numbers
version_ge() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

# Check for Homebrew
check_homebrew() {
    if command -v brew &> /dev/null; then
        echo -e "${GREEN}Homebrew is installed.${NC}"
        return 0
    else
        echo -e "${YELLOW}Homebrew not found.${NC}"
        return 1
    fi
}

# Install Homebrew
install_homebrew() {
    echo ""
    echo -e "${YELLOW}Homebrew is recommended for managing Python and dependencies.${NC}"
    read -p "Would you like to install Homebrew? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}Installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon Macs
        if [[ $(uname -m) == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        
        echo -e "${GREEN}Homebrew installed successfully!${NC}"
    else
        echo -e "${YELLOW}Skipping Homebrew installation.${NC}"
        echo -e "${YELLOW}You may need to install Python manually.${NC}"
    fi
}

# Check for Python installation
check_python() {
    echo -e "${YELLOW}Checking for Python installation...${NC}"
    
    for cmd in python3 python; do
        if command -v $cmd &> /dev/null; then
            PYTHON_CMD=$cmd
            PYTHON_VERSION=$($cmd --version 2>&1 | grep -oE '([0-9]+\.[0-9]+\.[0-9]+)')
            echo -e "  ${GREEN}Found: $cmd (Python $PYTHON_VERSION)${NC}"
            
            if version_ge $PYTHON_VERSION $MIN_PYTHON_VERSION; then
                return 0
            else
                echo -e "  ${RED}Version $PYTHON_VERSION is too old (minimum: $MIN_PYTHON_VERSION)${NC}"
            fi
        fi
    done
    
    # Check system Python (macOS comes with Python but often outdated)
    if [ -f "/usr/bin/python3" ]; then
        PYTHON_VERSION=$(/usr/bin/python3 --version 2>&1 | grep -oE '([0-9]+\.[0-9]+\.[0-9]+)')
        echo -e "  ${YELLOW}Found system Python: $PYTHON_VERSION${NC}"
        
        if version_ge $PYTHON_VERSION $MIN_PYTHON_VERSION; then
            PYTHON_CMD="/usr/bin/python3"
            return 0
        else
            echo -e "  ${RED}System Python is too old (minimum: $MIN_PYTHON_VERSION)${NC}"
        fi
    fi
    
    return 1
}

# Install Python
install_python() {
    echo ""
    echo -e "${RED}Python $MIN_PYTHON_VERSION or higher not found.${NC}"
    read -p "Would you like to install Python $RECOMMENDED_PYTHON_VERSION? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Installation cancelled.${NC}"
        exit 1
    fi
    
    # Check if Homebrew is available
    if check_homebrew; then
        echo ""
        echo -e "${CYAN}Installing Python $RECOMMENDED_PYTHON_VERSION via Homebrew...${NC}"
        brew install python@3.11
        
        # Link Python if needed
        brew link python@3.11
        
        echo -e "${GREEN}Python installed successfully!${NC}"
    else
        # Try to install Homebrew first
        install_homebrew
        
        if check_homebrew; then
            echo ""
            echo -e "${CYAN}Installing Python $RECOMMENDED_PYTHON_VERSION via Homebrew...${NC}"
            brew install python@3.11
            brew link python@3.11
            echo -e "${GREEN}Python installed successfully!${NC}"
        else
            # Fallback to manual installation
            echo ""
            echo -e "${YELLOW}Opening Python download page...${NC}"
            open "https://www.python.org/downloads/macos/"
            echo ""
            echo -e "${YELLOW}Please install Python $RECOMMENDED_PYTHON_VERSION from the website.${NC}"
            echo -e "${YELLOW}After installation, run this script again.${NC}"
            exit 0
        fi
    fi
    
    # Re-check Python after installation
    if ! check_python; then
        echo -e "${RED}Python installation verification failed!${NC}"
        echo -e "${YELLOW}You may need to restart your terminal.${NC}"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    echo ""
    echo -e "${YELLOW}Checking for required system dependencies...${NC}"
    
    if check_homebrew; then
        echo -e "${CYAN}Installing audio libraries via Homebrew...${NC}"
        
        # Install PortAudio for sounddevice
        if ! brew list portaudio &> /dev/null; then
            echo -e "  Installing portaudio..."
            brew install portaudio
        else
            echo -e "  ${GREEN}portaudio already installed${NC}"
        fi
        
        # Install JACK (optional but recommended)
        if ! brew list jack &> /dev/null; then
            echo -e "  Installing jack..."
            brew install jack
        else
            echo -e "  ${GREEN}jack already installed${NC}"
        fi
        
        echo -e "${GREEN}System dependencies installed.${NC}"
    else
        echo -e "${YELLOW}Homebrew not available, skipping optional dependencies.${NC}"
        echo -e "${YELLOW}If audio issues occur, install Homebrew and run: brew install portaudio jack${NC}"
    fi
}

# Main installation
if ! check_homebrew; then
    echo -e "${YELLOW}Homebrew not found. Some features may require it.${NC}"
fi

if ! check_python; then
    install_python
fi

echo ""
echo -e "${GREEN}Using Python $PYTHON_VERSION ($PYTHON_CMD)${NC}"

# Install system dependencies
install_dependencies

# Check if virtual environment exists
echo ""
echo -e "${YELLOW}Checking for virtual environment...${NC}"

if [ -d ".venv" ]; then
    echo -e "  ${GREEN}Virtual environment already exists.${NC}"
    read -p "  Recreate it? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "  ${YELLOW}Removing old virtual environment...${NC}"
        rm -rf .venv
    else
        echo -e "  ${GREEN}Using existing virtual environment.${NC}"
    fi
fi

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo -e "  ${CYAN}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv .venv
    echo -e "  ${GREEN}Virtual environment created successfully!${NC}"
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate
echo -e "  ${GREEN}Virtual environment activated.${NC}"

# Upgrade pip
echo ""
echo -e "${YELLOW}Upgrading pip...${NC}"
python -m pip install --upgrade pip --quiet
echo -e "  ${GREEN}pip upgraded.${NC}"

# Install requirements
echo ""
echo -e "${YELLOW}Installing Python packages...${NC}"

if [ -f "REQUIREMENTS.md" ]; then
    echo -e "  ${CYAN}Installing from REQUIREMENTS.md...${NC}"
    
    # Package list
    packages=(
        "numpy"
        "scipy"
        "sounddevice"
        "soundfile"
        "mido"
        "python-rtmidi"
        "pyyaml"
    )
    
    for package in "${packages[@]}"; do
        echo -e "    Installing $package..." >&2
        if python -m pip install "$package" --quiet; then
            echo -e "      ${GREEN}✓ $package${NC}"
        else
            echo -e "      ${RED}✗ $package (failed)${NC}"
        fi
    done
else
    echo -e "  ${RED}REQUIREMENTS.md not found!${NC}"
    exit 1
fi

# Verify installation
echo ""
echo -e "${YELLOW}Verifying installation...${NC}"

python -c "
import sys
try:
    import numpy
    import scipy
    import sounddevice
    import soundfile
    import mido
    import yaml
    print('SUCCESS')
except ImportError as e:
    print(f'FAILED: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}All packages installed successfully! ✓${NC}"
else
    echo -e "  ${RED}Package verification failed!${NC}"
    exit 1
fi

# Test AutosamplerT
echo ""
echo -e "${YELLOW}Testing AutosamplerT...${NC}"
if python autosamplerT.py --help > /dev/null 2>&1; then
    echo -e "  ${GREEN}AutosamplerT is working! ✓${NC}"
else
    echo -e "  ${RED}AutosamplerT test failed!${NC}"
fi

# Success message
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo -e "${CYAN}To use AutosamplerT:${NC}"
echo -e "  ${NC}1. Activate virtual environment:${NC}"
echo -e "     ${YELLOW}source .venv/bin/activate${NC}"
echo -e "  ${NC}2. Run setup:${NC}"
echo -e "     ${YELLOW}python autosamplerT.py --setup all${NC}"
echo -e "  ${NC}3. Start sampling:${NC}"
echo -e "     ${YELLOW}python autosamplerT.py --script conf/test/test_single_note.yaml${NC}"
echo ""
echo -e "${CYAN}Documentation: See DOCUMENTATION.md${NC}"
echo ""
echo -e "${YELLOW}Note: On macOS, you may need to grant microphone permissions${NC}"
echo -e "${YELLOW}in System Preferences > Security & Privacy > Privacy > Microphone${NC}"
echo ""
