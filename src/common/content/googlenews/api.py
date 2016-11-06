from common.utils import string as str_util


class SearchKeywordsHandler:
    def __init__(self, topic_name, custom_keywords=None):
        self.topic_name = topic_name
        self.keywords = custom_keywords
        if self.keywords: return
        tokens = self.parse_parentheses(topic_name)
        self.keywords = ' '.join([self.double_quote(token) for token in tokens])
    
    @classmethod    
    def parse_parentheses(cls, words):
        """ Assuming there is at most one pair of parentheses. """
        if not words: return []
        tokens = words.split('(')
        if len(tokens) > 2:
            raise Exception("Invalid search keywords! %s" % words)
        elif len(tokens) == 2:
            right_parenthesis_index = tokens[1].find(')')
            if right_parenthesis_index == -1:
                raise Exception("Invalid search keywords! %s" % words)
            tokens[1] = tokens[1][:right_parenthesis_index]
        return [str_util.strip(token) for token in tokens]

    @classmethod
    def double_quote(cls, keywords):
        keywords = str_util.strip(keywords)
        words = keywords.split(' ')
        if len(words) == 1:
            return words[0]
        else:
            return '"%s"' % keywords

