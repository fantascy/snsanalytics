r"""
fulltext matcher
fetch content from an article's url, and match it against a set of keywords.
"""

import logging
import httplib
import re
from urlparse import urlparse
from sets import ImmutableSet

from common.utils import html2text
from common.utils.porter import PorterStemmer


#boundary chars, to be replace with " " in text match
boundary_chars_re=re.compile("[\[\]#]")


class FulltextMatcher:
    r"""
    fulltext matcher
    """
    def __init__(self):
        pass
    
    def getText(self, url):
        r"""
          download html page and turn it into plain text. 
          This method will return empty string when we cannot get content
        """
        try:
            (scheme, netloc, path, params, querystring, fragment) = urlparse(url)
            if not scheme in ('http', 'https'):
                return ""
            conn = httplib.HTTPConnection(netloc)
            requesturl=path
            if querystring:
                requesturl="?".join((requesturl,querystring))
                
            headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                       "User-Agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.11)",
                       "Accept-Language": "en-us,en;q=0.7,zh;q=0.3",
                       "Accept-Charset": "utf-8,ISO-8859-1"
                        }

            conn.request("HEAD", requesturl,headers=headers)
            res = conn.getresponse()
            conn.close()
            #when returned error
            if res.status > 400:
                return ""
            
            if res.getheader("content-type") == None:
                return ""
            elif res.getheader("content-type").find("html") == -1 and res.getheader("content-type").find("json")==-1:
                return ""
            
            #now get real content
            
            conn.request("GET",requesturl,headers=headers)
            response = conn.getresponse()
            html = response.read()
            conn.close()
            from feedparser import _getCharacterEncoding as enc
            encoding = enc(dict(response.getheaders()), html)[0]
            if encoding == 'us-ascii': 
                encoding = 'utf-8'
            decoded = html.decode(encoding,'ignore')
            return html2text.html2text(decoded)
        except Exception,ex:
            if str(ex).find('ApplicationError: 2') != -1:
                logging.warning("Unexpected error processing %s : %s"%(url,str(ex)))
            else:
                logging.exception("Unexpected error processing %s" % (url))
            return ""


    def match_url(self, keywords, url):
        r"""
          match a list of keywords against a url, return a score. 
          return matched keywords as a list
        """
        return self.match_text(keywords, text=self.getText(url))
        
    
    def match_text(self, keywords=[], text=""):
        r"""
        match a list keywords against a text string, return matched keywords as a list
        """
        if not keywords:
            return []
        if not text:
            return []
        matches=[]
        ksets = ImmutableSet(map(lambda x:(x.lower(),x), keywords))
        for key, kwd in ksets:
            text_lower = ' ' + unicode(text.lower()) + ' '
            key_lower = unicode(key.lower())
            p = re.compile("\W"+key_lower+"\W")
            if not p.search(text_lower) == None:
                matches.append(kwd)
        return matches
    
    def match_text_with_frequency(self, keywords=[], text=""):
        r"""
        match text by stemming suffix first and return keywords frequency.
        this method returns a list, and each item includes (keyword,frequency),
        such as [("nba",2),("yao",3)]..
        """
        if not keywords:
            return []
        if not text:
            return []
        stemmer=PorterStemmer()
        querystems = map(lambda x:(stemmer.stem(x.lower(),0,len(x)-1),x), keywords)
        matches=[]
        textwords=map(lambda x: stemmer.stem(x,0,len(x)-1),boundary_chars_re.sub(" ",text.lower()).split())
        for key,kwd in querystems:
            count=textwords.count(key)
            if count>0:
                matches.append((kwd,count))
        return matches
