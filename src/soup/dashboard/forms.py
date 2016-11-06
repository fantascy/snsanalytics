from django import forms


class ShareForm(forms.Form):
    title =forms.CharField(widget=forms.TextInput(attrs={"class":"input-field","id":"title-input"}),max_length=150)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows":"4"}))
    keywords = forms.CharField(widget=forms.HiddenInput)
    mediaType = forms.IntegerField(widget=forms.HiddenInput)
    topic =forms.CharField(widget=forms.TextInput(attrs={"size":"25",
                                                         "id":"topic-input", 
                                                         "placeholder":"Type in a topic or pick a popular one below."}),
                           max_length=150)
    showImg = forms.BooleanField(widget=forms.CheckboxInput(attrs={'onclick':'toggleImgMedia(this)'}), required=False)
    postToFacebook = forms.BooleanField(widget=forms.CheckboxInput(attrs={}), required=False)
    postToTwitter = forms.BooleanField(widget=forms.CheckboxInput(attrs={}), required=False)
    
    
        

