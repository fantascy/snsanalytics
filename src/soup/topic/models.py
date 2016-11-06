from google.appengine.ext import db
from sns.core.base import SoftDeleteBaseModel
from sns.core.core import KeyName
import context

class SoupFeed(SoftDeleteBaseModel,KeyName):
    title = db.StringProperty()
    description = db.TextProperty()
    items = db.ListProperty(db.Text)
    
    @classmethod
    def keyNamePrefix(cls):
        return "SoupFeed:" 
    
    def feedUrl(self):
        return "http://%s/feed/%s"%(context.get_context().long_domain(),self.keyNameStrip())
    
    
    
    
