#!/usr/bin/env python3

import subprocess
import sys
import argparse
import os
from collections import deque
from pathlib import Path
import random

def ensure_pytest_aider_dir():
    """Create pytest_aider directory if it doesn't exist"""
    path = Path('pytest_aider')
    path.mkdir(exist_ok=True)
    return path

def parse_args():
    parser = argparse.ArgumentParser(description='Run pytest with AI-powered fixing')
    parser.add_argument('--max-iterations', type=int, default=10,
                      help='Maximum number of fix attempts (default: 10)')
    parser.add_argument('--tail-lines', type=int, default=20,
                      help='Number of output lines to show (default: 20)')
    parser.add_argument('--max-message-length', type=int, default=100000,
                      help='Maximum length of message to AI (default: 100000)')
    parser.add_argument('--test-file', type=str, default='test_github_stars.py',
                      help='Test file to run (default: test_github_stars.py)')
    parser.add_argument('--source-file', type=str, default='github_stars.py',
                      help='Source file to fix (default: github_stars.py)')
    return parser.parse_args()

# Get command line arguments
args = parse_args()

# Configuration constants
MAX_ITERATIONS = args.max_iterations
TAIL_LINES = args.tail_lines
MAX_MESSAGE_LENGTH = args.max_message_length

def get_tail(text, n=TAIL_LINES):
    """Get the last n lines of text"""
    lines = text.splitlines()
    return '\n'.join(lines[-n:]) if lines else ''

def run_pytest():
    result = subprocess.run(
        ["pytest", "-v", args.test_file],  # Added -v for verbose output
        capture_output=True,
        text=True
    )
    return result

INSTRUCTION_LIST = [
        "Follow the following pattern: 1. Evaluate (1a. What worked? 1b. What didn't work?) 2. Wildcard: Brainstorm radically different approaches 3. Problem: Identify issue 4. Information (4a. What do we know? 4b. How to gather more data? 4c. Where should we add more prints?) 5. Options: Generate solutions 6. Select: Choose best option 7. Execute: Implement solution",
        "Please add more tests when possible and it makes sense. Please remove tests that are not necessary.",
        "Please add comments to the code when it helps to explain what it does.",
        "Please remove comments from the code that are not necessary.",
        "Refactor the code to make it more readable and maintainable.",
        ]




def run_aider(pytest_output, error_summary):
    random_instruction = random.choice(INSTRUCTION_LIST)
    message = (
        f"Fix the following pytest failures:\n\n"
        f"Error Summary:\n{error_summary}\n\n"
        f"Full pytest output:\n{pytest_output}"
        "To modify files, use search replace blocks. "
        "When editing, make sure to actually change something. "
        "Don't just replace with the same text you searched for. "
    )
    message += f"\n\n{random_instruction}"
    print("message:", message)
    # Trim message if it exceeds maximum length
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[-MAX_MESSAGE_LENGTH:]
        # Ensure we don't cut in the middle of a line by finding the first newline
        first_newline = message.find('\n')
        if first_newline != -1:
            message = message[first_newline + 1:]
    # Ensure pytest_aider directory exists
    pytest_dir = ensure_pytest_aider_dir()
    
    # Set up history file paths in pytest_aider directory
    chat_history = pytest_dir / "chat_history.md"
    input_history = pytest_dir / "input_history"
    llm_history = pytest_dir / "llm_history"
    
    subprocess.run([
        "aider",
        args.test_file,
        args.source_file,
        "--message", message,
        "--restore-chat-history",
        "--chat-history-file", str(chat_history),
        "--input-history-file", str(input_history),
        "--llm-history-file" , str(llm_history),
        "--yes-always",
        "--no-detect-urls",
        "--no-suggest-shell-commands",
        "--verbose",
        # "--architect",
    ], check=True)

def get_error_summary(result):
    """Extract key information about test failures"""
    # Look for lines starting with FAILED or ERROR
    error_lines = [
        line for line in result.stdout.splitlines() 
        if line.startswith(('FAILED', 'ERROR'))
    ]
    
    # Get the test summary line (shows total tests/failures)
    summary_lines = [
        line for line in result.stdout.splitlines()
        if '===' in line and 'failed' in line.lower()
    ]
    
    return '\n'.join(error_lines + summary_lines)

def main():
    for i in range(MAX_ITERATIONS):
        print(f"\nIteration {i + 1}/{MAX_ITERATIONS}")
        print("-" * 40)
        
        # Run pytest
        result = run_pytest()
        
        # Save the complete output
        with open("pytest_output.txt", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)
        
        # Get the tail of the output
        output_tail = get_tail(result.stdout + "\n" + result.stderr)
        
        # Check if pytest failed
        if result.returncode != 0:
            print("\npytest failed. Error summary:")
            error_summary = get_error_summary(result)
            print(error_summary)
            print("\nLast few lines of output:")
            print(output_tail)
            print("\nRunning aider to fix it...")
            run_aider(result.stdout + "\n" + result.stderr, error_summary)
        else:
            print("\npytest succeeded! Last few lines of output:")
            print(output_tail)
            break
    else:
        print("\nMax iterations reached. Exiting.")

if __name__ == "__main__":
    main()
