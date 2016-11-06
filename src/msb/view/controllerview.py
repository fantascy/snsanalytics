import context
from common.view.controllerview import ControllerView as CommonControllerView


class ControllerView(CommonControllerView):
    def __init__(self, viewName=None, pageTitle=None, request=None):
        """ Make sure to raise error if user is not logged in and login is required. """
        context.get_context().get_user()
        self.navigation = []
        if viewName:
            self.viewName = viewName
        else:
            self.viewName = "Mysocialboard"
        if pageTitle:
            self.pageTitle = pageTitle
        else:
            self.pageTitle = "My Social Board."
    

