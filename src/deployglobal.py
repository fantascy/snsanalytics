'''
Place for deployment data
'''

import deploysns, deploymsb, deploysoup, deploycake, deployappspot


APP_DEPLOY_MAP = {
    'snsanalytics.com' : deploysns,
    'mysocialboard.com' : deploymsb,
    'allnewsoup.com' : deploysoup,
    'rippleone.com' : deploycake,
    'appspot.com' : deployappspot,
    'localhost' : deployappspot,
    }


REDIRECT_MAP = {
    'l.sns.mx:8080' : 'localhost.snsanalytics.com:8080',
    'a.sns.mx' : 'a.snsanalytics.com',
    'b.sns.mx' : 'b.snsanalytics.com',
    'c.sns.mx' : 'c.snsanalytics.com',
    'd.sns.mx' : 'd.snsanalytics.com',
    'e.sns.mx' : 'e.snsanalytics.com',
    'w.sns.mx' : 'www.snsanalytics.com',
    '1.sns.mx' : '1.snsanalytics.com',
    '2.sns.mx' : '2.snsanalytics.com',
    '3.sns.mx' : '3.snsanalytics.com',
    '4.sns.mx' : '4.snsanalytics.com',
    '5.sns.mx' : '5.snsanalytics.com',
    '6.sns.mx' : '6.snsanalytics.com',
    'e.sns.mx' : 'e.snsanalytics.com',
    '8.sns.mx' : '8.snsanalytics.com',
    '9.sns.mx' : '9.snsanalytics.com',
                }


APPSPOT_DOMAIN_MAP = {
    'localhost':'l.sns.mx:8080',
    'ripple-a':'ripple-a.appspot.com',
    'ripple-b':'ripple-b.appspot.com',
    'ripple-c':'ripple-c.appspot.com',
    'ripple-d':'ripple-d.appspot.com',
    'ripple-e':'ripple-e.appspot.com',
    'ripple1app':'ripple1app.appspot.com',
    'sns-01':'sns-01.appspot.com',
    'sns-02':'sns-02.appspot.com',
    'sns-03':'sns-03.appspot.com',
    'sns-04':'sns-04.appspot.com',
    'sns-05':'sns-05.appspot.com',
    'sns-06':'sns-06.appspot.com',
    'sns-08':'sns-08.appspot.com',
    'sns-09':'sns-09.appspot.com',
    }

