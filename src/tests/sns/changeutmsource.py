from sns.api import consts as api_const

from client import conf, apiclient


def changeCampaignAnalytics():   
    params={} 
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    
    #moduleName=api_const.API_M_POSTING_RULE
    moduleName=api_const.API_M_CAMPAIGN
    operation='changeanalyticssource'      
    
    while True:
        response = apiclient.call_api(apiclient.server_api_domain(), moduleName, operation, params)
        if response != 'null':                
            response=eval(response)   
            params=response
        else:
            break
    print 'over'
    
            
def main():
    changeCampaignAnalytics()
    

if __name__ == "__main__" :
    main()