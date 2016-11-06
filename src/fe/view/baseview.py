from sns.view.baseview import BaseView as SNSBaseView
from fe.api.facade import iapi as fe_iapi

class BaseView(SNSBaseView):
    iapi = fe_iapi
    app_path = 'fe' 
            
