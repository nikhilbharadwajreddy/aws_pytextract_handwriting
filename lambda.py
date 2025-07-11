import json
import boto3
import os
from botocore.exceptions import ClientError
from urllib.parse import unquote_plus

# Hardcoded configurations
MODEL_ID = "us.deepseek.r1-v1:0"  # Cross-region inference profile for DeepSeek R1

def get_response_headers(event):
    """Return appropriate headers based on event type"""
    if 'Records' in event:
        # S3 event - no CORS needed
        return {'Content-Type': 'application/json'}
    else:
        # API call - include CORS
        return {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        }

def lambda_handler(event, context):
    try:
        # Check if it's an S3 event or manual API call
        if 'Records' in event and event['Records']:
            # S3 event trigger
            s3_record = event['Records'][0]['s3']
            s3_bucket = s3_record['bucket']['name']
            s3_key = unquote_plus(s3_record['object']['key'])  # URL decode
            
            print(f"S3 Event triggered for: s3://{s3_bucket}/{s3_key}")
        else:
            # Manual API call - extract from body
            body = json.loads(event.get('body', '{}') if isinstance(event.get('body'), str) else event.get('body', '{}'))
            s3_bucket = body.get('bucket', '')
            s3_key = body.get('key', '')
            
            if not s3_bucket or not s3_key:
                return {
                    'statusCode': 400,
                    'headers': get_response_headers(event),
                    'body': json.dumps({'error': 'Missing bucket or key parameter'})
                }
        
        # Initialize AWS clients
        textract_client = boto3.client('textract')
        bedrock_runtime = boto3.client('bedrock-runtime')
        s3_client = boto3.client('s3')
        
        # First, check if file exists and get metadata
        try:
            file_info = s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
            file_size = file_info['ContentLength']
            content_type = file_info.get('ContentType', '')
            
            print(f"File size: {file_size} bytes, Content-Type: {content_type}")
            
            # Check file size limit (10MB for detect_document_text)
            if file_size > 10 * 1024 * 1024:  # 10MB
                return {
                    'statusCode': 400,
                    'headers': get_response_headers(event),
                    'body': json.dumps({
                        'error': 'File too large',
                        'message': f'File size {file_size} bytes exceeds 10MB limit for Textract'
                    })
                }
                
        except ClientError as e:
            return {
                'statusCode': 404,
                'headers': get_response_headers(event),
                'body': json.dumps({
                    'error': 'File not found',
                    'message': f'Could not access s3://{s3_bucket}/{s3_key}'
                })
            }
        
        # Perform OCR using AWS Textract
        print(f"Processing file: s3://{s3_bucket}/{s3_key}")
        
        try:
            # Use detect_document_text for simple text detection (no tables/forms)
            textract_response = textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                }
            )
        except ClientError as textract_error:
            error_code = textract_error.response['Error']['Code']
            error_message = textract_error.response['Error']['Message']
            
            print(f"Textract Error: {error_code} - {error_message}")
            
            # Try alternative approach for PDFs
            if error_code == 'UnsupportedDocumentException' and s3_key.lower().endswith('.pdf'):
                return {
                    'statusCode': 400,
                    'headers': get_response_headers(event),
                    'body': json.dumps({
                        'error': 'PDF format not supported',
                        'message': 'Try converting PDF to JPG/PNG format, or ensure PDF is not password protected',
                        'suggestions': [
                            'Convert PDF to image format (JPG, PNG)',
                            'Ensure PDF is not password protected',
                            'Check if PDF file is corrupted',
                            'Verify PDF is under 10MB'
                        ]
                    })
                }
            else:
                # Re-raise the original error
                raise textract_error
        
        # Extract text from Textract response
        extracted_text = ""
        
        for block in textract_response['Blocks']:
            if block['BlockType'] == 'LINE':
                text = block.get('Text', '')
                extracted_text += text + "\n"
        
        # If no text extracted, return early
        if not extracted_text.strip():
            return {
                'statusCode': 200,
                'headers': get_response_headers(event),
                'body': json.dumps({
                    'original_text': '',
                    'enhanced_text': '',
                    'changes_made': [],
                    'summary': 'No text detected in document'
                })
            }
        
        # Prepare LLM prompt for text enhancement
        system_prompt = """You are a text enhancement specialist for OCR-extracted content.

Your task is to:
- Fix spelling mistakes and OCR errors in the provided text
- Correct common OCR misreads (like 'rn' instead of 'm', '0' instead of 'O', etc.)
- Improve text formatting and readability
- Maintain the original meaning and structure
- Be conservative - only fix obvious errors
- Preserve names, addresses, and numbers as accurately as possible

Focus on:
- Spelling corrections for common words
- OCR character recognition errors
- Proper capitalization
- Basic punctuation fixes
- Removing extra spaces or line breaks where appropriate"""

        user_prompt = f"""Please enhance and correct the following OCR-extracted text. Fix spelling mistakes and OCR errors while preserving the original meaning and structure:

ORIGINAL OCR TEXT:
{extracted_text}

Please return your response as a JSON object with the following structure:
{{
    "enhanced_text": "corrected and enhanced version of the text",
    "changes_made": [
        {{
            "original": "original text/word",
            "corrected": "corrected text/word",
            "type": "spelling|ocr_error|formatting|punctuation"
        }}
    ],
    "summary": "Brief summary of improvements made"
}}

Only return the JSON object, no additional text."""

        # Combine prompts
        combined_prompt = f"""{system_prompt}

{user_prompt}"""

        # Call LLM for text enhancement
        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "messages": [
                    {
                        "role": "user", 
                        "content": combined_prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1,  # Low temperature for accuracy
                "top_p": 0.9
            })
        )
        
        # Parse the LLM response
        response_body = json.loads(response['body'].read())
        
        # Extract the text enhancement analysis
        if 'choices' in response_body:
            enhancement_analysis = response_body['choices'][0]['message']['content']
        elif 'content' in response_body:
            enhancement_analysis = response_body['content'][0]['text']
        elif 'output' in response_body:
            enhancement_analysis = response_body['output']['message']['content'][0]['text']
        else:
            enhancement_analysis = str(response_body)
        
        # Try to parse enhancement analysis as JSON
        try:
            enhancement_json = json.loads(enhancement_analysis)
            enhanced_text = enhancement_json.get('enhanced_text', extracted_text.strip())
            changes_made = enhancement_json.get('changes_made', [])
            summary = enhancement_json.get('summary', 'No changes made')
        except json.JSONDecodeError:
            # If LLM didn't return valid JSON, return original text
            enhanced_text = extracted_text.strip()
            changes_made = []
            summary = 'Error parsing enhancement response'
        
        # Format the final response - minimal structure
        final_response = {
            'original_text': extracted_text.strip(),
            'enhanced_text': enhanced_text,
            'changes_made': changes_made,
            'summary': summary
        }
        
        return {
            'statusCode': 200,
            'headers': get_response_headers(event),
            'body': json.dumps(final_response)
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"AWS Client Error: {error_code} - {error_message}")
        
        return {
            'statusCode': 500,
            'headers': get_response_headers(event),
            'body': json.dumps({
                'error': f"AWS Service Error: {error_code}",
                'message': error_message
            })
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': get_response_headers(event),
            'body': json.dumps({
                'error': 'Invalid JSON in request body',
                'message': str(e)
            })
        }
        
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_response_headers(event),
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }