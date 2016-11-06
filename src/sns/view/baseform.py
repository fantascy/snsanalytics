from django import forms

from sns.api import facade

class NoNameBaseForm(forms.Form):
    def api_module(self):
        pass
        
    def iapi(self):
        """
        Return an iapi instance
        """
        return facade.iapi(self.api_module())
    
    def getModel(self):
        """
        Return the db.Model subclass
        """
        return self.iapi().getModel()
    
class BaseForm(NoNameBaseForm):
    name = forms.CharField(widget=forms.TextInput(attrs={
                           'size':'60'}),
                           max_length=60)
    descr = forms.CharField(widget=forms.Textarea(attrs={
                           'rows':'5','cols':'45'}), required=False)
        
    def clean_name(self):
        """
        Validate name duplication before save.
        We use the convention of form name to check if we need to do a uniqueness check. There must be some better methods.
        """
        name = self.cleaned_data['name']
        if self.__class__.__name__.endswith("CreateForm") and len(self.iapi().query(dict(nameLower=name.lower(), limit=1))) > 0:
            raise forms.ValidationError("Duplicated name!")
        return name


class NameModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, queryset, label_attr='name', required = True,widget=forms.SelectMultiple()):
        self.label_attr = label_attr
        forms.ModelMultipleChoiceField.__init__(self, queryset, required = required, widget=widget)
        
    def label_from_instance(self, obj):
        return getattr(obj, self.label_attr)
    

class NameMultipleChoiceField(forms.MultipleChoiceField):
    def __init__(self, choices, label_attr='name', required = True):
        self.label_attr = label_attr
        forms.MultipleChoiceField.__init__(self, choices, required = required)
        
    def label_from_instance(self, obj):
        return getattr(obj, self.label_attr)
    
class NameMultipleChoiceChangeField(forms.MultipleChoiceField):
    def __init__(self, choices, label_attr='name', required = True,widget=forms.SelectMultiple()):
        self.label_attr = label_attr
        forms.MultipleChoiceField.__init__(self, choices, required = required, widget=widget)
        
    def label_from_instance(self, obj):
        return getattr(obj, self.label_attr)

    
class NameModelMultipleChoiceSmallField(NameModelMultipleChoiceField):
    def __init__(self, queryset, label_attr='name', required = True):
        self.label_attr = label_attr
        count = queryset.count()
        count = min(count,6)
        forms.ModelMultipleChoiceField.__init__(self, queryset, required = required ,widget= forms.SelectMultiple(attrs={'size':str(count)}))
    
class NameMultipleChoiceSmallField(NameMultipleChoiceField):
    def __init__(self, choices, label_attr='name', required = True):
        self.label_attr = label_attr
        count = len(choices)
        count = min(count,6)
        forms.MultipleChoiceField.__init__(self, choices, required = required ,widget= forms.SelectMultiple(attrs={'size':str(count)}))


if __name__ == '__main__':
    pass