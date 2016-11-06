from django import forms

from sns.view.baseform import NoNameBaseForm
from cake import consts as cake_const

class TopicForm(NoNameBaseForm):
    topic = forms.ChoiceField(choices=cake_const.MAIN_MENU_TOPIC_CHOICES,
                                   widget=forms.Select(
                                   attrs={"onchange":"gotoTopicFramePage(this)", "class":"topic-select"}))