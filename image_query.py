import boto3
import os
import json
from boto3.dynamodb.conditions import Attr, Or

images_bucket = os.environ['IMAGES_BUCKET']
thumbnail_bucket = os.environ['THUMBNAIL_BUCKET']

def get_images_urls_from_labels(labels):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['LABELS_TABLE'])
    if labels:
        conditions = [Attr('labels').contains(label) for label in labels]
        if len(conditions) == 1: 
            filter_expr = conditions[0]
        else:
            filter_expr = Or(*conditions)
        response = table.scan(FilterExpression=filter_expr)
    
    else:
        response = table.scan()
    
    s3 = boto3.client('s3')
    for item in response['Items']:
        image_id = item['image_id']
        item['thumbnail_url'] = s3.generate_presigned_url(
            'get_object',
            Params = {'Bucket': thumbnail_bucket, 'Key': image_id},
            ExpiresIn=3600
        )
        item['original_url'] = s3.generate_presigned_url(
            'get_object',
            Params = {'Bucket': images_bucket, 'Key': image_id},
            ExpiresIn=3600
        )
    
    return response['Items']

def lambda_handler(event, context):
    labels = []
    if event.get('queryStringParameters') and event['queryStringParameters'].get('labels'):
        labels = event['queryStringParameters']['labels']
        labels = labels.split(',')
    ret = get_images_urls_from_labels(labels)
    return {
        'statusCode': 200,
        'body': json.dumps(ret)
    }