"""
storage.py

Abstraction layer for file storage operations.
Supports both local filesystem and S3 storage.
"""

import os
import shutil
from datetime import datetime
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from typing import Optional

class StorageError(Exception):
    """Base class for storage-related errors"""
    pass

class StorageHandler(ABC):
    """Abstract base class for storage operations"""
    
    @abstractmethod
    def version_existing_file(self, key: str) -> Optional[str]:
        """Version existing file with timestamp"""
        pass
    
    @abstractmethod
    def read_file(self, key: str) -> pd.DataFrame:
        """Read file content"""
        pass
    
    @abstractmethod
    def write_file(self, key: str, data: pd.DataFrame) -> None:
        """Write file content"""
        pass

class LocalStorageHandler(StorageHandler):
    """Handles local file storage operations"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(os.path.join(self.base_path, 'current'), exist_ok=True)
        os.makedirs(os.path.join(self.base_path, 'archive'), exist_ok=True)
    
    def _get_full_path(self, key: str) -> str:
        """Convert key to full file path"""
        return os.path.join(self.base_path, key)
    
    def version_existing_file(self, key: str) -> Optional[str]:
        """
        Version existing file by moving it to archive directory with timestamp.
        
        Args:
            key: Original file path relative to base_path
            
        Returns:
            Optional[str]: Path to archived file if original exists, None otherwise
        """
        current_path = self._get_full_path(os.path.join('current', key))
        if not os.path.exists(current_path):
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(key)
        archive_key = f'archive/{os.path.splitext(filename)[0]}_{timestamp}.csv'
        archive_path = self._get_full_path(archive_key)
        
        shutil.copy2(current_path, archive_path)
        return archive_key
    
    def read_file(self, key: str) -> pd.DataFrame:
        """
        Read CSV file from local storage.
        
        Args:
            key: File path relative to base_path
            
        Returns:
            DataFrame containing file contents
            
        Raises:
            StorageError: If file reading fails
        """
        try:
            full_path = self._get_full_path(key)
            return pd.read_csv(full_path)
        except Exception as e:
            raise StorageError(f"Failed to read file {key}: {str(e)}")
    
    def write_file(self, key: str, data: pd.DataFrame) -> None:
        """
        Write DataFrame to CSV file in local storage.
        
        Args:
            key: File path relative to base_path
            data: DataFrame to write
            
        Raises:
            StorageError: If file writing fails
        """
        try:
            full_path = self._get_full_path(key)
            data.to_csv(full_path, index=False)
        except Exception as e:
            raise StorageError(f"Failed to write file {key}: {str(e)}")

class S3StorageHandler(StorageHandler):
    """Handles S3 storage operations"""
    
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3_client = boto3.client('s3')
    
    def version_existing_file(self, key: str) -> Optional[str]:
        """
        Version existing file in S3 by copying it to archive prefix with timestamp.
        
        Args:
            key: Original S3 key
            
        Returns:
            Optional[str]: Key of archived file if original exists, None otherwise
        """
        try:
            # Check if original file exists
            try:
                self.s3_client.head_object(Bucket=self.bucket, Key=key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return None
                raise
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(key)
            archive_key = f'archive/{os.path.splitext(filename)[0]}_{timestamp}.csv'
            
            self.s3_client.copy_object(
                Bucket=self.bucket,
                CopySource={'Bucket': self.bucket, 'Key': key},
                Key=archive_key
            )
            
            return archive_key
            
        except ClientError as e:
            raise StorageError(f"S3 operation failed: {str(e)}")
    
    def read_file(self, key: str) -> pd.DataFrame:
        """
        Read CSV file from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            DataFrame containing file contents
            
        Raises:
            StorageError: If file reading fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return pd.read_csv(response['Body'])
        except Exception as e:
            raise StorageError(f"Failed to read S3 file {key}: {str(e)}")
    
    def write_file(self, key: str, data: pd.DataFrame) -> None:
        """
        Write DataFrame to CSV file in S3.
        
        Args:
            key: S3 object key
            data: DataFrame to write
            
        Raises:
            StorageError: If file writing fails
        """
        try:
            csv_buffer = data.to_csv(index=False)
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=csv_buffer
            )
        except Exception as e:
            raise StorageError(f"Failed to write S3 file {key}: {str(e)}")

def get_storage_handler() -> StorageHandler:
    """
    Factory function to get appropriate storage handler based on environment.
    
    Returns:
        StorageHandler implementation
    """
    storage_type = os.getenv('STORAGE_TYPE', 'local').lower()
    
    if storage_type == 'local':
        base_path = os.getenv('LOCAL_STORAGE_PATH', 'local_testing')
        return LocalStorageHandler(base_path)
    elif storage_type == 's3':
        bucket = os.getenv('S3_BUCKET')
        if not bucket:
            raise ValueError("S3_BUCKET environment variable must be set when using S3 storage")
        return S3StorageHandler(bucket)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
