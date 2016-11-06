from google.appengine.ext import db
from django import forms

from common.utils import url as url_util
from sns.api import consts as api_const
from sns.view.baseform import NoNameBaseForm
from sns.view import consts as view_const
from sns.cont.models import Topic
from sns.cont import consts as cont_const
from sns.cont.api import BaseFeedProcessor


class FeedForm(NoNameBaseForm):
    url  = forms.CharField(max_length=480,widget=forms.TextInput(attrs={'size':'50'}))
    
    def api_module(self):
        return api_const.API_M_FEED
    
    def clean_url(self):
        """
        get feed name by reading its url
        """
        url=self.cleaned_data['url']
        url=url_util.sanitize_url(url)
        noCheck = False
        if self.data.has_key('id'):
            feed = db.get(self.data['id'])
            if feed.url == url:
                noCheck = True
        if noCheck:
            return url +"***"+self.data['name']+"***"+url
        else:
            fetcher = BaseFeedProcessor.get_feed_fetcher_by_url(url)
            if not fetcher.is_valid:
                raise forms.ValidationError("invalid feed!")
            return "%s***%s***%s" % (fetcher.url(), fetcher.title, fetcher.url())


class FeedCreateForm(FeedForm):
    pass
    
    
class FeedUpdateForm(FeedForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}))    
    id=forms.CharField(widget=forms.HiddenInput)
    

class FeedTopicForm(forms.Form):
    id=forms.CharField(widget=forms.HiddenInput(attrs={"id":'feed_id'}))
    
    def __init__( self, *args, **kwargs ):
        super(FeedTopicForm, self ).__init__( *args, **kwargs )
        choices = []
        topics = Topic.all().fetch(limit=2000)
        for topic in topics:
            choices.append((topic.keyNameStrip(),topic.name))
        self.fields['topics'] = forms.MultipleChoiceField(choices=choices)
    
    def clean_topics(self):
        topics = self.cleaned_data['topics']
        return topics
    

class FeedSortByForm(forms.Form):    
    type = forms.ChoiceField(choices=[('nameLower',"Name"),('modifiedTime',"Last modified time")],
                                   widget=forms.Select(
                                   attrs={"id":"id_sortBy_type","name":"id_sortBy_type","onchange":"sortByKeyWord()"}),required=True)
    order = forms.ChoiceField(choices=view_const.LIST_ORDER,
                                   widget=forms.Select(
                                   attrs={"id":"id_direct_type","name":"id_direct_type","onchange":"sortByKeyWord()"}),required=True)
    paginate = forms.ChoiceField(choices=view_const.LIST_PAGINATE,
                                   widget=forms.Select(
                                   attrs={"id":"id_paginate_num","name":"id_paginate_num","onchange":"sortByKeyWord()"}),required=True)


class CustomFeedUploadForm(NoNameBaseForm):
    file = forms.FileField()
    

class CustomTypeForm(NoNameBaseForm):
    fsid = forms.ChoiceField(choices=cont_const.FEED_SOURCE_CHOICES,
                                   widget=forms.Select(
                                   attrs={"onchange":"chooseCustomFeed(this)"}))