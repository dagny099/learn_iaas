"""
test_locally.py

Script to test the Lambda function locally.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.append(str(src_path))

from enhanced_workout_processor import handler

def main():
    # Set up environment for local testing
    os.environ['STORAGE_TYPE'] = 'local'
    os.environ['LOCAL_STORAGE_PATH'] = str(Path(__file__).parent / 'local_testing')
    
    # Create event for local testing
    event = {
        'file_key': 'user2632022_workout_history.csv'
    }
    
    # Process the file
    response = handler(event, None)
    print("\nLambda Response:")
    print(f"Status Code: {response['statusCode']}")
    print(f"Body: {response['body']}")

if __name__ == '__main__':
    main()
