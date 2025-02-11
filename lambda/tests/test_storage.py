"""
test_storage.py

Unit tests for storage handlers focusing on both local and S3 implementations.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import pytest
import pandas as pd
import os
import shutil
from datetime import datetime
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from storage import (
    StorageHandler,
    LocalStorageHandler,
    S3StorageHandler,
    StorageError,
    get_storage_handler
)

@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame({
        'workout_id': ['1234', '5678'],  # Keep as strings explicitly
        'date': ['2024-02-01', '2024-02-02'],
        'activity': ['Running', 'Cycling']
    }).astype({
        'workout_id': 'str',
        'date': 'str',
        'activity': 'str'
    })

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary directory structure for testing."""
    base_dir = tmp_path / "test_storage"
    (base_dir / "current").mkdir(parents=True)
    (base_dir / "archive").mkdir(parents=True)
    return str(base_dir)

class TestLocalStorageHandler:
    """Test suite for LocalStorageHandler"""

    def test_init_creates_directories(self, temp_storage_dir):
        """Test that initialization creates required directories."""
        # Remove directories to test creation
        shutil.rmtree(temp_storage_dir)
        
        handler = LocalStorageHandler(temp_storage_dir)
        assert os.path.exists(os.path.join(temp_storage_dir, 'current'))
        assert os.path.exists(os.path.join(temp_storage_dir, 'archive'))

    def test_version_existing_file(self, temp_storage_dir, sample_df):
        """Test versioning of existing files."""
        handler = LocalStorageHandler(temp_storage_dir)
        
        # Create a test file
        current_file = os.path.join(temp_storage_dir, 'current', 'test.csv')
        sample_df.to_csv(current_file, index=False)
        
        # Version the file
        archive_key = handler.version_existing_file('test.csv')
        
        assert archive_key is not None
        assert archive_key.startswith('archive/test_')
        assert archive_key.endswith('.csv')
        assert os.path.exists(os.path.join(temp_storage_dir, archive_key))

    def test_version_nonexistent_file(self, temp_storage_dir):
        """Test versioning when file doesn't exist."""
        handler = LocalStorageHandler(temp_storage_dir)
        archive_key = handler.version_existing_file('nonexistent.csv')
        assert archive_key is None

    def test_read_write_file(self, temp_storage_dir, sample_df):
        """Test reading and writing files."""
        handler = LocalStorageHandler(temp_storage_dir)
        
        # Write file with explicit dtypes
        test_key = 'current/test.csv'
        handler.write_file(test_key, sample_df)
        
        # Read file with explicit dtypes
        read_df = handler.read_file(test_key)
        
        # Ensure consistent dtypes before comparison
        for col in sample_df.columns:
            read_df[col] = read_df[col].astype(str)
        
        pd.testing.assert_frame_equal(sample_df, read_df)

    def test_read_nonexistent_file(self, temp_storage_dir):
        """Test reading a nonexistent file raises StorageError."""
        handler = LocalStorageHandler(temp_storage_dir)
        with pytest.raises(StorageError):
            handler.read_file('nonexistent.csv')

class TestS3StorageHandler:
    """Test suite for S3StorageHandler"""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        with patch('boto3.client') as mock_client:
            yield mock_client.return_value

    def test_version_existing_file(self, mock_s3_client):
        """Test versioning of existing S3 files."""
        handler = S3StorageHandler('test-bucket')
        
        # Mock successful head_object
        mock_s3_client.head_object.return_value = {}
        
        archive_key = handler.version_existing_file('test.csv')
        
        assert archive_key is not None
        assert archive_key.startswith('archive/test_')
        assert mock_s3_client.copy_object.called

    def test_version_nonexistent_file(self, mock_s3_client):
        """Test versioning when S3 file doesn't exist."""
        handler = S3StorageHandler('test-bucket')
        
        # Mock 404 response
        error_response = {'Error': {'Code': '404'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        archive_key = handler.version_existing_file('nonexistent.csv')
        assert archive_key is None

    def test_read_write_file(self, mock_s3_client, sample_df):
        """Test reading and writing S3 files."""
        handler = S3StorageHandler('test-bucket')
        
        # Create a proper mock response with BytesIO
        from io import BytesIO
        csv_content = BytesIO()
        sample_df.to_csv(csv_content, index=False, encoding='utf-8')
        csv_content.seek(0)
        
        mock_response = {'Body': csv_content}
        mock_s3_client.get_object.return_value = mock_response
        
        # Write file
        handler.write_file('test.csv', sample_df)
        assert mock_s3_client.put_object.called
        
        # Read file
        read_df = handler.read_file('test.csv')
        assert isinstance(read_df, pd.DataFrame)

    def test_s3_client_error(self, mock_s3_client):
        """Test handling of S3 client errors."""
        handler = S3StorageHandler('test-bucket')
        
        # Mock S3 error
        mock_s3_client.get_object.side_effect = ClientError(
            {'Error': {'Code': '500', 'Message': 'Test error'}},
            'GetObject'
        )
        
        with pytest.raises(StorageError):
            handler.read_file('test.csv')

def test_get_storage_handler_local():
    """Test storage handler factory with local configuration."""
    with patch.dict(os.environ, {'STORAGE_TYPE': 'local', 'LOCAL_STORAGE_PATH': '/tmp'}):
        handler = get_storage_handler()
        assert isinstance(handler, LocalStorageHandler)

def test_get_storage_handler_s3():
    """Test storage handler factory with S3 configuration."""
    with patch.dict(os.environ, {'STORAGE_TYPE': 's3', 'S3_BUCKET': 'test-bucket'}):
        handler = get_storage_handler()
        assert isinstance(handler, S3StorageHandler)

def test_get_storage_handler_invalid():
    """Test storage handler factory with invalid configuration."""
    with patch.dict(os.environ, {'STORAGE_TYPE': 'invalid'}):
        with pytest.raises(ValueError):
            get_storage_handler()