import urllib2

from asynchttpclient import http_client as async_client

from client import conf, apiclient


def job_count(host, port):
        apiurl = 'http://%s:%s/api/posting/rule/jobcount' % (host, port)
        serv_req = urllib2.Request(apiurl)
        serv_resp = urllib2.urlopen(serv_req)
        serv_resp_body = serv_resp.read()
        print "batch count is %s" % serv_resp_body
        return int(serv_resp_body)
    

def main():
    host = apiclient.server_domain().split(':')[0]
    port = apiclient.server_port()

    c_article = async_client(host, port, '/api/posting/rule/article/batch_post', 'GET')
    c_article.send(c_article.buffer)
    print "sent one batch post request for article posting rule!"

    c_feed = async_client(host, port, '/api/posting/rule/feed/batch_post', 'GET')
    c_feed.send(c_feed.buffer)
    print "sent one batch post request for feed posting rule!"

if __name__ == "__main__":
    apiclient.login(apiclient.server_domain(), conf.ADMIN_USER, conf.ADMIN_PASSWD, conf.APPLICATION_ID, conf.IS_DEV_SERVER, True)
    main()
