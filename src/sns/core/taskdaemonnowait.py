import logging

import deploysns
import context

from common.multithreading.taskdaemonnowait import TaskDaemonNoWait


class BackendTaskDaemonNoWait(TaskDaemonNoWait):
    def __init__(self, name=None, workers=3, deploy=deploysns):
        TaskDaemonNoWait.__init__(self, name=name, workers=workers)
        self.deploy = deploy
        
    def run(self):
        """ The run() function of worker threads. """
        context.set_deferred_context(self.deploy)
        TaskDaemonNoWait.run(self)

    
class DemoBackendTaskDaemonNoWait(BackendTaskDaemonNoWait):
    def __init__(self):
        BackendTaskDaemonNoWait.__init__(self, workers=5)
        
    def run_impl(self, task):
        logging.info("Thread %s processed task %s. %d tasks remaining."  % (self.current_thread_str(), str(task), len(self.tasks)))

    def pre_execute(self):
        self.add_tasks(range(100, 200))

    @classmethod
    def deferred_execute(cls):
        cls().execute()


if __name__ == '__main__':
    DemoBackendTaskDaemonNoWait().execute()

