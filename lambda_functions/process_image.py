import json
import boto3
from botocore.config import Config
import base64
import uuid
from datetime import datetime
import os

s3 = boto3.client('s3', region_name='us-west-2', config=Config(
    connect_timeout=5,
    read_timeout=5,
    retries={'max_attempts': 2}
))

# Get environment variables
IMAGES_BUCKET = os.environ['IMAGES_BUCKET']
FEEDBACK_BUCKET = os.environ['FEEDBACK_BUCKET']
AGENT_ID = os.environ['AGENT_ID']
AGENT_ALIAS_ID = os.environ['AGENT_ALIAS_ID']

# Create the correct Bedrock clients
try:
    # Management client
    bedrock = boto3.client('bedrock', region_name='us-west-2', config=Config(
        connect_timeout=5,
        read_timeout=50  # Longer timeout for model operations
    ))
    # Runtime client for model invocation
    bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2', config=Config(
        connect_timeout=5,
        read_timeout=50  # Longer timeout for model operations
    ))
    print("Successfully created bedrock clients")
except Exception as e:
    print(f"Error creating bedrock clients: {e}")

def lambda_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event['body'])
        image_data = body.get('image')
        user_id = body.get('userId', 'anonymous')
        
        # Add more detailed error logging
        print(f"Processing request for user: {user_id}")
        print(f"Image data length: {len(image_data) if image_data else 'None'}")
        
        # Add more detailed validation of the image data format
        if not image_data or not isinstance(image_data, str):
            raise ValueError(f"Invalid image data type: {type(image_data)}")
        
        if not image_data.startswith('data:image/'):
            raise ValueError("Image data doesn't have the expected MIME prefix")
        
        if ',' not in image_data:
            raise ValueError("Image data doesn't contain the expected base64 separator")

        print(f"Image data prefix: {image_data[:30]}...") # Log the beginning of the data
        
        # More careful image decoding
        if image_data and ',' in image_data:
            image_content = base64.b64decode(image_data.split(',')[1])
            print(f"Successfully decoded image, size: {len(image_content)} bytes")
        else:
            raise ValueError("Invalid image data format")
        
        # Generate IDs and timestamp
        image_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # For direct S3 access (keeping this commented out as reference)
        # image_key = f"{user_id}/{image_id}.jpg"
        # s3.put_object(
        #     Bucket=IMAGES_BUCKET,
        #     Key=image_key,
        #     Body=image_content,
        #     ContentType='image/jpeg'
        # )
        
        # Try to use the invoke_model directly on the bedrock_runtime client
        try:
            # List available models to help with debugging
            try:
                model_list = bedrock.list_foundation_models()
                print(f"Available models: {[m['modelId'] for m in model_list.get('modelSummaries', [])]}")
            except Exception as e:
                print(f"Could not list models: {e}")
            
            # Use Claude 3.7 model that you have access to
            model_id = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
            
            print(f"Sending base64 image to model, length: {len(image_data)}")
            
            # Create an improved prompt for nutritional analysis
            analysis_prompt = """
            Analyze this meal image and provide a comprehensive nutritional assessment:

            1. IDENTIFICATION:
               - Identify all visible foods and ingredients in this meal

            2. NUTRITIONAL EVALUATION:
               - Estimate the nutrition score of this meal on a scale of 1-10
               - How balanced is this meal? Score 1-10
               - How healthy is this meal overall? Score 1-10
               - How sustainable is this meal environmentally? Score 1-10
               
            3. IMPROVEMENTS:
               - Identify any unhealthy or unsustainable ingredients
               - Suggest specific healthier and more sustainable alternatives
               - Justify each recommendation with brief nutritional facts
               
            Format your response in clear sections with headings and bullet points where appropriate.
            """
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/jpeg",
                                        "data": image_data.split(',')[1]
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": analysis_prompt
                                }
                            ]
                        }
                    ]
                })
            )
            
            # Process the response
            response_body = json.loads(response['body'].read())
            print(f"Model response keys: {response_body.keys()}")
            
            # Claude 3 response format is different
            if 'content' in response_body:
                agent_response = response_body['content'][0]['text']
            else:
                agent_response = response_body.get('completion', '')
            
            # Save feedback to S3 (now including base64 image directly)
            feedback_data = {
                'userId': user_id,
                'imageId': image_id,
                # 'imageUrl': f"s3://{IMAGES_BUCKET}/{image_key}",  # Not needed anymore
                'imageBase64': image_data,  # Store the original base64 data
                'timestamp': timestamp,
                'feedback': agent_response
            }
            
            feedback_key = f"{user_id}/{image_id}_feedback.json"
            s3.put_object(
                Bucket=FEEDBACK_BUCKET,
                Key=feedback_key,
                Body=json.dumps(feedback_data),
                ContentType='application/json'
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({
                    'success': True,
                    'imageId': image_id,
                    'feedback': agent_response
                })
            }
            
        except Exception as e:
            print(f"ERROR DETAILS: {str(e)}")
            import traceback
            traceback_str = traceback.format_exc()
            print(f"FULL TRACEBACK: {traceback_str}")
            
            # Return more detailed error info (for development only)
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                },
                'body': json.dumps({
                    'success': False,
                    'error': str(e),
                    'traceback': traceback_str
                })
            }
            
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        } 