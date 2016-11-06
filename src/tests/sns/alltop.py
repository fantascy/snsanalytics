"""
How to run this program?

Go to src directory. There are 2 steps. Assuming category name is 'work', then the 2 steps are:
step 1: python test\alltop.py work 1
step 2: python test\alltop.py work 2
"""

import sys
import datetime
import csv

from common.utils import url as url_util
from common.content import feedfetcher
from alltopparser import AllTopListParser, AllTopPageParser


PATH = "data/alltop"
 

def parse_topic_list(category):
    startTime = datetime.datetime.now()
    print "Started parsing topic list for category '%s'." % (category, )
    listHtml = open("%s/%s.html" % (PATH, category))
    data = listHtml.read()
    listHtml.close()
    parser = AllTopListParser()
    parser.feed(data)
    output = open("%s/%s_topics.csv" % (PATH, category), 'w')
    writer = csv.writer(output)
    for topic in parser.topics:
        writer.writerow([category, topic[0], topic[1]])
    output.close()
    endTime = datetime.datetime.now()
    timeDelta = endTime - startTime
    print "Finished parsing topic list for category '%s' in %d seconds." % (category, timeDelta.seconds)
    

def parse_topic_feeds(category):
    startTime = datetime.datetime.now()
    print "Started parsing topic feeds for category '%s'." % (category, )
    topicFile = csv.reader(open("%s/%s_topics.csv" % (PATH, category), 'r'))
    allFeeds = []
    topicCount = 0
    feedCount = 0
    while True :
        topic = None
        topicName, link = (None, None)
        try :
            topic = topicFile.next()
            topicName, link = tuple(topic[1:3])
        except :
            topic = None
            break
        topicStartTime = datetime.datetime.now()
        topicFeedCount = 0
        try:
            data = url_util.fetch_url(link, agent=False)
            parser = AllTopPageParser()
            parser.feed(data)
            for feed in parser.feeds:
#                if topicFeedCount>1 :
#                    break
                try:
                    print ("Parsing feed %s" % str(feed))
                    blogName = feed[0]
                    blogUrl = feed[1]
                    fetcher = feedfetcher.FeedFetcher(blogUrl)
                    allFeeds.append([category, topicName, blogName, blogUrl, str(fetcher.urlFileStreamOrString)])
                except Exception, e1:
                    print 'Error when fetching feed %s' % str(e1)
                topicFeedCount += 1
                feedCount += 1
        except Exception, e2:
            print "Error when parsing topic '%s'" % str(e2)
        topicCount += 1
        topicEndTime = datetime.datetime.now()
        topicProcessTime = (topicEndTime - topicStartTime).seconds
        if topicFeedCount>0 :
            print "[%s] Finished parsing %d feeds for topic '%s' in %d seconds. Average time per feed: %.2f seconds." \
                    % (topicEndTime, topicFeedCount, topicName, topicProcessTime, 1.0*topicProcessTime/topicFeedCount)
        else :
            print "Topic '%s' has 0 feed!" % topic
    output = open("%s/%s_feeds.csv" % (PATH, category), 'w')
    writer = csv.writer(output)
    writer.writerow(['Category','Topic','Blog Name','Blog Url','Feed Url'])
    for feed in allFeeds:
        writer.writerow(feed)
    output.close()
    endTime = datetime.datetime.now()
    timeDelta = (endTime - startTime).seconds
    print "Finished parsing %d feeds from %d topics for category '%s' in %d seconds." % (feedCount, topicCount, category, timeDelta)
        

if __name__ == "__main__" :
    category = sys.argv[1]
    step = sys.argv[2]
    if int(step)==1 :
        parse_topic_list(category)
    else :
        parse_topic_feeds(category)
        
    