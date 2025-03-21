#!/bin/bash

# Script to run the update_readme.py in the correct virtual environment

# Navigate to the project root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Get the project name (use the directory name by default)
PROJECT_NAME=${PROJECT_NAME:-$(basename "$(pwd)")}
export PROJECT_NAME

# Set environment variables if needed
export EXCLUDE_PATTERNS_FILE="$SCRIPT_DIR/exclude_patterns.txt"

# Check if .env file exists, create if not
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    if [ -z "$OPENAI_API_KEY" ]; then
        echo "Please enter your OpenAI API key:"
        read API_KEY
        echo "OPENAI_API_KEY=$API_KEY" > .env
    else
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" > .env
    fi
fi

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
echo "Generating codebase summary for $PROJECT_NAME..."
python scripts/update_readme.py

# Check if the script was successful
if [ $? -ne 0 ]; then
    echo "Error running script" >&2
else
    echo "Codebase summary update complete!"
    if [ -f "README.md" ]; then
        echo "Updated README.md file. You may want to review it."
    fi
fi

# Exit the virtual environment
deactivate 