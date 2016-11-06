from google.appengine.ext import db
from django import forms

from sns.api import consts as api_const
from sns.view.baseform import NoNameBaseForm
from sns.cont.models import Topic


class TopicForm(NoNameBaseForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}))
    image = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}), required=False)
    fbTopic = forms.CharField(widget=forms.TextInput(attrs={'size':'50'}), required=False)
    description = forms.CharField(widget=forms.Textarea(attrs={
                           'rows':'5','cols':'45'}), required=False)
        
    def __init__( self, *args, **kwargs ):
        super(TopicForm, self ).__init__( *args, **kwargs )
        choices = []
        topics = Topic.all().fetch(limit=1000)
        if kwargs.has_key('initial') and kwargs['initial'].has_key('id'):
            topic = db.get(kwargs['initial']['id'])
            key_name = topic.keyNameStrip()
        else:
            key_name = ''
        for topic in topics:
            if topic.keyNameStrip()!= key_name:
                choices.append((topic.keyNameStrip(),topic.name))
        self.fields['relatedTopics'] = forms.MultipleChoiceField(choices=choices, required=False)
        self.fields['parentTopics'] = forms.MultipleChoiceField(choices=choices, required=False)
        
    def api_module(self):
        return api_const.API_M_TOPIC
    
class TopicCreateForm(TopicForm):
    pass

class TopicUpdateForm(TopicForm):
    id=forms.CharField(widget=forms.HiddenInput)
    
        
class TopicUploadForm(NoNameBaseForm):
    file = forms.FileField()
