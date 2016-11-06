import context
from common.view.controllerview import ControllerView as CommonControllerView


_BASE_TAB_MENU =   [   
                        ("Marketing Channels" , None,   [
                            ("Twitter Accounts", "/chan/"),
                            ("Facebook Accounts","/chan/facebook/"),
                            ("Facebook Pages","/chan/fbpage/"),
                                                        ]),
                   ]


_FOLLOW_TAB = ("Follow Campaigns", None, 
                            [
                            ("Follow Campaigns", "/fe/follow/account/"),           
                            ])


_SYSTEM_TAB = ("System" , None,   [
                            ("Users", "/usr/"),
                            ('All Follow Campaigns','/fe/follow/all/rule/list/'),
                             ('Suspended Follow Campaigns','/fe/follow/suspend/rule/list/'),
                            ('System Settings','/fe/follow/system/'),
                                ])                         


class ControllerView(CommonControllerView):
    def __init__(self, viewName=None, pageTitle=None):
        CommonControllerView.__init__(self)
        """ Make sure to raise error if user is not logged in and login is required. """
        context.get_context().get_user()
        self.navigation = _BASE_TAB_MENU + [_FOLLOW_TAB, _SYSTEM_TAB]
        if viewName:
            self.viewName = viewName
        else:
            self.viewName = context.get_context().app_name()
        if pageTitle:
            self.pageTitle = pageTitle
        else:
            self.pageTitle = context.get_context().app_name()

