import json
import boto3
from botocore.config import Config
import os

# Initialize S3 client with proper config
s3 = boto3.client('s3', region_name='us-west-2', config=Config(
    connect_timeout=5,
    read_timeout=5,
    retries={'max_attempts': 2}
))

# Get environment variables
FEEDBACK_BUCKET = os.environ['FEEDBACK_BUCKET']

def lambda_handler(event, context):
    try:
        # Get user ID from path parameters
        user_id = event.get('pathParameters', {}).get('userId')
        if not user_id:
            user_id = 'anonymous'  # Default user ID if not provided
        
        print(f"Fetching history for user: {user_id}")
        
        # List objects in the feedback bucket with user_id prefix
        response = s3.list_objects_v2(
            Bucket=FEEDBACK_BUCKET,
            Prefix=f"{user_id}/"
        )
        
        # Extract feedback files
        history_items = []
        if 'Contents' in response:
            for item in response['Contents']:
                if item['Key'].endswith('_feedback.json'):
                    # Get the feedback file content
                    feedback_obj = s3.get_object(
                        Bucket=FEEDBACK_BUCKET,
                        Key=item['Key']
                    )
                    feedback_data = json.loads(feedback_obj['Body'].read().decode('utf-8'))
                    
                    # Add to history items (now including the base64 image)
                    history_items.append({
                        'id': feedback_data.get('imageId', ''),
                        'timestamp': feedback_data.get('timestamp', ''),
                        'feedback': feedback_data.get('feedback', ''),
                        'imageBase64': feedback_data.get('imageBase64', ''),  # Use base64 data instead of URL
                    })
        
        # Sort by timestamp (newest first)
        history_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET'
            },
            'body': json.dumps({
                'success': True,
                'userId': user_id,
                'historyItems': history_items
            })
        }
    
    except Exception as e:
        print(f"Error fetching user history: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }