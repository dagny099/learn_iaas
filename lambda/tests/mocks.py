"""
mocks.py

Mock classes for testing the workout processor.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import pandas as pd
from enhanced_workout_processor import WorkoutProcessingError

class MockS3Operations:
    """Mock S3 operations for testing"""
    def __init__(self, bucket):
        self.bucket = bucket
        
    def version_existing_file(self, key):
        return 'archive/old_file.csv'
    
    def read_csv_file(self, key):
        # Access the sample_workout_data fixture through the request object
        data = self._get_test_data()
        if 'archive' in key:
            return data.iloc[0:1].copy()
        return data.copy()
    
    def _get_test_data(self):
        """Helper method to get test data - will be overridden in tests"""
        return pd.DataFrame()  # Empty DataFrame by default

class ErrorS3Operations:
    """Mock S3 operations that raise errors for testing"""
    def __init__(self, bucket):
        self.bucket = bucket
        
    def version_existing_file(self, key):
        raise WorkoutProcessingError("Test error")
    
    def read_csv_file(self, key):
        raise WorkoutProcessingError("Test error")