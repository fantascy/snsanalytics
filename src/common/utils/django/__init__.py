from django.utils import feedgenerator


class SNSFeed(feedgenerator.Atom1Feed):
    def add_item_elements(self, handler, item):
        feedgenerator.Atom1Feed.add_item_elements(self, handler, item)
        
        # Full Image
        full_image = item.get('full_image', None)
        if full_image:
            handler.addQuickElement(u"full_image", full_image)
    