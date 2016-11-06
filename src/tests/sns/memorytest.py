import sys


class ChannelIdMemoryTest:
    chid_set = set([]) 
    CHID_START = 12345678901234567890

    @classmethod
    def set_chid_set(cls, size=100000):
        cls.chid_set = None
        chid_list = range(cls.CHID_START, cls.CHID_START + size)
        list_size = sys.getsizeof(chid_list)
        print 'list size of %d is %d, avg %d per item.' % (size, list_size, list_size/size)
        cls.chid_set = set(chid_list)
        set_size = sys.getsizeof(cls.chid_set)
        print 'set size of %d is %d, avg %d per item.' % (size, set_size, set_size/size)
        return set_size
        

if __name__ == '__main__':
    ChannelIdMemoryTest.set_chid_set(size=10)        
    ChannelIdMemoryTest.set_chid_set(size=100)        
    ChannelIdMemoryTest.set_chid_set(size=1000)        
    ChannelIdMemoryTest.set_chid_set(size=1000)        
    ChannelIdMemoryTest.set_chid_set(size=10000)
    ChannelIdMemoryTest.set_chid_set(size=100000)

