import os
import boto3
from PIL import Image
from io import BytesIO
import base64
from multipart import MultipartParser

def resize_image(img, target_size=(400, 400)):
    """Resize image maintaining aspect ratio"""
    ratio = min(target_size[0]/img.size[0], target_size[1]/img.size[1])
    new_size = tuple([int(x*ratio) for x in img.size])
    return img.resize(new_size, Image.Resampling.LANCZOS)

def parse_multipart(body, boundary):
    parts = {}
    segments = body.split(b'--' + boundary)
    
    for segment in segments:
        if len(segment) > 0 and not segment.startswith(b'--'):
            # Handle different line ending scenarios
            if b'\r\n\r\n' in segment:
                headers, content = segment.split(b'\r\n\r\n', 1)
            else:
                headers, content = segment.split(b'\n\n', 1)
                
            headers = headers.decode()
            
            if 'filename=' in headers:
                name = headers.split('name="')[1].split('"')[0]
                # Remove trailing boundary markers and whitespace
                content = content.strip(b'\r\n').strip(b'-')
                parts[name] = {
                    'body': content,
                    'filename': headers.split('filename="')[1].split('"')[0]
                }
    
    return parts

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = os.environ['BUCKET_NAME']
    max_file_size = 2 * 1024 * 1024  # 2 MB
    
    try:
        # Get content type and boundary from headers
        content_type = event['headers'].get('content-type', event['headers'].get('Content-Type'))
        if not content_type or 'boundary=' not in content_type:
            return {
                "statusCode": 400,
                "body": "Invalid content type or missing boundary"
            }
            
        boundary = content_type.split('boundary=')[1].encode()
        
        # Get the body - handle both base64 encoded and raw binary
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body)
        elif isinstance(body, str):
            body = body.encode()
            
        # Parse multipart form data
        parts = parse_multipart(body, boundary)
        
        if 'image1' not in parts or 'image2' not in parts:
            return {
                "statusCode": 400,
                "body": "Both images are required"
            }
        
        # Process images
        img1 = Image.open(BytesIO(parts['image1']['body']))
        img2 = Image.open(BytesIO(parts['image2']['body']))
        
        # Convert images to RGB if they're not
        if img1.mode != 'RGB':
            img1 = img1.convert('RGB')
        if img2.mode != 'RGB':
            img2 = img2.convert('RGB')
        
        # Resize images
        img1_resized = resize_image(img1)
        img2_resized = resize_image(img2)
        
        # Create combined image
        total_width = img1_resized.size[0] + img2_resized.size[0] + 20
        max_height = max(img1_resized.size[1], img2_resized.size[1])
        combined_img = Image.new('RGB', (total_width, max_height), 'white')
        
        # Paste images
        combined_img.paste(img1_resized, (0, 0))
        combined_img.paste(img2_resized, (img1_resized.size[0] + 20, 0))
        
        # Save to buffer
        output_buffer = BytesIO()
        combined_img.save(output_buffer, format='JPEG', quality=85)
        output_buffer.seek(0)
        
        # Save to S3
        output_key = f"combined_image_{context.aws_request_id}.jpg"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=output_buffer,
            ContentType='image/jpeg'
        )
        
        #  Return the response with CORS headers Proxy integration
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "image/jpeg",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Content-Disposition": "attachment; filename=combined_image.jpg"
            },
            "body": base64.b64encode(output_buffer.getvalue()).decode('utf-8'),
            "isBase64Encoded": True
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        # Include CORS headers in error responses
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": str(e)
        }
        