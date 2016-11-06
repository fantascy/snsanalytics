from google.appengine.api import users

import conf
import context
from common import consts as common_const

class ControllerView(object):
    def __init__(self):
        self.dateFormat = common_const.UI_DATETIME_FORMAT
        self.conf = conf
    
    def ctx(self):
        return context.get_context(raiseErrorIfNotFound=False) 

    def raise_error_if_no_login(self):
        self.ctx().get_user()

    def isAdminUser(self):
        if users.is_current_user_admin():
            return True
        else:
            return False
    
    def ga_tracking_code(self):
        if self.isAdminUser() :
            return "TBD"
        else :
            return self.ctx().ga_tracking_code()
    
    def title(self):
        "Title not specified!"

    def template(self):
        pass
    
    
DEFAULT_CONTROLLER_VIEW = ControllerView()
