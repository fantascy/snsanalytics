from django import template 


register = template.Library()   


@register.filter('pluralHandler')    
def pluralHandler(count, singular, plural=None):
    if count is None or count=='' :
        count = 0
    count = int(count)
    descr = singular
    if count > 1 :
        if plural is None :
            descr = singular + 's'
        else :
            descr = plural
    return "%s %s" % (count, descr)

