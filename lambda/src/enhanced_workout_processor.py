"""
enhanced_workout_processor.py

Enhanced Lambda function for processing workout data files with:
- Structured error handling
- File versioning
- Improved data validation
- Detailed logging

Supports both local testing and S3 deployment.
"""

import json
import logging
from typing import Dict, Any, Tuple, List, Set
from datetime import datetime
import re
import os
from storage import get_storage_handler, StorageError
import pandas as pd

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class WorkoutProcessingError(Exception):
    """Base class for workout processing errors"""
    pass

class DataValidationError(WorkoutProcessingError):
    """Raised when data validation fails"""
    pass

class WorkoutDataValidator:
    """Validates workout data structure and content"""
    
    REQUIRED_COLUMNS = {
        'Date Submitted',
        'Workout Date',
        'Activity Type',
        'Calories Burned (kcal)',
        'Distance (mi)',
        'Workout Time (seconds)',
        'Link'
    }
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> None:
        """Validate DataFrame structure and content"""
        # Check required columns
        missing_cols = WorkoutDataValidator.REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise DataValidationError(f"Missing required columns: {missing_cols}")
        
        # Check for empty DataFrame
        if df.empty:
            raise DataValidationError("DataFrame is empty")
        
        # Validate Link format (should contain workout ID)
        invalid_links = df[~df['Link'].str.contains(r'/workout/\d+', na=False)]
        if not invalid_links.empty:
            logger.warning(f"Found {len(invalid_links)} rows with invalid workout links")
            logger.debug(f"Invalid links: {invalid_links['Link'].tolist()}")

class WorkoutProcessor:
    """Processes workout data and identifies new records"""
    
    def __init__(self):
        """Initialize processor with storage handler"""
        self.storage = get_storage_handler()
    
    def extract_workout_id(self, url: str) -> str:
        """Extract workout ID from URL"""
        if pd.isna(url):
            return None
        match = re.search(r'/workout/(\d+)', url)
        return match.group(1) if match else None
    
    def process_file(self, file_key: str) -> Tuple[int, List[str]]:
        """
        Process new workout file and identify new records.
        
        Args:
            file_key: Key/path to the new file
            
        Returns:
            Tuple containing count of new records and list of new workout IDs
        """
        # Version existing file
        current_key = os.path.join('current', file_key)
        archived_key = self.storage.version_existing_file(current_key)
        
        # Read new file
        new_df = self.storage.read_file(file_key)
        WorkoutDataValidator.validate_dataframe(new_df)
        
        # Extract workout IDs
        processed_df = new_df.copy()
        processed_df['workout_id'] = processed_df['Link'].apply(self.extract_workout_id)
        processed_df = processed_df.dropna(subset=['workout_id'])
        
        # If we have an archived file, compare with it
        new_workout_ids = set(processed_df['workout_id'])
        if archived_key:
            old_df = self.storage.read_file(archived_key)
            old_df['workout_id'] = old_df['Link'].apply(self.extract_workout_id)
            existing_ids = set(old_df['workout_id'].dropna())
            new_workout_ids = new_workout_ids - existing_ids
        
        # Write new file to current location
        self.storage.write_file(current_key, new_df)
        
        return len(new_workout_ids), list(new_workout_ids)

def send_sns_notification(topic_arn: str, new_records: int, file_key: str) -> None:
    """Send SNS notification about processing results"""
    try:
        import boto3
        sns_client = boto3.client('sns')
        message = {
            'file_processed': file_key,
            'new_records': new_records,
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
        
        sns_client.publish(
            TopicArn=topic_arn,
            Message=json.dumps(message, indent=2),
            Subject=f'Workout Processing Complete: {new_records} new records'
        )
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {str(e)}")
        # Don't raise - notification failure shouldn't fail the whole process

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for processing workout files"""
    try:
        # Extract file information
        if os.getenv('STORAGE_TYPE') == 'local':
            # For local testing, expect file path in event
            key = event.get('file_key', 'user2632022_workout_history.csv')
        else:
            # For S3 trigger
            key = event['Records'][0]['s3']['object']['key']
        
        logger.info(f"Processing file {key}")
        
        # Process file
        processor = WorkoutProcessor()
        new_record_count, new_workout_ids = processor.process_file(key)
        
        # Send notification if in S3 mode
        if os.getenv('STORAGE_TYPE') == 's3':
            topic_arn = f"arn:aws:sns:{context.invoked_function_arn.split(':')[3]}:{context.invoked_function_arn.split(':')[4]}:workout-processing-notifications"
            send_sns_notification(topic_arn, new_record_count, key)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully processed {new_record_count} new workouts',
                'file_processed': key,
                'new_workout_ids': new_workout_ids
            })
        }
        
    except (WorkoutProcessingError, StorageError) as e:
        error_msg = f"Processing error: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg})
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
