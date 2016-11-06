import threading
import logging
import random


class TaskDaemon:
    def __init__(self, name=None, workers=3, task_limit=10):
        self.name = name if name else "%s-%d" % (self.__class__.__name__, random.randint(1000, 9999)) 
        self.tasks = []
        self.mission_accomplished = False
        self.cv = threading.Condition()
        self.task_limit = task_limit
        self.workers = []
        for i in range(workers):
            worker_name = "%s-worker-%d" % (self.name, i)
            worker = self.get_thread_class()(name=worker_name, target=self.run)
            self.workers.append(worker) 
        
    @classmethod
    def get_thread_class(cls):
        return threading.Thread
        
    def should_master_wait(self):
        return len(self.tasks) >= self.task_limit and not self.mission_accomplished 
    
    def should_worker_wait(self):
        return len(self.tasks) == 0 and not self.mission_accomplished 
    
    def set_mission_accomplished(self):
        with self.cv:
            while self.tasks:
                self.cv.wait()
            self.mission_accomplished = True
            self.cv.notify_all()
    
    def start(self):
        for worker in self.workers:
            worker.start() 
            
    def join(self):
        for worker in self.workers:
            worker.join() 
            
    def run(self):
        """ The run() function of worker threads. """
        while not self.mission_accomplished:
            task = None
            with self.cv:
                while self.should_worker_wait():
                    self.cv.wait()
                if self.tasks:
                    task = self.tasks.pop(-1) 
                self.cv.notify_all()
            if task:
                try:
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
        self.set_mission_accomplished()
        self.join()
        self.post_execute()

    def pre_execute(self):
        """ Subclass implementation of the master thread. """
        pass

    def post_execute(self):
        logging.info("Finished executing all tasks.")

    def add_tasks(self, tasks):
        if not tasks:
            return
        with self.cv:
            while self.should_master_wait():
                self.cv.wait()
            self.tasks.extend(tasks)
            self.cv.notify_all()

    def current_thread_str(self):
        current_thread = threading.current_thread()
        return "%s(%d)"  % (current_thread.name, current_thread.ident)

    
class DemoTaskDaemon(TaskDaemon):
    def __init__(self):
        TaskDaemon.__init__(self, workers=5)
        
    def run_impl(self, task):
        logging.info("Thread %s processed task %s. %d tasks remaining."  % (self.current_thread_str(), str(task), len(self.tasks)))

    def pre_execute(self):
        self.add_tasks(range(100, 200))

    @classmethod
    def deferred_execute(cls):
        cls().execute()


if __name__ == '__main__':
    DemoTaskDaemon().execute()

