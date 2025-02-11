"""
conftest.py

Shared test fixtures for workout processor tests.
"""

import pytest
import pandas as pd
import os

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
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def s3_event():
    """Sample S3 event"""
    return {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'test.csv'}
            }
        }]
    }

@pytest.fixture
def mock_context():
    """Mock Lambda context"""
    class MockContext:
        def __init__(self):
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'
    return MockContext()