"""
test_enhanced_workout_processor.py

Tests for the workout processor Lambda function using shared fixtures.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import pytest
import boto3
import os
from enhanced_workout_processor import (
    WorkoutProcessor,
    WorkoutDataValidator,
    WorkoutProcessingError
)
from storage import StorageHandler
from .mocks import MockS3Operations, ErrorS3Operations

def test_workout_id_extraction(monkeypatch):
    """Test workout ID extraction from URLs."""
    # Mock the storage handler to return None
    monkeypatch.setenv('STORAGE_TYPE', 'local')
    monkeypatch.setenv('LOCAL_STORAGE_PATH', 'test_data')
    
    processor = WorkoutProcessor()
    
    assert processor.extract_workout_id(
        'http://www.mapmyfitness.com/workout/7434147697'
    ) == '7434147697'
    assert processor.extract_workout_id('invalid_url') is None
    assert processor.extract_workout_id(None) is None

def test_data_validation(sample_workout_data):
    """Test data validation functionality."""
    WorkoutDataValidator.validate_dataframe(sample_workout_data)
    
    invalid_df = sample_workout_data.drop('Activity Type', axis=1)
    with pytest.raises(WorkoutProcessingError):
        WorkoutDataValidator.validate_dataframe(invalid_df)

def test_process_file_with_new_records(sample_workout_data, monkeypatch):
    """Test processing file with new records."""
    class TestStorageHandler(StorageHandler):
        def version_existing_file(self, key):
            return 'archive/old_file.csv'
        
        def read_file(self, key):
            if 'archive' in key:
                return sample_workout_data.iloc[0:1].copy()
            return sample_workout_data.copy()
            
        def write_file(self, key, data):
            pass
    
    # Mock the storage handler factory
    import storage
    monkeypatch.setattr(storage, 'get_storage_handler', lambda: TestStorageHandler())
    
    processor = WorkoutProcessor()
    new_count, new_ids = processor.process_file('test.csv')
    
    assert new_count == 1
    assert '7434147698' in new_ids

def test_handler_success(s3_event, aws_credentials, mock_context, sample_workout_data, monkeypatch):
    """Test successful Lambda handler execution"""
    class TestStorageHandler(StorageHandler):
        def version_existing_file(self, key):
            return 'archive/old_file.csv'
        
        def read_file(self, key):
            if 'archive' in key:
                return sample_workout_data.iloc[0:1].copy()
            return sample_workout_data.copy()
            
        def write_file(self, key, data):
            pass
    
    # Mock the storage handler factory and boto3
    import storage
    monkeypatch.setattr(storage, 'get_storage_handler', lambda: TestStorageHandler())
    monkeypatch.setattr(boto3, 'client', lambda service: None)
    
    response = handler(s3_event, mock_context)
    
    assert response['statusCode'] == 200
    assert 'Successfully processed' in response['body']

def test_handler_error(s3_event, aws_credentials, mock_context, monkeypatch):
    """Test Lambda handler error handling"""
    class ErrorStorageHandler(StorageHandler):
        def version_existing_file(self, key):
            raise WorkoutProcessingError("Test error")
            
        def read_file(self, key):
            raise WorkoutProcessingError("Test error")
            
        def write_file(self, key, data):
            raise WorkoutProcessingError("Test error")
    
    # Mock the storage handler factory and boto3
    import storage
    monkeypatch.setattr(storage, 'get_storage_handler', lambda: ErrorStorageHandler())
    monkeypatch.setattr(boto3, 'client', lambda service: None)
    
    response = handler(s3_event, mock_context)
    
    assert response['statusCode'] == 400
    assert 'error' in response['body']

if __name__ == '__main__':
    pytest.main(['-v'])