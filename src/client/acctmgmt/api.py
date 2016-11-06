from sns.api import consts as api_const
from sns.acctmgmt import consts as acctmgmt_const
from sns.acctmgmt import utils as acctmgmt_util
from client import apiclient
from client.base.api import ApiBase


class AcctMgmtApi(ApiBase):
    API_MODULE = api_const.API_M_ACCTMGMT_YAHOO
    
    def query_all(self, params={}):
        queryParams = params.copy()
        acctType = queryParams.get('acctType')
        stateProp = acctmgmt_util.state_property(acctType)
        states = queryParams.pop('states', None)
        results = []
        if states:
            states = [int(state) for state in states.split(',')]
            for state in states:
                queryParams[stateProp] = state
                results.extend(ApiBase.query_all(self, queryParams))
        else:
            results = ApiBase.query_all(self, queryParams)
        return results
    
    @classmethod
    def transform_obj(cls, obj):
        for attr in acctmgmt_const.ALL_DATETIME_ATTRS:
            cls.transform_datetime(obj, attr)
        return obj
    
    @classmethod
    def transform_datetime(cls, obj, attr):
        if obj.has_key(attr) and obj[attr]:
            obj[attr] = obj[attr][:19]


if __name__ == "__main__":
    apiclient.login_as_admin()
    db = AcctMgmtApi()
    acct = {"name": "a@yahoo.com", 
           "password": "pass001", 
           "tHandle": "ahandle", 
           "tPassword": "pass001", 
           "state": acctmgmt_const.YAHOO_STATE_INIT, 
           "tState": acctmgmt_const.TWITTER_STATE_INIT,
        }
    print db.create(acct)
    
    
