from django.views.generic.simple import direct_to_template

import context 
from sns.core.core import get_user
from fe.view.controllerview import ControllerView


class DashBoardControllerView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self, viewName="Home")
        

def home(request):
    context.get_context().set_login_required(False)
    user = get_user()
    if request.path == '/' and user is not None:
        return direct_to_template(request, 'fe/layout/contents.html', dict(view = DashBoardControllerView()))
    if user is not None:
        return direct_to_template(request, 'fe/dashboard.html', dict(name=context.get_context().app_name(),view = DashBoardControllerView()))
    else:
        return direct_to_template(request, 'fe/index.html', dict(name=context.get_context().app_name(),view = DashBoardControllerView()))

