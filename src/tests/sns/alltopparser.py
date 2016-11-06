from sgmllib import SGMLParser


class AllTopListParser(SGMLParser):
    def __init__(self,verbose=0):
        self.verbose = verbose
        self.ish3 = False
        self.currentLink = None
        self._temp_br_text = ''
        self.topics = []
        self.reset()
                
    def handle_data(self, text):
        if self.ish3:
            self._temp_br_text += text
        
    def start_h3(self, attrs):
        self.ish3 = True
        
    def end_h3(self):
        self.ish3 = False  
        self.currentLink = None
        
    def start_a(self,attrs):
        if self.ish3:
            for k, v in attrs:
                k = k.strip()
                v = v.strip()
                if k == 'href':
                    v = v.strip()
                    self.currentLink = v
    
    def end_a(self):
        if self.ish3:
            if self.currentLink is None:
                print 'None link for topic %s'%self._temp_br_text
            else:
                self.topics.append((self._temp_br_text,self.currentLink))
        self._temp_br_text = ''
        
class AllTopPageParser(SGMLParser):
    def __init__(self,verbose=0):
        self.verbose = verbose
        self.isTitle = False
        self.currentLink = None
        self._temp_br_text = ''
        self.feeds = []
        self.reset()
                
    def handle_data(self, text):
        if self.isTitle:
            self._temp_br_text += text
                
    def start_a(self,attrs):
        for k, v in attrs:
            k = k.strip()
            v = v.strip()
            if k == 'href':
                self.currentLink = v
            if k == 'class':
                if v == 'snap_shots':
                    self.isTitle = True
                
    
    def end_a(self):
        if self.isTitle and self.currentLink is not None:
            self.feeds.append((self._temp_br_text,self.currentLink))
        self.isTitle = False
        self._temp_br_text = ''
        self.currentLink = None
        
