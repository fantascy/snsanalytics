import logging
from django.http import HttpResponse
from cake.user.models import Feedback


def feedback(request):
    subject = request.REQUEST.get("subject", None)
    body = request.REQUEST.get("body", None)
    email = request.REQUEST.get("email", None)
    logging.info("Collected a feedback:\nemail - %s\nsubject - %s\nbody - %s" % (email, subject, body))
    feedback = Feedback(subject=subject, body=body, email=email)
    feedback.put()
    return HttpResponse("success") 


