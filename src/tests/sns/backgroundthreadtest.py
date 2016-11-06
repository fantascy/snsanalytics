from google.appengine.api import background_thread

from threadtest import TestThreadIF


class TestBackgroundThread(TestThreadIF, background_thread.BackgroundThread):
    def __init__(self, name):
        background_thread.BackgroundThread.__init__(self, name=name)
        self.name = name
        

if __name__ == '__main__':
    TestBackgroundThread.test()        
