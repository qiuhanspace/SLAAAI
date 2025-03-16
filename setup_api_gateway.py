import boto3
import json
import os

# Initialize clients
api_gateway = boto3.client('apigatewayv2')
lambda_client = boto3.client('lambda')
iam = boto3.client('iam')

def create_api_gateway(process_image_lambda_arn, get_history_lambda_arn):
    # Create HTTP API
    api_name = 'MealAnalyzerAPI'
    
    print(f"Creating API Gateway: {api_name}")
    
    response = api_gateway.create_api(
        Name=api_name,
        ProtocolType='HTTP',
        CorsConfiguration={
            'AllowOrigins': ['*'],
            'AllowMethods': ['POST', 'GET', 'OPTIONS'],
            'AllowHeaders': ['Content-Type', 'Authorization'],
            'MaxAge': 300
        }
    )
    
    api_id = response['ApiId']
    print(f"Created API with ID: {api_id}")
    
    # Create routes
    # 1. Route for processing images
    api_gateway.create_route(
        ApiId=api_id,
        RouteKey='POST /analyze-meal',
        Target=f'integrations/{create_lambda_integration(api_id, process_image_lambda_arn)}'
    )
    print("Created route: POST /analyze-meal")
    
    # 2. Route for getting meal history
    api_gateway.create_route(
        ApiId=api_id,
        RouteKey='GET /meal-history/{userId}',
        Target=f'integrations/{create_lambda_integration(api_id, get_history_lambda_arn)}'
    )
    print("Created route: GET /meal-history/{userId}")
    
    # After creating your routes, add this CORS configuration
    api_gateway.update_route(
        ApiId=api_id,
        RouteKey='GET /meal-history/{userId}',
        RouteResponseSelectionExpression='$default',
        AuthorizationType='NONE',
        Target=f'integrations/{create_lambda_integration(api_id, get_history_lambda_arn)}',
        ResponseParameters={
            'method.response.header.Access-Control-Allow-Origin': "'*'",
            'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key'",
            'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'"
        }
    )
    
    # Add an OPTIONS method for CORS preflight requests
    api_gateway.create_route(
        ApiId=api_id,
        RouteKey='OPTIONS /meal-history/{userId}',
        Target=f'integrations/{create_options_integration(api_id)}'
    )
    
    # Create stage and deploy
    api_gateway.create_stage(
        ApiId=api_id,
        StageName='$default',
        AutoDeploy=True
    )
    
    # Get the API endpoint URL
    api_endpoint = f"https://{api_id}.execute-api.{boto3.session.Session().region_name}.amazonaws.com"
    print(f"API Gateway endpoint: {api_endpoint}")
    
    return api_endpoint

def create_lambda_integration(api_id, lambda_arn):
    # Create integration
    response = api_gateway.create_integration(
        ApiId=api_id,
        IntegrationType='AWS_PROXY',
        IntegrationMethod='POST',
        PayloadFormatVersion='2.0',
        IntegrationUri=lambda_arn
    )
    
    # Add permission for API Gateway to invoke Lambda
    try:
        source_arn = f"arn:aws:execute-api:{boto3.session.Session().region_name}:{boto3.session.Session().client('sts').get_caller_identity()['Account']}:{api_id}/*/*"
        lambda_client.add_permission(
            FunctionName=lambda_arn,
            StatementId=f"apigateway-invoke-{api_id}-{lambda_arn.split(':')[-1]}",
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
    except lambda_client.exceptions.ResourceConflictException:
        # Permission already exists
        pass
    
    return response['IntegrationId']

def create_options_integration(api_id):
    # Implementation of create_options_integration function
    # This function needs to be implemented based on your specific requirements
    # For now, we'll return a placeholder
    return "placeholder_integration_id"

def main():
    # Get Lambda ARNs (would be outputs from Lambda creation)
    # In a real setup, these would be retrieved from CloudFormation outputs or similar
    process_image_lambda_arn = input("Enter the ARN of the process_image Lambda function: ")
    get_history_lambda_arn = input("Enter the ARN of the get_user_history Lambda function: ")
    
    api_endpoint = create_api_gateway(process_image_lambda_arn, get_history_lambda_arn)
    
    # Output the endpoint to use in the React app
    print("\nAdd this URL to your React application's .env file:")
    print(f"REACT_APP_API_URL={api_endpoint}")

if __name__ == "__main__":
    main() 