import os
import json
import base64
import boto3
from PIL import Image
from io import BytesIO

images_bucket = os.environ.get('IMAGES_BUCKET')
thumbnail_bucket = os.environ.get('THUMBNAIL_BUCKET')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body','{}'))
        base64_image = body.get('image')
        
        if base64_image.startswith('data:image'):
            base64_image = base64_image.split(',')[1]
            
        image_bytes = base64.b64decode(base64_image)
        
        if image_bytes.startswith(b'\xff\xd8\xff'):
            file_ext = 'jpg'
            content_type = 'image/jpeg'
        elif image_bytes.startswith(b'\x89PNG'):
            file_ext = 'png'
            content_type = 'image/png'
        elif image_bytes.startswith(b'GIF'):
            file_ext = 'gif'
            content_type = 'image/gif'
        else: 
            file_ext = 'jpg' 
            content_type = 'image/jpeg'
            
        image_name = body.get('image_name')
        filename = f"{image_name}.{file_ext}"
        
        s3 = boto3.client('s3')
        
        s3.put_object(
            Bucket = images_bucket,
            Key = filename,
            Body = image_bytes,
            ContentType = content_type
        )

        # Create and store thumbnail
        image = Image.open(BytesIO(image_bytes))
        thumbnail_size = int(os.environ.get('THUMBNAIL_SIZE', '128'))
        image.thumbnail((thumbnail_size, thumbnail_size))
        
        thumbnail_io = BytesIO() 
        image.save(thumbnail_io, format=image.format or 'JPEG')
        thumbnail_io.seek(0)
        
        s3.put_object(
            Bucket = thumbnail_bucket,
            Key = filename,
            Body = thumbnail_io, 
            ContentType = content_type
        )
        
        return {
            'statusCode' : 200
        }
    except Exception as e: 
        return {
            'statusCode': 500, 
            'body': json.dumps({'error':f'Processing Failed: {str(e)}'})
        }