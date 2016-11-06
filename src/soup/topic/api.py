from sns.serverutils import memcache
from soup import consts as soup_const
from sns.cont import consts as cont_const
from sns.cont.models import Topic

def get_topic_name_by_key(key):
    topic = Topic.get_by_topic_key(key)
    if topic is not None:
        return topic.name
    else:
        return None
    
def get_custom_topics(topicKey):
    memKey = 'trending:' + topicKey
    customs = memcache.get(memKey)
    if customs is None :
        if topicKey == Topic.TOPIC_KEY_FRONTPAGE:
            topics = Topic.all().order('-c24h').fetch(limit=50)
            all_parents = []
            for topic in topics:
                if len(topic.parentTopics) >0:
                    for parent in topic.parentTopics:
                        if not parent in all_parents:
                            all_parents.append(parent)
            all_topics = []
            for topic in topics:
                if topic.keyNameStrip() not in all_parents and topic.name not in soup_const.MAIN_TOPIC_NAMES:
                    all_topics.append(topic)
        else:
            current = Topic.get_by_topic_key(topicKey)
            if current is None:
                return []
            if current.name not in soup_const.MAIN_TOPIC_NAMES:
                all_topics = [current]
            else:
                all_topics = []
            relates = current.relatedTopics
            for key in relates:
                all_topics.append(Topic.get_by_topic_key(key))
            sons = Topic.all().filter('parentTopics', topicKey).fetch(limit=50)
            for topic in sons:
                all_topics.append(topic)
            if current.type == cont_const.TOPIC_TAG_CITY:
                cities = Topic.all().filter('parentTopics', current.parentTopics[0]).fetch(limit=120)
                for city in cities:
                    if city != current:
                        all_topics.append(city)
            all_topics.sort(lambda x,y: cmp(x.c24h, y.c24h),reverse=True)
        customs =  all_topics[:10]
        memcache.set(memKey, customs, time = 3600)
    return customs
