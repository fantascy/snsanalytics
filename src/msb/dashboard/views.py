from django.views.generic.simple import direct_to_template

import context 
from msb.view.controllerview import ControllerView


class DashBoardControllerView(ControllerView):
    def __init__(self):
        context.get_context().set_login_required(False)
        ControllerView.__init__(self, viewName="Home")
        

def home(request):
    return direct_to_template(request, 'msb/index.html', dict(view = DashBoardControllerView()))
