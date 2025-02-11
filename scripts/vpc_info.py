import boto3
import json
from pprint import pprint

def get_vpc_info():
    """Get information about existing VPCs and their components."""
    ec2 = boto3.client('ec2')
    
    # Get VPCs
    vpcs = ec2.describe_vpcs()
    
    vpc_info = {}
    for vpc in vpcs['Vpcs']:
        vpc_id = vpc['VpcId']
        vpc_info[vpc_id] = {
            'CIDR': vpc['CidrBlock'],
            'IsDefault': vpc.get('IsDefault', False),
            'Tags': vpc.get('Tags', []),
            'Subnets': []
        }
        
        # Get subnets for this VPC
        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        for subnet in subnets['Subnets']:
            vpc_info[vpc_id]['Subnets'].append({
                'SubnetId': subnet['SubnetId'],
                'CIDR': subnet['CidrBlock'],
                'AvailabilityZone': subnet['AvailabilityZone'],
                'Tags': subnet.get('Tags', [])
            })
    
    return vpc_info

if __name__ == "__main__":
    print("\n🔍 Checking VPC Configuration:")
    print("=" * 50)
    
    vpc_info = get_vpc_info()
    
    for vpc_id, info in vpc_info.items():
        print(f"\nVPC: {vpc_id}")
        print(f"CIDR: {info['CIDR']}")
        print(f"Default VPC: {'Yes' if info['IsDefault'] else 'No'}")
        
        # Print any tags (especially Name tag)
        for tag in info['Tags']:
            if tag['Key'] == 'Name':
                print(f"Name: {tag['Value']}")
        
        print("\nSubnets:")
        for subnet in info['Subnets']:
            print(f"  - {subnet['SubnetId']} ({subnet['AvailabilityZone']})")
            print(f"    CIDR: {subnet['CIDR']}")
            # Print subnet name if it exists
            for tag in subnet.get('Tags', []):
                if tag['Key'] == 'Name':
                    print(f"    Name: {tag['Value']}")