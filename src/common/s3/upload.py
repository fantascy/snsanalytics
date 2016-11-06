import urllib

from google.appengine.api.images import resize

import context
from common.s3 import S3
from common import consts as common_const


def uploadImg(imageUrl,key,width=80):
    conn = S3.AWSAuthConnection(common_const.AWS_ACCESS_KEY_ID, common_const.AWS_SECRET_ACCESS_KEY)
    data = urllib.urlopen(imageUrl).read()
    imgData = resize(data,width=width)
    imgKey =  key +'.png'
    headers = {}
    headers['Content-Type'] = 'image/png'
    headers['x-amz-storage-class'] = 'REDUCED_REDUNDANCY'
    bucket = context.get_context().amazon_bucket()
    response = conn.put(bucket, imgKey, imgData, headers)
    return response.http_response.status