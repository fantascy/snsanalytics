import json
import logging
import StringIO

from boto.s3.connection import S3Connection

from common import consts as common_const


class BaseS3File:
    def __init__(self,
                 bucket, 
                 path, 
                 aws_key=common_const.AWS_ACCESS_KEY_ID, 
                 aws_secret=common_const.AWS_SECRET_ACCESS_KEY,
                 content_type = 'application/javascript',
                 storage_class = 'REDUCED_REDUNDANCY',
                 fetch_data = True):
        self.path = path
        self.aws_key = aws_key
        self.aws_secret = aws_secret
        self.content_type = content_type
        self.storage_class = storage_class
        self.connection = S3Connection(aws_access_key_id=self.aws_key, aws_secret_access_key=self.aws_secret)
        self.bucket = self.get_bucket(bucket)
        self.cache_json = None
        if fetch_data:
            self.get_json()

    def get_bucket(self, bucket_name):
        return self._execute(self._get_bucket, bucket_name)
    
    def delete(self):
        return self._execute(self._delete)
    
    def get_json(self):
        return self._execute(self._get_json)
    
    def set_json(self, json_data):
        """ Set in the cache, not commit to S3. """
        return self._execute(self._set_json, json_data)
    
    def put_json(self, json_data):
        """ Set and commit to S3. """
        return self._execute(self._put_json, json_data)
    
    def commit(self):
        """ Commit the cache to S3. """
        if self.cache_json is not None:
            self.put_json(self.cache_json)
        
    def _execute(self, func, *args, **kwargs):
        retry = 3
        while retry:
            try:
                return func(*args, **kwargs)
            except:
                retry -= 1
                if retry == 0:
                    raise
            
    def _get_bucket(self, bucket_name):
        return self.connection.get_bucket(bucket_name)
        
    def _get(self):
        key = self.bucket.get_key(self.path)
        if not key:
            return None
        return key.get_contents_as_string(response_headers={'content-type': self.content_type})

    def _delete(self):
        return self.bucket.delete_key(self.path)

    def _put(self, data):
        key = self.bucket.get_key(self.path)
        if not key:
            key = self.bucket.new_key(self.path)
        headers = {} #{'content-type': self.content_type}
        if data is None: data = ''
        if data is None or len(data) <= common_const.AWS_S3_MULTIPART_MIN_SIZE:
            return key.set_contents_from_string(data, headers=headers, reduced_redundancy=True)
        logging.info("Use multipart upload on data size of %d." % len(data))
        mp = self.bucket.initiate_multipart_upload(self.path, headers=headers)
        index = 0
        part_no = 0
        while index < len(data):
            part_no += 1
            fp = StringIO.StringIO(data[index: index+common_const.AWS_S3_MULTIPART_MIN_SIZE])
            mp.upload_part_from_file(fp, part_no)
            fp.close()
            index += common_const.AWS_S3_MULTIPART_MIN_SIZE
        resp = mp.complete_upload()
        key.change_storage_class('REDUCED_REDUNDANCY')
        return resp
        
    def _get_json(self):
        if self.cache_json is not None:
            return self.cache_json
        resp = self._get()
        if isinstance(resp, basestring): resp = eval(resp)
        if isinstance(resp, basestring): resp = eval(resp)
        self.cache_json = resp if resp else None
        return self.cache_json  

    def _set_json(self, json_data):
        self.cache_json = json_data 

    def _put_json(self, json_data):
        self.cache_json = json_data 
        jsons = json.dumps(self.cache_json)
        logging.debug("Uploading %d bytes to S3." % len(jsons))
        return self._put(jsons)


