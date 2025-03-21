#!/bin/bash

# Script to run the update_readme.py in the correct virtual environment

# Navigate to the project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install python-dotenv openai
else
    source venv/bin/activate
fi

# Create necessary directories if they don't exist
mkdir -p logs outputs/summaries

# Run the script
python scripts/update_readme.py

# Exit the virtual environment
deactivate

echo "Codebase summary update complete!" 