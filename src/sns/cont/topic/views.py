import logging
import csv
import StringIO

from django.template import RequestContext
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic.list_detail import object_list

from common import consts as common_const
from common.utils import string as str_util
from sns.serverutils import deferred
import context
from sns.api import consts as api_const
from sns.core.core import User
from sns.cont.models import Topic
from sns.feedbuilder.models import TopicScoreFeedBuilder
from sns.log.models import CmpTwitterAcctStats
from common.view import utils as view_util
from sns.view.baseview import BaseView
from sns.cont.views import ContentControllerView
from sns.cont.topic import api as topic_api
from sns.cont.topic.forms import TopicCreateForm, TopicUpdateForm, TopicUploadForm


class TopicView(BaseView, ContentControllerView):
    def __init__(self):
        BaseView.__init__(self,api_const.API_M_TOPIC,TopicCreateForm,TopicUpdateForm)
        ContentControllerView.__init__(self)
    
        
def topic_create(request):
    view = TopicView()
    return view.create(request, view, template_name="topic_form.html")


def topic_update(request):
    view = TopicView()
    return view.update(request, view, template_name="topic_form.html")


def topic_delete(request):
    view = TopicView()
    return view.delete(request)


def topic_list(request):
    keyword=request.GET.get('query', None)
    if str_util.empty(keyword):
        topics = Topic.all()
    else:
        topics = Topic.searchIndex.search(keyword)
    post_path = '/sns/topic/list/?paginate_by=20'
    params = {'post_path':post_path}
    return object_list( request, 
                        topics,
                        paginate_by=20,
                        extra_context = params,
                        template_name='sns/topic/topic_list.html'
                       )

    
def topic_ext_export(request):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=topic.csv'
    writer = csv.writer(response)
    writer.writerow(['Action', 'Name', 'Key', 'FB Page Topic', 'Parent Topics','Related Topics','Description','Image'])
    topics = Topic.all().fetch(limit=1000)
    for topic in topics:
        try:
            name = topic.name
            key_name = topic.keyNameStrip()
            parents = []
            for p in topic.parentTopics:
                parents.append(p)
            parentInfo = ';'.join(parents)
            relates = []
            for p in topic.relatedTopics:
                relates.append(p)
            relateInfo = ';'.join(relates)
            descprition = topic.description
            image = topic.image
            fbTopic = topic.fbTopic
            action = 'Update'
            writer.writerow([action, name, key_name, fbTopic, parentInfo, relateInfo, descprition,image])
        except Exception,ex:
            logging.error('Error when write topic %s'%str(ex))
    return response


def topic_upload_validate(request):
    if context.is_frontend():
        return HttpResponse(common_const.BACKEND_REQUIRED_MSG)
    if request.method == 'POST':
        data = StringIO.StringIO(request.FILES['file'].read())
        return HttpResponse(topic_api.topic_validate(data))
    else:
        form = TopicUploadForm()
        return render_to_response('sns/topic/topic_upload_validate.html', {'form':form, 'view':ContentControllerView(), 'title':'Validate CSV File'}, context_instance=RequestContext(request,{"path":request.path}))

    
def topic_upload(request):
    if context.is_frontend():
        return HttpResponse(common_const.BACKEND_REQUIRED_MSG)
    if request.method == 'POST':
        data = StringIO.StringIO(request.FILES['file'].read())
        return HttpResponse(deferred.defer(topic_api.topic_import, data))
    else:
        form = TopicUploadForm()
        return render_to_response('sns/topic/topic_upload.html', {'form':form, 'view':ContentControllerView(), 'title':'Import From CSV File'}, context_instance=RequestContext(request,{"path":request.path}))
    

def topic_level_export(request):
    if context.is_frontend():
        return HttpResponse(common_const.BACKEND_REQUIRED_MSG)
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=TopicsLevel1n2.csv'
    writer = csv.writer(response)

    """ Fetch all topics to memory. """ 
    topicMap = {}
    offset = 0
    while True :
        topicsMore = Topic.all().fetch(limit=1000, offset=offset)
        if len(topicsMore)==0 :
            break
        for topic in topicsMore :
            topicMap[topic.keyNameStrip()] = topic 
        offset += 1000

    """ Get all level 1 topics. """ 
    topicL1KeyList = list(topic_api.PSEUDO_LEVEL_1_TOPICS)
    for topicKey in topicMap.keys() :
        topic = topicMap[topicKey]
        if len(topic.parentTopics)==0 :
            topicL1KeyList.append(topicKey)
    topicL1KeyList = list(set(topicL1KeyList))        
    topicL1KeyList.sort()

    """ Get all level 2 topics for all level 1 topics. """ 
    topicL2KeyMap = {}
    for topicL1Key in topicL1KeyList :
        topicL2KeyMap[topicL1Key] = []
    for topicKey in topicMap.keys() :
        topic = topicMap[topicKey]
        for parentTopicKey in topic.parentTopics :
            if topicL2KeyMap.has_key(parentTopicKey) :
                topicL2KeyMap[parentTopicKey].append(topicKey)
    maxL2Count = 0
    for topicL1Key in topicL1KeyList :
        topicL2KeyList = topicL2KeyMap[topicL1Key]
        topicL2KeyList.sort()
        if len(topicL2KeyList)>maxL2Count :
            maxL2Count = len(topicL2KeyList)

    """ Write to file. Each level 1 topic takes one line. """
    writer.writerow([str_util.encode_utf8_if_ok(topicMap[topicKey].name) for topicKey in topicL1KeyList])
    for index in range(0, maxL2Count) :
        line = []
        for topicL1Key in topicL1KeyList :
            topicL2KeyList = topicL2KeyMap[topicL1Key]
            if len(topicL2KeyList)>index :
                line.append(str_util.encode_utf8_if_ok(topicMap[topicL2KeyList[index]].name))
            else :
                line.append('')
        writer.writerow(line)
        
    logging.info("Export file succeeded for all level 1/2 topics.")
    return response
            

