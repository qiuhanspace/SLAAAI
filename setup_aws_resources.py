import boto3
import json
import time
from botocore.exceptions import ClientError

# Initialize clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock')
bedrock_agent = boto3.client('bedrock-agent')
iam = boto3.client('iam')

# Create S3 buckets
def create_buckets():
    # Bucket for storing food images
    images_bucket_name = 'healthy-meal-images-bucket'
    # Bucket for storing feedback data
    feedback_bucket_name = 'healthy-meal-feedback-bucket'
    # Bucket for knowledge base documents
    kb_bucket_name = 'healthy-meal-kb-bucket'
    
    buckets = [images_bucket_name, feedback_bucket_name, kb_bucket_name]
    
    for bucket_name in buckets:
        try:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': 'us-west-2'}
            )
            print(f"Created bucket: {bucket_name}")
            
            # Enable CORS for frontend access
            cors_configuration = {
                'CORSRules': [{
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': []
                }]
            }
            s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"Bucket already exists: {bucket_name}")
            else:
                print(f"Error creating bucket {bucket_name}: {e}")
    
    return {
        'images_bucket': images_bucket_name,
        'feedback_bucket': feedback_bucket_name,
        'kb_bucket': kb_bucket_name
    }

# Create IAM role for Bedrock agent
def create_agent_role():
    # Use your existing role ARN for agents
    role_arn = "arn:aws:iam::430672174368:role/service-role/PerceiverAgent-ospy3-role-98S15A8K7GW"
    print(f"Using existing agent role: {role_arn}")
    return role_arn

# Upload nutrition guidelines to knowledge base bucket
def upload_nutrition_guidelines(kb_bucket):
    # Create some basic nutrition guideline documents
    guidelines = [
        {
            "title": "Healthy Plate Model",
            "content": """
            A healthy meal should follow the plate model:
            - 1/2 of the plate: vegetables and fruits
            - 1/4 of the plate: whole grains or starchy vegetables
            - 1/4 of the plate: protein-rich foods
            - Include a small amount of healthy fats
            - Drink water, tea, or coffee without added sugar
            """
        },
        {
            "title": "Protein Guidelines",
            "content": """
            Healthy protein sources include:
            - Lean meats like chicken, turkey, and fish
            - Plant-based proteins like beans, lentils, tofu, and tempeh
            - Low-fat dairy products
            - Eggs
            Limit red and processed meats.
            """
        },
        {
            "title": "Carbohydrate Guidelines",
            "content": """
            Choose complex carbohydrates:
            - Whole grains (brown rice, quinoa, oats, barley)
            - Starchy vegetables (sweet potatoes, squash)
            - Beans and legumes
            Limit refined grains and added sugars.
            """
        },
        {
            "title": "Fat Guidelines",
            "content": """
            Include healthy fats:
            - Avocados
            - Nuts and seeds
            - Olive oil
            - Fatty fish
            Limit saturated and trans fats.
            """
        },
        {
            "title": "Portion Size Guidelines",
            "content": """
            Appropriate portion sizes:
            - Protein: palm-sized portion (3-4 oz)
            - Grains/Starches: 1/2 cup or fist-sized portion
            - Vegetables: 1-2 cups or more
            - Fruits: 1 medium fruit or 1/2 cup
            - Fats: thumb-sized portion (1-2 tbsp)
            """
        }
    ]
    
    for i, guideline in enumerate(guidelines):
        filename = f"guideline_{i+1}.txt"
        s3.put_object(
            Bucket=kb_bucket,
            Key=filename,
            Body=guideline["content"],
            Metadata={"title": guideline["title"]}
        )
        print(f"Uploaded {filename} to {kb_bucket}")

# Create a knowledge base for nutrition guidelines
def create_knowledge_base(kb_bucket, role_arn):
    # Since you already have a knowledge base, just return the existing ID
    kb_id = "EA6O5SVHWD"
    print(f"Using existing knowledge base: {kb_id}")
    
    # Upload your nutrition guidelines to the existing knowledge base
    # You may need to manually upload these to the correct location
    # or use the dataSourceConfiguration to point to your S3 bucket
    
    return kb_id

