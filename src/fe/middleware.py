from sns import middleware as sns_middleware


def redirect_to_user_init(request, modelUser):
    if request.path.startswith('/fe/') and request.path.endswith('.html') :
        return False
    return sns_middleware.redirect_to_user_init(request, modelUser)


def process_request(request):
    return sns_middleware.process_request(request)


def process_exception(request, exception):
    return sns_middleware.process_exception(request, exception)


