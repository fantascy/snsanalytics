# -*- coding: utf-8 -*-
from datetime import datetime
import logging
import urllib
import urllib2
import urlparse
from sgmllib import SGMLParser
import StringIO

from google.appengine.api.urlfetch import fetch as urlfetch 
from PIL import Image

from common.utils import string as str_util, url as url_util


class BasePageParser(SGMLParser):
    def reset(self):    
        SGMLParser.reset(self)
                
    @classmethod
    def is_valid_image(cls, src, limit=200):
        retry = 0
        while retry < 3:
            retry +=1
            try:
                now = datetime.utcnow()
                data = urlfetch(src,deadline=5).content
                then = datetime.utcnow()
                timeDelta = then - now
                logging.debug('Time for fetch img data %s : %s'%(src,str(timeDelta)))
                img = Image.open(StringIO.StringIO(data))
                size = img.size
                big = max(size[0],size[1])
                small = min(size[0],size[1])
                if big > limit and big/small < 3:
                    return True
            except  Exception, ex :
                ex = str(ex)
                if ex.find('timed out') != -1:
                    return True
                elif ex.find('ApplicationError: 5') != -1:
                    continue
                else:
                    logging.warning('Error fetching image %s! %s' % (src, ex))
                break
        return False


class PageFeedUrlParser(BasePageParser):
    """
    Find feed URL from an HTML page.
    """
    def __init__(self, page=None, verbose=0):
        self.page = page
        BasePageParser.__init__(self, verbose=0)

    def reset(self):
        BasePageParser.reset(self)
        self.feedurls=[]

    def start_link(self,attrs):
        isRel=False
        isFeed=False
        for k, v in attrs:
            if k=="rel" and v=="alternate":
                isRel=True
            if k=="type" and (v.find("atom") or v.find("rss")!=-1):
                isFeed=True
            if k=="href":
                url=v
        if isRel and isFeed and url:
            self.feedurls.append(url)

    def findFeedUrl(self):
        """
        Notice this method doesn't validate the feed
        """
        try :
            usock = urllib2.urlopen(self.page)
            self.feed(usock.read())
            usock.close()
            self.close()
            if len(self.feedurls)>0:
                url = self.feedurls[0]
                if url.startswith("http"):
                    return url
                else:
                    return urlparse.urljoin(self.page, url) 
                return self.feedurls[0]
        except:
            logging.exception("Could not find feed URL from page: %s" % self.page)
        return None


class FeedEntryParser(BasePageParser):
    def reset(self):    
        BasePageParser.reset(self)
        self.img = None
                
    def start_img(self, attrs):
        for k, v in attrs:
            if k == 'src':
                src = v.strip()
                if src.startswith('http') and self.img is None and self.is_valid_image(src, limit=50):
                    self.img = src

    
class RedditPageParser(BasePageParser):
    def __init__(self, url, verbose=0):
        index = url.find('//')
        full = url[index:]
        head = url[:index]
        domain = urllib.splithost(full)[0]
        domain = head + '//' + domain
        self.scheme_domain = domain
        self.title = None
        BasePageParser.__init__(self, verbose=0)
        
    def reset(self):                              
        BasePageParser.reset(self)
        self.reddit = None
        self.title = None
        self.is_title = False
        
    def handle_data(self, text):
        if self.is_title:
            self.title = text
        
    def start_title(self, attrs):
        self.is_title= True 
            
    def end_title(self):    
        self.is_title=False
        
    def start_a(self, attrs):
        is_class_title = False 
        for k, v in attrs:
            if k != 'class': continue
            v = v.strip().split()
            if 'title' in v:
                is_class_title = True
        if not is_class_title: return
        for k, v in attrs:
            if k != 'href': continue
            v = v.strip()
            if v.startswith('/') and self.scheme_domain: v = self.scheme_domain + v
            if not v.startswith('http'): return
            self.reddit = v
            return

    
