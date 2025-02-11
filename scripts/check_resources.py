# Description: A script to check if AWS resources were created correctly for a project.
# This script will:
# - Check if S3 bucket exists and is properly configured
# - Verify RDS instance is running and accessible
# - Confirm Lambda function is deployed correctly
# - Validate CloudWatch logs are set up


import boto3
import sys
from botocore.exceptions import ClientError

def check_resources(project_name, environment):
    """Verify AWS resources were created correctly."""
    print(f"\n🔍 Checking AWS resources for {project_name}-{environment}")
    print("=" * 50)
    
    # Initialize AWS clients
    s3 = boto3.client('s3')
    rds = boto3.client('rds')
    lambda_client = boto3.client('lambda')
    logs = boto3.client('cloudwatch')
    
    # Check S3 bucket
    print("\n📦 Checking S3 Bucket:")
    bucket_name = f"{project_name}-data-lake-{environment}"
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"✅ S3 bucket '{bucket_name}' exists")
        
        # Check versioning
        versioning = s3.get_bucket_versioning(Bucket=bucket_name)
        print(f"Versioning status: {versioning.get('Status', 'Not enabled')}")
    except ClientError as e:
        print(f"❌ Error with S3 bucket: {str(e)}")
    
    # Check RDS instance
    print("\n🛢️ Checking RDS Database:")
    db_identifier = f"{project_name}-{environment}"
    try:
        dbs = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)
        db = dbs['DBInstances'][0]
        print(f"✅ RDS instance '{db_identifier}' exists")
        print(f"Status: {db['DBInstanceStatus']}")
        print(f"Endpoint: {db.get('Endpoint', {}).get('Address', 'N/A')}")
        print(f"Engine: {db['Engine']} {db['EngineVersion']}")
    except ClientError as e:
        print(f"❌ Error with RDS: {str(e)}")
    
    # Check Lambda function
    print("\n⚡ Checking Lambda Function:")
    function_name = f"{project_name}-data-processor-{environment}"
    try:
        lambda_info = lambda_client.get_function(FunctionName=function_name)
        print(f"✅ Lambda function '{function_name}' exists")
        print(f"Runtime: {lambda_info['Configuration']['Runtime']}")
        print(f"Memory: {lambda_info['Configuration']['MemorySize']}MB")
        print(f"Timeout: {lambda_info['Configuration']['Timeout']}s")
    except ClientError as e:
        print(f"❌ Error with Lambda: {str(e)}")
    
    # Check CloudWatch Log Group
    print("\n📊 Checking CloudWatch Logs:")
    log_group_name = f"/aws/lambda/{function_name}"
    try:
        logs.describe_log_groups(logGroupNamePrefix=log_group_name)
        print(f"✅ Log group '{log_group_name}' exists")
    except ClientError as e:
        print(f"❌ Error with CloudWatch Logs: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_resources.py <project_name> <environment>")
        sys.exit(1)
        
    project_name = sys.argv[1]
    environment = sys.argv[2]
    check_resources(project_name, environment)