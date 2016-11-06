from sns.email.models import MailExecution
from sns.email.models import MailCampaign

"""
event type
"""
ON_REGISTER              =        "on_register" 

"""
command
"""
SEND_MAILS                  =        "send mails"
CLEAN_CACHE                 =        "clean cache"


"""
a Map of event dispatcher
"""
_EVENT_HANDLER_MAP = {
                      
    #ON_REGISTER                 :             OnRegisterEmailEventHandler,
    
                }

_COMMAND_HANDLER_MAP = {
                      
    #SEND_MAILS                     :             OnSendEmailsCommandHandler,
    #CLEAN_CACHE                     :             OnCleanCacheCommandHandler,         
    
                }
_EXECUTION_MAP = {
        SEND_MAILS:MailExecution,
                  }
_CAMPAIGN_MAP  = {
        SEND_MAILS:MailCampaign,
                  }