class SPageParser(BasePageParser):
    def __init__(self, verbose=0):
        self.scheme_domain = None
        BasePageParser.__init__(self, verbose=verbose)

    @classmethod
    def get_prepared_parser(cls, url):
        data = url_util.fetch_url(url)
        parser = cls()
        parser.feed(data)
        return parser
        
    def reset(self):                              
        BasePageParser.reset(self)
        self.is_title=False
        self.is_p = False
        self.is_br = False
        self.after_title = False
        self.is_h = False
        self.no_script = False
        self.imgs =[]
        self.allImgs = []
        self.theOne = None
        self.keywords = None
        self.headerImg = None
        self.videoImg = None
        self.video = []
        self.title = None
        self.og_title = None
        self.og_url = None
        self.ps = []
        self.br = []
        self.pics = []
        self._temp_br_text = ''
        self.tempP = ''
        self._temp_title_text = ''
        self.code = 'utf-8'
        self.plength = 0
        self.page_fetch = True
    
    @property
    def url(self):
        return self.og_url
        
    def feed(self, data,is_quick=False):
        if data is None:
            return
        try:
            BasePageParser.feed(self, data)
        except Exception:
            logging.exception("Error when parsing data for url! %s" % self.url)
        try:
            self.decode_text(is_quick)
        except Exception:
            logging.exception("Error when parsing/decoding data for url! %s" % self.url)
        if is_quick and not self.title and not self.pics:
            try:
                Image.open(StringIO.StringIO(data))
                self.pics = [self.url]
            except:
                pass
                   
    def parse_declaration(self, i):
        try:
            return BasePageParser.parse_declaration(self, i)
        except Exception:
            logging.exception("Error when parsing declaration for url! %s" % self.url)
            return self.parse_endtag(i)
    
    def get_title(self):
        return self.og_title if self.og_title else self.title
        
    def get_keywords(self):
        if self.keywords:
            keywords = []
            for item in self.keywords.split(','):
                keyword = str_util.strip(item)
                if keyword:
                    keywords.append(keyword)
            return keywords
        return [] 
        
    def start_title(self, attrs):
        self.is_title= True 
            
    def end_title(self):    
        self.is_title = False
        self.title = str_util.strip_one_line(self._temp_title_text)
        self._temp_title_text = ''
        
    def process_title(self):
        if not self.after_title:
            self.after_title = True
            self.imgs = []
            
    def start_h1(self, attrs):
        self.is_h = True
        
    def end_h1(self):
        self.is_h = False    
        
    def start_h2(self, attrs):
        self.is_h = True
        
    def end_h2(self):
        self.is_h = False  
        
    def start_h3(self, attrs):
        self.is_h = True
        
    def end_h3(self):
        self.is_h = False  
        
    def start_noscript(self, attrs):
        self.no_script = True
        
    def end_noscript(self):
        self.no_script = False  
                
    def start_p(self, attrs):
        if self.is_p == False:
            self.is_p= True 
        else:
            if self._is_valid_text(self.tempP) and self.page_fetch and self.plength <=1:
                text_p = self.tempP
                self.ps.append(text_p)
            self.tempP = ''
            self.plength = 0
            
    def end_p(self):    
        self.is_p=False
        if self._is_valid_text(self.tempP) and self.page_fetch:
            text_p = self.tempP
            self.ps.append(text_p)
        self.tempP = ''
        self.plength = 0
        
    def start_br(self, attrs):
        self.is_br =True
                        
    def handle_data(self, text):
        if self.is_h:
            if self._is_prefix_of_title(text):
                self.process_title()
        if len(self.br) < 1:
            if self.is_br:
                if self._is_valid_text(self._temp_br_text) and self.page_fetch:
                    text_b = self._temp_br_text
                    self.br.append(text_b)
            self._temp_br_text = text
            self.is_br = False
        if self.is_title and not self.title:
            self._temp_title_text = text
        if self.is_p:
            if len(self.ps) >= 1:
                pass
            else:
                self.plength += 1
                
    def start_link(self,attrs):
        be_video_src = False
        be_img_src = False
        for k, v in attrs:
            v = v.lower().strip()
            if k == 'rel' and v == 'video_src':
                be_video_src = True
            if k == 'rel' and v == 'image_src':
                be_img_src = True
                
        if be_video_src:
            for k, v in attrs:
                if k == 'href':
                    self.video.append(v)
                    
        if be_img_src:
            for k, v in attrs:
                if k == 'href':
                    self.headerImg = v
        
    def start_meta(self, attrs):   
        attr_map = dict(attrs)
        content = attr_map.get('content', None)
        content = str_util.strip(content)
        if content:
            content_lower = str_util.lower_strip(content)
            if content_lower.find('charset') != -1 and content_lower.find('=') != -1:
                index = content_lower.find('=')
                code = content_lower[index+1:].strip()
                self.code = self.parse_code(code)
        for k, v in attrs:
            k = str_util.lower_strip(k)
            v = str_util.lower_strip(v)
            if self._match_meta(k, v, 'keywords'):
                self.keywords = content
            elif self._match_meta(k, v, 'description'):
                if self._is_valid_text(content):
                    self.ps = [content] 
            elif self._match_meta(k, v, 'og:title'):
                self.og_title = str_util.strip_one_line(content)
            elif self._match_meta(k, v, 'og:url'):
                self.og_url = str_util.strip_one_line(content)
                self.scheme_domain = url_util.scheme_domain(self.og_url)
            elif self._match_meta(k, v, 'og:description'):
                if self._is_valid_text(content):
                    self.ps = [content] 
            elif self._match_meta(k, v, 'og:image'):
                self.headerImg = content
            elif self._match_meta(k, v, 'og:video'):
                self.video = [content]
                
    def _match_meta(self, key, value, target_value):
        if key in ['name', 'itemprop', 'property']:
            return value == target_value
        return False
                
    def parse_code(self,code):
        code = code.lower().strip()
        try:
            'a'.decode(code)
        except:
            code = 'utf-8'
        return code                      
           
    def decode_text(self, is_quick):
        if self.title:
            self.title = self.title.decode(self.code, 'ignore')
        ps = []
        for p in self.ps:
            ps.append(p.decode(self.code,'ignore'))
        self.ps = ps
        br = []
        for b in self.br:
            br.append(b.decode(self.code,'ignore'))
        self.br = br
        if self.headerImg:
            self.headerImg = self.headerImg.decode(self.code, 'ignore')
        if self.keywords:
            self.keywords = self.keywords.decode(self.code, 'ignore')[:500]
        if self.headerImg and self.headerImg.startswith('/') and self.scheme_domain:
            self.headerImg = self.scheme_domain + self.headerImg
                    
        if is_quick:
            pics = sorted(self.allImgs , key=lambda e: e[3],reverse=True)
            for pic in pics:
                self.pics.append(pic[0])
            if self.headerImg is not None:
                if len(self.pics)>0 and not isinstance(self.pics[0], unicode) and not isinstance(self.pics[0], str):
                    logging.info("TEMP_DEBUG headerImg='%s'; pics='%s'." % (self.headerImg, str(self.pics)))
                for pic in self.pics:
                    if pic == self.headerImg:
                        self.pics.remove(pic)
                self.pics.insert(0, self.headerImg) 
        elif self.headerImg is None:
            if len(self.imgs) > 0:
                gotBig = False
                for img in self.imgs:
                    if img[1] is not None and img[2] is not None:
                        smaller = min(img[1],img[2])
                        if smaller > 250:
                            gotBig = True
                            self.theOne = img[0]
                            break
                if not gotBig:
                    if self.after_title:
                        fetchTime = 0
                        gotOne = False
                        for theImg in self.imgs:
                            if gotOne :
                                break
                            fetchTime += 1
                            if fetchTime > 5:
                                break
                            theSrc = theImg[0]
                            retry = 0
                            while retry < 3:
                                retry +=1
                                try:
                                    now = datetime.utcnow()
                                    data = urlfetch(theSrc,deadline=5).content
                                    then = datetime.utcnow()
                                    timeDelta = then - now
                                    logging.debug('Time for fetch img data %s : %s'%(theSrc,str(timeDelta)))
                                    img = Image.open(StringIO.StringIO(data))
                                    size = img.size
                                    big = max(size[0],size[1])
                                    small = min(size[0],size[1])
                                    if big > 50 :
                                        gotOne = True
                                    if big > 200 and big/small < 3:
                                        self.theOne = theSrc
                                    break
                                except  Exception, ex :
                                    ex = str(ex)
                                    if ex.find('timed out') != -1:
                                        self.theOne = theSrc
                                    elif ex.find('ApplicationError: 5') != -1:
                                        continue
                                    else:
                                        logging.warning('Error fetching image %s! %s' % (theSrc, ex))
                                    break
                    else:
                        self.get_size_img()
        self._videoProcess() 
        self._process_denial() 
        if self.theOne is not None:
            self.theOne = self.theOne.decode(self.code,'ignore')[:500]
        
    def get_size_img(self):
        for img in self.imgs:
            if img[1] is not None and img[2] is not None:
                big = max(img[1],img[2])
                small = min(img[1],img[2])
                if big > 200 and big/small < 3:
                    self.theOne = img[0]
                    break
            elif img[1] is not None:
                if img[1] > 200:
                    if self.is_valid_image(img[0]):
                        self.theOne = img[0]
                        break
            elif img[2] is not None:
                if img[2] > 200:
                    if self.is_valid_image(img[0]):
                        self.theOne = img[0]
                        break
            
    def _process_denial(self):
        if self.title:
            title = str_util.normalizeTitle(self.title)
            denied = False
            flags = ['access denied', '403 forbidden', '404 page not found']
            for flag in flags:
                if title.find(flag) != -1:
                    denied = True
                    break
            if denied:
                self.title = None
                self.ps = []
                self.br = []
                
    def _videoProcess(self):
        if self.scheme_domain == 'http://www.youtube.com' or self.scheme_domain == 'http://youtube.com':
            self._youtube()
        if self.scheme_domain == 'http://www.vimeo.com' or self.scheme_domain == 'http://vimeo.com':
            self._vimeo()
        elif self.scheme_domain == 'http://www.dailymotion.com' or self.scheme_domain == 'http://dailymotion.com':
            self._dailymotion()
        if len(self.video)>0:
            videoSrc = self.video[0]
            self.video = [self.videoPreprocess(videoSrc)]
            self.videoImg = self.headerImg
            
    def videoPreprocess(self,src):
        if src.startswith('http://www.presstv.ir/player'):
            src = src.replace('&autostart=true','')
        return src
            
    def _youtube(self):
        text = 'Sorry for the interruption'
        for p in self.ps:
            if p.find(text) != -1:
                self.ps.remove(p)
        for b in self.br:
            if b.find(text) != -1:
                self.br.remove(b)
        
    def _vimeo(self):
        y_id = None
        url = self.url
        path = urllib.splitquery(url)[0]
        path = path.rstrip('/')
        index = path.rfind('/')
        if index != -1:
            y_id = path[index+1:]
        try:
            y_id = int(y_id)
            videosrc = 'http://player.vimeo.com/video/'+str(y_id)+'?title=0&amp;byline=0&amp;portrait=0'
            self.video.append(videosrc)
            self.videoImg = self.headerImg
        except:
            pass
                
    def _dailymotion(self):
        vs = []
        for v in self.video:
            path = urllib.splitquery(v)[0]
            vs.append(path)
        self.video = vs
        self.videoImg = self.headerImg
        
    def _parse_image_size(self, value):
        try:
            if not value:   return None
            if value.find('%')!=-1:
                return None
            value = value.lower().replace('px', '')
            value = value.replace(';', '')
            value = str_util.strip(value)
            if not value:   return None
            return int(float(value))
        except:
            logging.warning("Invalid image size: %s" % value)
            return None
        
    def start_img(self,attrs):
        if self.no_script:
            return
        width = None
        height = None
        src = None
        for k, v in attrs:
            if k == 'src':
                src = v.strip()
                if src.startswith('/') and self.scheme_domain:
                    src = self.scheme_domain + src.decode(self.code, 'ignore')
                if src.startswith('http') and src.find('fbcdn.net') == -1:
                    pass
                else:
                    src = None
            elif k == 'height':
                height = self._parse_image_size(v)
            elif k == 'width':
                width = self._parse_image_size(v)
        if src is not None:
            added = False
            for imgInfo in self.allImgs:
                if hash(src) == hash(imgInfo[0]):
                    added = True
                    break
            if not added:
                toAdd = False
                toStrictAdd = False
                if height is not None and width is not None:
                    if height > 50 or width > 50:
                        toAdd = True
                        size = max(height,width)
                    if height > 150 or width > 150:
                        toStrictAdd = True
                elif height is not None:
                    if height > 50:
                        toAdd = True
                        size = height
                    if height > 150:
                        toStrictAdd = True
                elif width is not None:
                    if width >= 50:
                        toAdd = True
                        size = width
                    if width >= 150:
                        toStrictAdd = True
                else:
                    toAdd = True
                    toStrictAdd = True
                    size = 0
                if toAdd:
                    self.allImgs.append([src,width,height,size])
                if toStrictAdd:
                    self.imgs.append([src,width,height,size])

    def _is_prefix_of_title(self, text):
        if not self.title:
            return False
        text = str_util.normalizeTitle(text)[:10]
        title = str_util.normalizeTitle(self.title)
        return title.startswith(text)
        
    def _is_valid_text(self, text):
        text = str_util.strip(text)
        if text is None:
            return False
        text = text.replace(' ', '')
        if len(text) < 120:
            return False
        elif text.count('=') >= 2:
            return False
        elif text.count('{') >= 1:
            return False
        elif text.count('|') >= 2:
            return False
        else:
            return True

