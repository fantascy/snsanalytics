import time
import threading
import logging


class TestThreadIF:
    def run(self):
        retry = 10
        while retry > 0:
            current_thread = threading.current_thread()
            print "Current thread id(%d) %s."  % (current_thread.ident, current_thread.name)
            time.sleep(1)
            retry -= 1

    @classmethod
    def test(cls):
        count = 0
        threads = [cls(name=str(i)) for i in range(25)]
        try:
            for thread in threads:
                thread.start()
                count += 1
                print "Thread id(%d) %s started."  % (thread.ident, thread.name)
            for thread in threads:
                thread.join()
                print "Thread id(%d) %s died."  % (thread.ident, thread.name)
        except:
            logging.exception("Exception after creating %d threads!" % count)

    @classmethod
    def test_limit(cls):
        threads = []
        while True:
            try:
                thread = cls(name=len(threads))
                thread.start()
                threads.append(thread)
            except:
                logging.exception("Couldn't create more threads!")
                break
        print "Created %d threads." % len(threads)
                

class TestThread(TestThreadIF, threading.Thread):
    def __init__(self, name):
        threading.Thread.__init__(self, name=name)
        self.name = name


def test_thread_pool():
    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(processes=10)
    def func(arg1, arg2):
        current_thread = threading.current_thread()
        print "Current thread id(%d) %s. %s %s"  % (current_thread.ident, current_thread.name, arg1, arg2)
    for i in range(100):
        pool.apply_async(func, ("Hello!", i))


if __name__ == '__main__':
#    TestThread.test()
#    TestThread.test_limit()
    test_thread_pool()
        
