from common.s3.models import BaseS3File
from common.utils import datetimeparser 
import context


class FollowHistoryIF(BaseS3File):
    def __init__(self, time_bucket):
        self.time_bucket = int(time_bucket)
        BaseS3File.__init__(self, bucket=context.get_context().amazon_bucket(), path=self.s3_file_path(time_bucket))
        
    @classmethod
    def time_bucket_func(cls):
        pass

    @classmethod
    def get_by_time_bucket(cls, time_bucket):
        return cls(time_bucket=time_bucket)

    def s3_file_directory(self):
        pass
        
    def s3_file_path(self, time_bucket): 
        return "femaster/%s/%s.json" % (self.s3_file_directory(), time_bucket)
    
    def add_user_ids(self, more):
        if not more:
            return
        user_ids = self.get_json()
        if user_ids:
            user_ids.extend(more)
        else:
            user_ids = more
        self.set_json(user_ids)
 

class SrcFollowHistoryIF(FollowHistoryIF):
    def __init__(self, chid, time_bucket):
        self.chid = chid
        FollowHistoryIF.__init__(self, time_bucket=time_bucket)

    @classmethod
    def get_by_chid_and_time_bucket(cls, chid, time_bucket):
        return cls(chid=chid, time_bucket=time_bucket)

        
class SrcFollowAllocMonthly(SrcFollowHistoryIF):
    """ 
        parent - the Source object. 
        key_name - string value of the integer week time bucket.
    """
    @classmethod
    def time_bucket_func(cls):
        return datetimeparser.intMonth

    def s3_file_directory(self):
        return "src_alloc_monthly/%s" % self.chid
        
    @classmethod
    def get_by_chid_and_time(cls, chid, t):
        return cls.get_by_chid_and_time_bucket(chid, cls.time_bucket_func()(t))


class SysFollowAllocWeekly(FollowHistoryIF):
    """ 
        parent - none. 
        key_name - string value of the integer week time bucket.
    """
    @classmethod
    def time_bucket_func(cls):
        return datetimeparser.intWeek
    
    def s3_file_directory(self):
        return "sys_alloc_weekly"

