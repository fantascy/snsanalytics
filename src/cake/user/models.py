from google.appengine.ext import db

from sns.core.base import DatedBaseModel


class Feedback(DatedBaseModel):
    email = db.StringProperty()
    subject = db.StringProperty()
    body = db.TextProperty()
    