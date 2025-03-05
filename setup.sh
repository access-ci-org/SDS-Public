#!/usr/bin/env bash

PYTHON_VERSION="3.12.4"
ENV_NAME="SDS_ENV"

# Displays a colored message (using ANSI escape codes) to distinguish echo from regular command output
colored_echo () {
    BLUE='\e[34m'   # Light blue
    NC="\e[0m"      # No Color
    echo -e "${BLUE}$1${NC}"
}

# Function to check if a command exists
command_exists () {
    type "$1" &> /dev/null ;
}

# Echo red warning if most recent command exited with error (exit code != 0)
check_status () {
    if [ $? -ne 0 ]; then
        echo -e "\e[31mCommand failed.\e[0m"
    fi
}

# Function to determine operating system and architecture for proper installation of conda
determine_os () {
    case "$OSTYPE" in
        msys*)
            OS_NAME="Windows"
            ARCH="x86-64"
            ;;
        darwin*)
            OS_NAME="MacOSX"
            ARCH=$(uname -m)
            ;;
        linux*)
            OS_NAME="Linux"
            ARCH=$(uname -m)
            ;;
        *)
            colored_echo "Unable to determine operating system."
            ;;
    esac
}

# Check if conda is installed
if command_exists conda; then
    colored_echo "Conda is already installed."
else
    determine_os
    colored_echo "OS Name: $OS_NAME"
    colored_echo "Architecture: $ARCH"
    CONDA_FILE="Miniconda3-latest-$OS_NAME-$ARCH.sh"    # Fetch the proper version of Miniconda

    colored_echo "Conda not found. Installing miniconda3..."

    # Check for wget
    if ! command_exists wget; then
        colored_echo "wget not found. Installing Wget..."

        # # Check for pip first, since it's OS independent
        # if command_exists pip; then
        #     colored_echo "installing wget with pip"
        #     pip install wget

        if [ "$OS_NAME" = "Windows" ]; then
            # Placeholder for now
            colored_echo "Please install wget manually."
            exit 1
            
        elif [ "$OS_NAME" = "MacOSX" ]; then
            colored_echo "installing wget with brew"
            brew install wget

        elif [ "$OS_NAME" = "Linux" ]; then
            # Determine which package manager their distro uses
            if command_exists apt-get; then
                sudo apt-get update
                sudo apt-get install -y wget
                
            elif command_exists yum; then
                sudo yum update
                sudo yum install -y wget

            elif command_exists dnf; then
                sudo dnf update
                sudo dnf install -y wget

            else
                colored_echo "Unknown package manager. Please install wget manually."
                exit 1
            fi
        else
            colored_echo "Unknown operating system. Please install wget manually."
            exit 1
        fi
    fi

    # Download the latest Miniconda installer script
    wget https://repo.anaconda.com/miniconda/$CONDA_FILE -O conda.sh 
    check_status


    # Run the miniconda installer
    bash conda.sh -b
    check_status

    # Determine the shell being used. Source the {shell}rc to ensure conda is initialized/path is updated
    # NOTE: You can just do both instead of doing either or for MAC/LINUX but Windows is weird
    case "$SHELL" in
        *bash*)
            ~/miniconda3/bin/conda init bash
            source ~/.bashrc
            check_status

            ;;
        *zsh*)
            ~/miniconda3/bin/conda init zsh
            source ~/.zshrc
            check_status
            ;;
    esac
    check_status


    colored_echo "Conda installed successfully"

    # Clean up after itself
    rm -rf conda.sh
fi

# clean conda
colored_echo "Cleaning conda"
conda clean -a -y
check_status

# Create a virtual environment
colored_echo "Creating a virtual Python environment..."
conda create --prefix=./env/$ENV_NAME python=$PYTHON_VERSION -y
check_status
colored_echo "Virtual environment '$ENV_NAME' created successfully"


colored_echo "Updating conda env configs..."
# remove env prefix from shell prompts
conda config --set env_prompt '({name})'
check_status
# add env to config (env is now found by --name, -n)
conda config --append envs_dirs ./env/
check_status
colored_echo "Conda env configs updated"

# Activate the virtual environment
colored_echo "Activating your new virtual environment..."
conda run -n  $ENV_NAME
check_status
conda activate $ENV_NAME
colored_echo "Virtual environment '$ENV_NAME' activated"

colored_echo "Installing Requirements..."
# Install requirements
conda env update -f env.yaml --prune
check_status
colored_echo "Requirements Installed"
