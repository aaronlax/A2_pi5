#!/usr/bin/env python3
import os
import glob
import subprocess
import datetime
import sys
import fnmatch
import logging

# Import our custom logger configuration
try:
    # Add script directory to path to allow importing local modules
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(script_dir)
    from logger_config import setup_logger
except ImportError:
    # Fallback if logger_config.py is not available
    def setup_logger(name):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

# Set up logger
logger = setup_logger("CodebaseSummarizer")

try:
    from dotenv import load_dotenv
    from openai import OpenAI
except ImportError:
    logger.error("Missing required packages. Please run:")
    logger.error("python3 -m venv venv && source venv/bin/activate && pip install python-dotenv openai")
    sys.exit(1)

# Load environment variables from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in .env file")
    sys.exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Directory paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
OUTPUTS_DIR = os.path.join(ROOT_DIR, "outputs")
SUMMARIES_DIR = os.path.join(OUTPUTS_DIR, "summaries")

# Create directories if they don't exist
for directory in [LOGS_DIR, OUTPUTS_DIR, SUMMARIES_DIR]:
    os.makedirs(directory, exist_ok=True)

# File patterns to include (add or modify as needed)
INCLUDE_PATTERNS = [
    "*.py",
    "*.md",
    "requirements.txt",
    "client/*.py",
    "hardware/*.py",
    # Add more patterns as needed
]

# Files or directories to exclude
EXCLUDE_PATHS = [
    "venv/",
    "__pycache__/",
    ".git/",
    "outputs/",
    "logs/",
    "scripts/",
]

def should_include(file_path):
    """Check if file should be included based on exclusion rules"""
    for exclude in EXCLUDE_PATHS:
        if exclude in file_path:
            return False
    return True

def get_files_to_concatenate():
    """Get all files matching the include patterns and not in excluded directories"""
    all_files = []
    
    # Switch to the root directory
    os.chdir(ROOT_DIR)
    
    # First get all Python and text files from root directory
    for pattern in INCLUDE_PATTERNS:
        if '*/' not in pattern:  # Non-recursive patterns
            files = glob.glob(pattern)
            all_files.extend([f for f in files if should_include(f)])
    
    # Then walk through directories recursively
    for root, dirs, files in os.walk('.'):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not any(exclude in os.path.join(root, d) for exclude in EXCLUDE_PATHS)]
        
        for file in files:
            file_path = os.path.join(root, file)
            if should_include(file_path):
                # Check if file matches any of our patterns
                for pattern in INCLUDE_PATTERNS:
                    if fnmatch.fnmatch(file, pattern.split('/')[-1]):
                        all_files.append(file_path)
                        break
    
    return sorted(list(set(all_files)))  # Remove duplicates

def create_concatenated_file(files):
    """Concatenate all files into a single text file with headers"""
    output = []
    
    # Add timestamp and summary header
    output.append(f"# Codebase Concatenation - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"Total files: {len(files)}\n")
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                output.append(f"\n\n{'='*80}")
                output.append(f"FILE: {file_path}")
                output.append(f"{'='*80}\n")
                output.append(content)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")
            output.append(f"\n\nError reading {file_path}: {str(e)}")
    
    return "\n".join(output)

def generate_summary(content):
    """Generate a summary of the codebase using OpenAI"""
    system_prompt = """You are a helpful AI assistant that generates concise summaries of codebases.
    Analyze the provided concatenated codebase and generate a summary that includes:
    1. The project's purpose and main functionality
    2. Key components and how they interact
    3. Technologies and libraries used
    4. Any notable implementation details
    
    Format the response as markdown with appropriate sections and code references.
    """
    
    # Limit content length if needed (API token limitations)
    max_tokens = 100000  # Adjust based on your OpenAI plan
    if len(content) > max_tokens:
        logger.warning(f"Content too large, truncating to {max_tokens} characters")
        content = content[:max_tokens] + "...\n(content truncated due to size limitations)"
    
    try:
        logger.info("Calling OpenAI API for summary generation")
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=2000,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return f"Error generating summary: {str(e)}"

def update_readme(summary):
    """Create or update the README.md file with the generated summary"""
    readme_path = os.path.join(ROOT_DIR, "README.md")
    
    # Add timestamp and header
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    readme_content = f"""# A2: Pi5 Codebase

# Project Summary
> Last updated: {timestamp}

{summary}

## Auto-generated Summary
This README was automatically generated by a script that concatenates the codebase
and uses OpenAI's API to generate a summary.
"""
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    return readme_path

def main():
    logger.info("Starting codebase summarization process...")
    
    # Get files to concatenate
    files = get_files_to_concatenate()
    logger.info(f"Found {len(files)} files to process")
    
    # Concatenate files
    logger.info("Concatenating files...")
    concatenated_content = create_concatenated_file(files)
    
    # Save concatenated content to file
    date_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    concat_filename = os.path.join(SUMMARIES_DIR, f"concatenated_codebase_{date_str}.txt")
    with open(concat_filename, 'w', encoding='utf-8') as f:
        f.write(concatenated_content)
    logger.info(f"Concatenated content saved to {concat_filename}")
    
    # Generate summary using OpenAI
    logger.info("Generating summary with OpenAI...")
    summary = generate_summary(concatenated_content)
    
    # Update README.md
    logger.info("Updating README.md...")
    update_readme(summary)
    
    # Create output with updated README
    output_filename = os.path.join(SUMMARIES_DIR, f"codebase_summary_{date_str}.txt")
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(concatenated_content + "\n\n")
        f.write("="*80 + "\n")
        f.write("UPDATED README.md\n")
        f.write("="*80 + "\n\n")
        with open(os.path.join(ROOT_DIR, "README.md"), 'r', encoding='utf-8') as readme:
            f.write(readme.read())
    
    logger.info(f"Process complete. Output saved to {output_filename}")
    logger.info(f"README.md has been updated with a summary of the codebase")

if __name__ == "__main__":
    main() 