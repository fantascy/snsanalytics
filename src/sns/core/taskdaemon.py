import threading
import logging

from google.appengine.api.background_thread import BackgroundThread

import deploysns
import context
from common.multithreading.taskdaemon import TaskDaemon


class BackendTaskDaemon(TaskDaemon):
    def __init__(self, name=None, workers=3, task_limit=10, deploy=deploysns):
        TaskDaemon.__init__(self, name=name, workers=workers, task_limit=task_limit)
        self.deploy = deploy
        
    @classmethod
    def get_thread_class(cls):
        return threading.Thread if context.is_dev_mode() else BackgroundThread
        

    
class DemoBackendTaskDaemon(BackendTaskDaemon):
    def __init__(self):
        BackendTaskDaemon.__init__(self, workers=5)
        
    def run_impl(self, task):
        logging.info("Thread %s processed task %s. %d tasks remaining."  % (self.current_thread_str(), str(task), len(self.tasks)))

    def pre_execute(self):
        self.add_tasks(range(100, 200))

    @classmethod
    def deferred_execute(cls):
        cls().execute()


if __name__ == '__main__':
    DemoBackendTaskDaemon().execute()

