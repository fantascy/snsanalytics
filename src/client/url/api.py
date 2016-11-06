# import datetime, time
# import threading
# import logging
# 
# from common.multithreading.taskdaemonnowait import TaskDaemonNoWait
# from sns.api import consts as api_const
# from client import apiclient
# from client.base.api import ApiBase
# 
# 
# THREAD_POOL = 5     
# TASK_LIMIT = 100     
# TIME_BUCKET = 60
# 
# def thread_name():
#     return "Thread %d" % threading.current_thread().ident 
# 
# 
# class GlobalUrl(ApiBase):
#     API_MODULE = api_const.API_M_GLOBAL_URL
# 
# 
# class TroveUrlResolveTaskDaemon(TaskDaemonNoWait):
#     def __init__(self):
#         TaskDaemonNoWait.__init__(self, workers=THREAD_POOL)
#         
#     def run_impl(self, task):
#         return False
# 
#     def pre_execute(self):
#         self.add_tasks(sources)
# 
# 
# if __name__ == '__main__':
#     while True:
#         apiclient.login_as_admin()
#         TroveUrlResolveTaskDaemon().execute()
#         time.sleep(TIME_BUCKET)

