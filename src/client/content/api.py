from sns.api import consts as api_const
from sns.cont import consts as cont_const
from client import apiclient
from client.base.api import ApiBase


class TopicApi(ApiBase):
    API_MODULE = api_const.API_M_TOPIC
        

class TopicCacheMgr:
    topic_map = {}

    @classmethod
    def clear(cls):
        cls.topic_map = {}
    
    @classmethod
    def load(cls):
        cls.topic_map = {}
        topics = TopicApi().query_all()
        for topic in topics:
            topic_key = TopicApi(topic).key_name
            cls.topic_map[topic_key] = topic

    @classmethod
    def get_topic_by_key(cls, topic_key):
        return cls.topic_map.get(topic_key, None) 
    

class RawContentApi(ApiBase):
    API_MODULE = api_const.API_M_RAW_CONTENT
    
    @classmethod
    def test_obj(cls):
        return {
            "cskey": cont_const.CS_HARK, 
            "contents": "Dummy",
            }


if __name__ == "__main__":
    apiclient.login_as_admin()
    TopicApi().query_all(params=dict(keys_only=True))
    RawContentApi().query_all()
    

    
    