def topic_export(request):
    response = view_util.get_csv_response_base("SNS Analytics News Channels")
    writer = csv.writer(response)
    topic_header = ['Topic', 'Topic Key', 'Parent 1', 'Parent 2', 'Parent 3', 'Parent 4', 'Trove Score', 'Gnews Score', ]
    channel_header = ['Twitter ID', 'Handle', 'Created At', 'State',
                     'User ID', 'User Email', 'Cohort', 'Feed Source', 'FE', 
                     'Followers', 'Clicks - 30D', 'Posts - 30D', 
                     'Notes', ]
    writer.writerow(topic_header + channel_header)
    topic_key_unknown = 'unknown_topic'
    no_channel_row = [None] * len(channel_header)
    all_topics_map = topic_api.TopicCacheMgr.get_or_build_all_topic_map()
    try:
        cmp_users = User.all().filter('isContent', True).fetch(limit=1000)
        cmp_users_map = dict([(user.uid, user) for user in cmp_users])
        limit = 100
        cursor = None
        count = 0
        rows_map = {}
        query = CmpTwitterAcctStats.all()
        while True:
            if cursor: query.with_cursor(cursor)
            stats_list = query.fetch(limit=limit)
            count += len(stats_list)
            for stats in stats_list:
                stats_info = [stats.latelyFollower, stats.totalClick, stats.totalPost]
                uid = stats.uid
                user = cmp_users_map.get(uid, None)
                if user:
                    user_info = [user.uid, user.mail, user.name, user.tags, stats.server]
                else:
                    user_info = [None, None, None, None, None]
                topic_key = stats.first_topic_key()
                if not topic_key: topic_key = topic_key_unknown
                channel_info = [int(stats.key().name()), stats.name, stats.acctCreatedTime, stats.chanState]
                row_data = channel_info + user_info + stats_info
                rows = rows_map.get(topic_key, [])
                rows.append(row_data)
                rows_map[topic_key] = rows
            cursor = query.cursor()
            logging.debug("Queried total %d CMP acct stats. Current cursor is %s." % (count, cursor))
            if not stats_list: break
        for topic_key, topic in all_topics_map.items():
            export_topic_key = 'Default' if topic_key == str_util.name_2_key(topic.name) else topic_key
            row_data = [topic.name, export_topic_key]
            for parentKey in topic.parentTopics:
                parent = Topic.get_by_topic_key(parentKey)
                row_data.append(parent.name)
            while len(row_data)<6:
                row_data.append('None')
            topicscorefb = TopicScoreFeedBuilder.get_by_key_name_strip(topic_key)
            if topicscorefb:
                row_data.extend([int(topicscorefb.trovescore), int(topicscorefb.gnewsscore)])
            else:
                row_data.extend([None, None])
            channel_rows = rows_map.pop(topic_key, [no_channel_row])
            notes = 'Duplicated topic' if len(channel_rows) > 1 else None
            for channel_row in channel_rows:
                writer.writerow(row_data + channel_row + [notes])
        for topic_key, no_topic_rows in rows_map.items():
            for no_topic_row in no_topic_rows:
                writer.writerow([None, topic_key, None, None, None, None, None, None] + no_topic_row + ['Unknown topic'])
    except Exception, ex:
        return HttpResponse("Unexpected error when exporting: %s" % str(ex), status=500)
    finally:
        logging.info("Completed exporting %d topics and %d channel records." % (len(all_topics_map), count))
    return response


def topic_cache_refresh(request):
    if context.is_frontend():
        return HttpResponse(common_const.BACKEND_REQUIRED_MSG)
    topic_api.TopicCacheMgr.deferred_build_all_cache(force=True)
    return HttpResponse("Topic cache refresh launched. It should finish within 1-2 minutes.")
        
        
