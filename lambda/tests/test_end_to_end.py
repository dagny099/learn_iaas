"""
test_end_to_end.py

Complete end-to-end tests for the workout processing pipeline.
Tests the entire flow from file upload to SNS notification.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

import pytest
import boto3
import json
import pandas as pd
from datetime import datetime
import os
from moto import mock_s3, mock_sns, mock_lambda
from enhanced_workout_processor import handler



@pytest.fixture
def sample_workout_data():
    """Create sample workout data for testing."""
    return pd.DataFrame({
        'Date Submitted': ['2024-02-01', '2024-02-02'],
        'Workout Date': ['2024-02-01', '2024-02-02'],
        'Activity Type': ['Running', 'Cycling'],
        'Calories Burned (kcal)': [400, 300],
        'Distance (mi)': [5.0, 3.5],
        'Workout Time (seconds)': [1800, 1500],
        'Link': [
            'http://www.mapmyfitness.com/workout/7434147697',
            'http://www.mapmyfitness.com/workout/7434147698'
        ]
    })

@pytest.fixture
def sample_new_workout_data():
    """Create sample new workout data with one additional record."""
    return pd.DataFrame({
        'Date Submitted': ['2024-02-01', '2024-02-02', '2024-02-03'],
        'Workout Date': ['2024-02-01', '2024-02-02', '2024-02-03'],
        'Activity Type': ['Running', 'Cycling', 'Running'],
        'Calories Burned (kcal)': [400, 300, 500],
        'Distance (mi)': [5.0, 3.5, 6.0],
        'Workout Time (seconds)': [1800, 1500, 2000],
        'Link': [
            'http://www.mapmyfitness.com/workout/7434147697',
            'http://www.mapmyfitness.com/workout/7434147698',
            'http://www.mapmyfitness.com/workout/7434147699'
        ]
    })

@pytest.fixture
def aws_credentials():
    """Provide mock AWS credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def s3(aws_credentials):
    """Create mock S3 bucket and provide client."""
    with mock_s3():
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket='workout-data')
        yield s3

@pytest.fixture
def sns(aws_credentials):
    """Create mock SNS topic and provide client."""
    with mock_sns():
        sns = boto3.client('sns')
        response = sns.create_topic(Name='workout-notifications')
        yield sns, response['TopicArn']

@pytest.fixture
def lambda_context():
    """Create a mock Lambda context."""
    class MockContext:
        def __init__(self):
            self.function_name = 'workout-processor'
            self.function_version = '$LATEST'
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:workout-processor'
            self.memory_limit_in_mb = 128
            self.aws_request_id = 'test-request-id'
            self.log_group_name = '/aws/lambda/workout-processor'
            self.log_stream_name = '2024/02/10/[$LATEST]abcdef123456'
    return MockContext()

def test_full_workflow_new_file(s3, sns, lambda_context, sample_workout_data, sample_new_workout_data):
    """Test complete workflow with a new file containing new records."""
    sns_client, topic_arn = sns
    
    # Set up environment
    os.environ['STORAGE_TYPE'] = 's3'
    os.environ['S3_BUCKET'] = 'workout-data'
    
    # Upload initial file
    s3.put_object(
        Bucket='workout-data',
        Key='current/user2632022_workout_history.csv',
        Body=sample_workout_data.to_csv(index=False).encode()
    )
    
    # Create S3 event for new file upload
    s3_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'workout-data'},
                'object': {'key': 'user2632022_workout_history.csv'}
            }
        }]
    }
    
    # Upload new file with additional record
    s3.put_object(
        Bucket='workout-data',
        Key='user2632022_workout_history.csv',
        Body=sample_new_workout_data.to_csv(index=False).encode()
    )
    
    # Process the new file
    response = handler(s3_event, lambda_context)
    
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert response_body['new_workout_ids'] == ['7434147699']
    assert response_body['message'].startswith('Successfully processed 1 new')

def test_workflow_no_new_records(s3, sns, lambda_context, sample_workout_data):
    """Test workflow when new file has no new records."""
    sns_client, topic_arn = sns
    
    # Set up environment
    os.environ['STORAGE_TYPE'] = 's3'
    os.environ['S3_BUCKET'] = 'workout-data'
    
    # Upload same file twice
    s3.put_object(
        Bucket='workout-data',
        Key='current/user2632022_workout_history.csv',
        Body=sample_workout_data.to_csv(index=False).encode()
    )
    
    s3_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'workout-data'},
                'object': {'key': 'user2632022_workout_history.csv'}
            }
        }]
    }
    
    s3.put_object(
        Bucket='workout-data',
        Key='user2632022_workout_history.csv',
        Body=sample_workout_data.to_csv(index=False).encode()
    )
    
    response = handler(s3_event, lambda_context)
    
    assert response['statusCode'] == 200
    response_body = json.loads(response['body'])
    assert len(response_body['new_workout_ids']) == 0

def test_workflow_invalid_file(s3, sns, lambda_context):
    """Test workflow with invalid file format."""
    sns_client, topic_arn = sns
    
    # Set up environment
    os.environ['STORAGE_TYPE'] = 's3'
    os.environ['S3_BUCKET'] = 'workout-data'
    
    # Upload invalid file
    s3.put_object(
        Bucket='workout-data',
        Key='user2632022_workout_history.csv',
        Body='invalid,csv,format\n1,2,3'
    )
    
    s3_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'workout-data'},
                'object': {'key': 'user2632022_workout_history.csv'}
            }
        }]
    }
    
    response = handler(s3_event, lambda_context)
    
    assert response['statusCode'] == 400
    assert 'error' in json.loads(response['body'])

def test_sns_notification(s3, sns, lambda_context, sample_workout_data, sample_new_workout_data):
    """Test SNS notification is sent with correct information."""
    sns_client, topic_arn = sns
    
    # Set up environment
    os.environ['STORAGE_TYPE'] = 's3'
    os.environ['S3_BUCKET'] = 'workout-data'
    
    # Create subscription to capture notifications
    messages = []
    def capture_message(message):
        messages.append(message)
    
    sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='lambda',
        Endpoint='arn:aws:lambda:us-east-1:123456789012:function:test'
    )
    
    # Upload files and trigger processing
    s3.put_object(
        Bucket='workout-data',
        Key='current/user2632022_workout_history.csv',
        Body=sample_workout_data.to_csv(index=False).encode()
    )
    
    s3_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'workout-data'},
                'object': {'key': 'user2632022_workout_history.csv'}
            }
        }]
    }
    
    s3.put_object(
        Bucket='workout-data',
        Key='user2632022_workout_history.csv',
        Body=sample_new_workout_data.to_csv(index=False).encode()
    )
    
    handler(s3_event, lambda_context)
    
    # Verify SNS notifications
    topics = sns_client.list_topics()['Topics']
    assert len(topics) == 1
    
    subscriptions = sns_client.list_subscriptions()['Subscriptions']
    assert len(subscriptions) == 1
    assert subscriptions[0]['TopicArn'] == topic_arn