# Create an agent to analyze meal images (or use existing)
def create_agent(kb_id, role_arn):
    # We already know the agent exists from the error message
    agent_id = "KKJN9H7DZE"
    print(f"Using existing agent: {agent_id}")
    
    # For an existing agent, we need to get the latest version
    try:
        versions = bedrock_agent.list_agent_versions(agentId=agent_id)
        agent_version = None
        
        for version in versions.get('agentVersionSummaries', []):
            if version['status'] == 'PREPARED' or version['status'] == 'READY':
                agent_version = version['agentVersion']
                print(f"Using existing agent version: {agent_version}")
                break
        
        # If no prepared version exists, use DRAFT
        if not agent_version:
            agent_version = 'DRAFT'
            print(f"No prepared version found, using: {agent_version}")
            
            # Try to prepare the DRAFT version
            try:
                prepare_response = bedrock_agent.prepare_agent(
                    agentId=agent_id,
                    agentVersion=agent_version
                )
                print(f"Prepared agent version: {agent_version}")
            except Exception as e:
                print(f"Error preparing agent version: {e}")
        
        # Check if we need to associate the knowledge base
        try:
            kbs = bedrock_agent.list_agent_knowledge_bases(
                agentId=agent_id,
                agentVersion=agent_version
            )
            
            kb_found = False
            for kb in kbs.get('agentKnowledgeBaseSummaries', []):
                if kb['knowledgeBaseId'] == kb_id:
                    kb_found = True
                    print(f"Knowledge base {kb_id} already associated with agent")
                    break
            
            if not kb_found:
                # Associate the knowledge base
                bedrock_agent.associate_agent_knowledge_base(
                    agentId=agent_id,
                    agentVersion=agent_version,
                    knowledgeBaseId=kb_id,
                    description='Nutrition guidelines knowledge base'
                )
                print(f"Associated knowledge base {kb_id} with agent {agent_id} (version: {agent_version})")
        except Exception as e:
            print(f"Error checking knowledge base associations: {e}")
        
        # Check if alias exists
        try:
            aliases = bedrock_agent.list_agent_aliases(agentId=agent_id)
            alias_id = None
            
            for alias in aliases.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == 'Production':
                    alias_id = alias['agentAliasId']
                    print(f"Using existing agent alias: {alias_id}")
                    break
            
            # Create alias if it doesn't exist
            if not alias_id:
                alias_response = bedrock_agent.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName='Production',
                    description='Production version of the meal analysis agent',
                    routingConfiguration=[
                        {
                            'agentVersion': agent_version,
                            'provisionedThroughput': None  # Use on-demand throughput
                        }
                    ]
                )
                
                alias_id = alias_response['agentAlias']['agentAliasId']
                print(f"Created agent alias: {alias_id}")
            
            return agent_id, agent_version, alias_id
        except Exception as e:
            print(f"Error with agent aliases: {e}")
            
    except Exception as e:
        print(f"Error getting agent versions: {e}")
    
    # If we get here, something went wrong but we still want to return what we know
    return agent_id, "DRAFT", None

def main():
    print("Setting up AWS resources for Healthy Meal Analysis app...")
    
    # Create S3 buckets
    buckets = create_buckets()
    
    # Create IAM role
    role_arn = create_agent_role()
    
    # Upload nutrition guidelines
    upload_nutrition_guidelines(buckets['kb_bucket'])
    
    # Create knowledge base
    kb_id = create_knowledge_base(buckets['kb_bucket'], role_arn)
    
    # Create or use existing agent
    agent_id, agent_version, alias_id = create_agent(kb_id, role_arn)
    
    print("\nAWS resources setup complete!")
    print(f"Images Bucket: {buckets['images_bucket']}")
    print(f"Feedback Bucket: {buckets['feedback_bucket']}")
    print(f"Knowledge Base Bucket: {buckets['kb_bucket']}")
    print(f"Knowledge Base ID: {kb_id}")
    print(f"Agent ID: {agent_id}")
    print(f"Agent Version: {agent_version}")
    if alias_id:
        print(f"Agent Alias ID: {alias_id}")
    
    # Return configuration for other components
    return {
        'images_bucket': buckets['images_bucket'],
        'feedback_bucket': buckets['feedback_bucket'],
        'kb_bucket': buckets['kb_bucket'],
        'knowledge_base_id': kb_id,
        'agent_id': agent_id,
        'agent_version': agent_version,
        'agent_alias_id': alias_id
    }

if __name__ == "__main__":
    main() 