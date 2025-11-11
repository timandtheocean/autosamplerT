#!/bin/bash
# AutosamplerT Installation Script for Linux
# Supports: Ubuntu, Debian, Fedora, Arch, openSUSE

set -e

MIN_PYTHON_VERSION="3.8"
RECOMMENDED_PYTHON_VERSION="3.11"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== AutosamplerT Installation Script for Linux ===${NC}"
echo ""

# Function to compare version numbers
version_ge() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
        DISTRO_VERSION=$DISTRIB_RELEASE
    else
        DISTRO="unknown"
    fi
    
    echo -e "${GREEN}Detected: $DISTRO $DISTRO_VERSION${NC}"
}

# Check for Python installation
check_python() {
    echo -e "${YELLOW}Checking for Python installation...${NC}"
    
    for cmd in python3 python; do
        if command -v $cmd &> /dev/null; then
            PYTHON_CMD=$cmd
            PYTHON_VERSION=$($cmd --version 2>&1 | grep -oP '(\d+\.\d+\.\d+)')
            echo -e "  ${GREEN}Found: $cmd (Python $PYTHON_VERSION)${NC}"
            
            if version_ge $PYTHON_VERSION $MIN_PYTHON_VERSION; then
                return 0
            else
                echo -e "  ${RED}Version $PYTHON_VERSION is too old (minimum: $MIN_PYTHON_VERSION)${NC}"
            fi
        fi
    done
    
    return 1
}

# Install Python based on distribution
install_python() {
    echo ""
    echo -e "${RED}Python $MIN_PYTHON_VERSION or higher not found.${NC}"
    read -p "Would you like to install Python $RECOMMENDED_PYTHON_VERSION? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Installation cancelled.${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${CYAN}Installing Python $RECOMMENDED_PYTHON_VERSION...${NC}"
    
    case $DISTRO in
        ubuntu|debian|linuxmint|pop)
            echo -e "  ${GREEN}Using apt package manager...${NC}"
            sudo apt update
            sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
            # For older Ubuntu versions without python3.11
            if [ $? -ne 0 ]; then
                echo -e "  ${YELLOW}Python 3.11 not available, installing python3...${NC}"
                sudo apt install -y python3 python3-venv python3-dev python3-pip
            fi
            # Install ALSA and JACK development libraries for sounddevice
            sudo apt install -y libasound2-dev libjack-dev portaudio19-dev
            ;;
            
        fedora|rhel|centos)
            echo -e "  ${GREEN}Using dnf/yum package manager...${NC}"
            if command -v dnf &> /dev/null; then
                sudo dnf install -y python3.11 python3-pip python3-devel
                # Install audio libraries
                sudo dnf install -y alsa-lib-devel jack-audio-connection-kit-devel portaudio-devel
            else
                sudo yum install -y python3.11 python3-pip python3-devel
                sudo yum install -y alsa-lib-devel jack-audio-connection-kit-devel portaudio-devel
            fi
            ;;
            
        arch|manjaro)
            echo -e "  ${GREEN}Using pacman package manager...${NC}"
            sudo pacman -Sy --noconfirm python python-pip
            # Install audio libraries
            sudo pacman -Sy --noconfirm alsa-lib jack2 portaudio
            ;;
            
        opensuse*|sles)
            echo -e "  ${GREEN}Using zypper package manager...${NC}"
            sudo zypper install -y python311 python311-pip python311-devel
            # Install audio libraries
            sudo zypper install -y alsa-devel libjack-devel portaudio-devel
            ;;
            
        *)
            echo -e "${RED}Unsupported distribution: $DISTRO${NC}"
            echo -e "${YELLOW}Please install Python $MIN_PYTHON_VERSION or higher manually.${NC}"
            echo -e "${YELLOW}Visit: https://www.python.org/downloads/${NC}"
            exit 1
            ;;
    esac
    
    echo -e "  ${GREEN}Python installed successfully!${NC}"
    
    # Re-check Python after installation
    if ! check_python; then
        echo -e "${RED}Python installation verification failed!${NC}"
        exit 1
    fi
}

# Main installation
detect_distro

if ! check_python; then
    install_python
fi

echo ""
echo -e "${GREEN}Using Python $PYTHON_VERSION ($PYTHON_CMD)${NC}"

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
