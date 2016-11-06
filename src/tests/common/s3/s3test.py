import unittest
import datetime
import StringIO

from boto.s3.connection import S3Connection

from common import consts as common_const
from common.s3.models import BaseS3File
import context


class TestBaseS3File(unittest.TestCase):
    def test_get_invalid_key(self):
        self.assertIsNone(BaseS3File(context.get_context().amazon_bucket(), 'invalid_key').get_json())
        
    def test_10(self):
        self._run_test(size=10)
    
    def _run_test(self, size=10):
        start_time = datetime.datetime.now()
        test_s3_file = BaseS3File(context.get_context().amazon_bucket(), 'test/test_data.json', fetch_data=False)
        data_in = [1234567890] * size
        test_s3_file.put_json(data_in)
        data_out = test_s3_file.get_json()
        self.assertEqual(str(data_in), str(data_out))
        test_s3_file.delete()
        end_time = datetime.datetime.now()
        print "Finished test_%d() in %s." % (size, end_time - start_time)


class TestBotoUpload (unittest.TestCase):
    def test_simple_upload(self):
        self.assertTrue(self.simple_upload(size=1000))

#     def test_multipart_upload(self):
#         self.assertTrue(self.multipart_upload())

    @classmethod
    def simple_upload(cls, size=1000):
        c = S3Connection(aws_access_key_id=common_const.AWS_ACCESS_KEY_ID, aws_secret_access_key=common_const.AWS_SECRET_ACCESS_KEY)
        b = c.get_bucket(context.get_context().amazon_bucket())
        key_name = 'test/simple-upload.txt'
        s_in = ''.join(['a'] * size)
        key = b.new_key(key_name)
        key.set_contents_from_string(s_in, reduced_redundancy=True)
        s_out = key.get_contents_as_string()
        b.delete_key(key_name)
        return s_in == s_out

    @classmethod
    def multipart_upload(cls):
        c = S3Connection(aws_access_key_id=common_const.AWS_ACCESS_KEY_ID, aws_secret_access_key=common_const.AWS_SECRET_ACCESS_KEY)
        b = c.lookup(context.get_context().amazon_bucket())
        key_name = 'test/multipart-upload.txt'
        mp = b.initiate_multipart_upload(key_name)
        f1 = ''.join(['a'] * common_const.AWS_S3_MULTIPART_MIN_SIZE)
        fp1 = StringIO.StringIO(f1)
        mp.upload_part_from_file(fp1, 1)
        fp1.close()
        f2 = ''.join(['b'] * 10)
        fp2 = StringIO.StringIO(f2)
        mp.upload_part_from_file(fp2, 2)
        fp2.close()
        mp.complete_upload()
        k = b.get_key(key_name)
        data = k.get_contents_as_string()
        k.change_storage_class('REDUCED_REDUNDANCY')
        b.delete_key(key_name)
        return len(data) == common_const.AWS_S3_MULTIPART_MIN_SIZE + 10


if __name__ == '__main__':
    unittest.main()
