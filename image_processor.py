import os
import json
import base64
import boto3
from PIL import Image
from io import BytesIO

images_bucket = os.environ.get('IMAGES_BUCKET')
thumbnail_bucket = os.environ.get('THUMBNAIL_BUCKET')

def detect_and_save_image_labels(filename, image_bytes):
    rekognition = boto3.client('rekognition')
    response = rekognition.detect_labels(
        Image = {'Bytes': image_bytes},
        MaxLabels = 10, 
        MinConfidence = 75
    )
    table_name = os.environ.get('LABELS_TABLE')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    labels = [label['Name'] for label in response['Labels']]
    table.put_item(
        Item = {
            'image_id': filename,
            'labels': labels
        }
    ) 

def send_email_notification(filename):
    sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
    sns = boto3.client('sns')
    sns.publish(
        TopicArn=sns_topic_arn,
        Subject='New Image Uploaded',
        Message=f'Image {filename} has been uploaded to the gallery.'
    )

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
        
        detect_and_save_image_labels(filename, image_bytes)
        send_email_notification(filename)
        
        return {
            'statusCode' : 200
        }
    except Exception as e: 
        return {
            'statusCode': 500, 
            'body': json.dumps({'error':f'Processing Failed: {str(e)}'})
        }