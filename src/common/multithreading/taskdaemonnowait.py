import threading
import logging
import random
import datetime


class TaskDaemonNoWait(object):
    def __init__(self, name=None, workers=3):
        self.name = name if name else "%s-%d" % (self.__class__.__name__, random.randint(1000, 9999)) 
        self.tasks = []
        self.mission_accomplished = False
        self.cv = threading.Condition()
        self.workers = []
        for i in range(workers):
            worker_name = "%s-worker-%d" % (self.name, i)
            worker = threading.Thread(name=worker_name, target=self.run)
            self.workers.append(worker) 
        
    def start(self):
        for worker in self.workers:
            worker.start() 
            
    def join(self):
        for worker in self.workers:
            worker.join() 
            
    def run(self):
        """ The run() function of worker threads. """
        while self.tasks:
            task = None
            with self.cv:
                if self.tasks: 
                    task = self.tasks.pop(-1) 
            try:
                if task is not None: 
                    self.run_impl(task)
            except:
                logging.exception("Unexpected exception when executing task inside thread %s!" % self.current_thread_str())
        logging.info("Thread %s died peacefully."  % self.current_thread_str())

    def run_impl(self, task):
        """ Subclass implementation of worker threads. """
        pass

    def execute(self):
        """ Typical steps of execution for the master thread. """
        self.pre_execute()
        self.start()
        self.join()
        self.post_execute()

    def pre_execute(self):
        """ Subclass implementation of the master thread. """
        pass

    def post_execute(self):
        logging.info("Finished executing all tasks at %s." % datetime.datetime.now())

    def add_tasks(self, tasks):
        if not tasks:
            return
        self.tasks.extend(tasks)

    def current_thread_str(self):
        current_thread = threading.current_thread()
        return "%s(%d)"  % (current_thread.name, current_thread.ident)

    
class DemoTaskDaemonNoWait(TaskDaemonNoWait):
    def __init__(self):
        TaskDaemonNoWait.__init__(self, workers=5)
        
    def run_impl(self, task):
        logging.info("Thread %s processed task %s. %d tasks remaining."  % (self.current_thread_str(), str(task), len(self.tasks)))

    def pre_execute(self):
        self.add_tasks(range(100, 200))


if __name__ == '__main__':
    DemoTaskDaemonNoWait().execute()

