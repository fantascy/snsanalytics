import os
import re
from sets import Set


DB_STRING_PROTECTIVE_LENGTH = 450 

def strip(s):
    if s is not None:
        s = s.strip()
        if len(s)==0 or s.lower()=="none":
            s = None
    return s 


def empty(s):
    if strip(s) is None:
        return True
    else:
        return False


def strip_one_line(s):
    if s is None:
        return None
    return strip(s.replace('\n', ' '))


def lower(s):
    if s is not None:
        return s.lower()
    else:
        return None


def upper(s):
    if s is not None:
        return s.upper()
    else:
        return None


def lower_strip(s):
    return lower(strip(s))


def upper_strip(s):
    return upper(strip(s))


def split(s, delimiter=" "):
    """
    This function is different from standard str.split() in two aspects:
        1, it does a strip for each split token;
        2, it eliminates empty string
    """
    if s is None: return []
    l = []
    for x in s.split(delimiter):
        xs = x.strip()
        if len(xs)>0:
            l.append(xs)
    return l


def split_dedupe(s, delimiter=" "):
    """
    Split and then dedupe
    """
    l = split(s, delimiter)
    return list(Set(l))


def split_dedupe_preserve_order(s, delimiter=" "):
    """
    Split and then dedupe, with order preserved
    """
    l = split(s, delimiter)
    st = Set(l)
    ret_list = []
    for item in l:
        if item in st:
            ret_list.append(item)
            st.remove(item)
    return ret_list


def index(l, s):
    if l is None or len(l)==0:
        return None
    if l.count(s)==0:
        return 0
    else:
        return l.index(s)
    
    
def slice(value, arg):
    """
    Returns a '...' slice of input string.
    For instance,
        slice('1234567890', '0:9') returns '123456...'
        slice('1234567890', '0:10') returns '1234567890'
    No error is handled.
    """
    r = arg.split(u':')
    start = (int)(r[0]) 
    end = (int)(r[1])
    if len(value)<=(end-start):
        return value
    else:
        result=[]
        for x in range(start,end-3):
            result.append(value[x])
        result.extend('...')
        s=''.join(result)
        return s


def slice_double_byte_character_set(s, length_display, suffix=True):
    length_double=length_display/2
    length_unicode=len(s)
    if length_unicode<length_double:
        return s
    else:
        str_utf_8=s.encode('utf-8')
        length_utf_8=len(str_utf_8)
        difference=length_utf_8-length_unicode
        if difference/2+length_unicode<=length_display:
            return s
        else:
            str_current=s[:length_double]
            str_utf_8_current=str_current.encode('utf-8')
            for i in range(length_double,length_unicode):                
                length_utf_8_current=len(str_utf_8_current)
                length_unicode_current=len(str_current)
                length_display_current=(length_utf_8_current-length_unicode_current)/2+length_unicode_current
                char=s[i]
                char_utf_8=char.encode('utf-8')
                if length_display_current+1>length_display and len(char_utf_8)==1:
                    if len(str_current)<length_unicode:
                        if suffix:
                            str_current+="..."
                    return str_current
                if len(char_utf_8)!=1:
                    difference=length_display-(len(char_utf_8)*2/3+length_display_current)
                    if difference==0:
                        if len(str_current)<length_unicode:
                            if suffix:
                                str_current+="..."
                        return str_current+char
                    elif difference<0:
                        if len(str_current)<length_unicode:
                            if suffix:
                                str_current+="..."
                        return str_current
                str_current+=char
                str_utf_8_current+=char_utf_8


def decode_utf8_if_ok(s):
    try:
        return s.decode('utf-8')
    except:
        return s
    

def encode_utf8_if_ok(s):
    try:
        return s.encode('utf-8')
    except:
        return s
    

def normalize(strOrList):
    if strOrList is None:
        return None
    if isinstance(strOrList, basestring):
        return strip(strOrList.lower())
    if type(strOrList)==list:
        retList = []
        for s in strOrList:
            s = strip(s)
            if s is None:
                continue
            retList.append(s.lower())
        return retList
    return None

def normalizeTitle(title):
    l = []
    for s in title.split():
        s = s.strip().lower()
        if len(s) > 0:
            l.append(s)
    return ' '.join(l)


EMAIL_REGEX = re.compile(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")
def is_valid_email(s):
    return EMAIL_REGEX.match(s) is not None if s else False


def normalizeEmail(email):
    result = strip(email)
    if result is None:
        return None
    else:
        return result.lower()


def numberDisplay(number_string):
    display_string=''
    while True:
        if len(number_string)>3:
            display_string=','+number_string[-3:]+display_string
            number_string=number_string[:-3]
        else:
            display_string=number_string+display_string
            break
    return display_string


def is_not_key_char(char):
    ai = ord(char)
    if ai >=8 and ai<= 10:
        return True
    elif ai == 13:
        return True
    elif ai >= 32 and ai<= 47:
        return True
    elif ai >=58 and ai <= 64:
        return True
    elif ai >= 91 and ai <=96:
        return True
    elif ai >= 123 and ai <= 126:
        return True
    else:
        return False
    

def title_2_key(title):
    if strip(title) is None:
        return None
    key = []
    for c in title.lower()[:256]:
        if is_not_key_char(c):
            key.append('_')
        else:
            key.append(c)
    key = ''.join(key)
    while key.find('__')!= -1:
        key = key.replace('__', '_')    
    return key.strip('_').rstrip('_')


def name_2_key(name):
    if strip(name) is None:
        return None
    key = []
    for c in name.lower()[:256]:
        if is_not_key_char(c):
            pass
        else:
            key.append(c)
    return ''.join(key)


def str_2_boolean(s):
    s = lower_strip(s)
    return s in ('true', 'yes')


def split_strip(data, separator=',', lowercase=False):
    r = []
    if data is None:
        return r 
    infos = data.split(separator)
    for info in infos:
        info = info.strip()
        if info:
            r.append(info.lower() if lowercase else info)
    return r
    

def nameNormalize(name):
    while name.find('__')!= -1:
        name = name.replace('__', '_') 
    return name.strip().lower()


def int_list_2_list_str(int_list):
    str_list = [str(item) for item in int_list]
    return "[%s]" % ','.join(str_list)


def int_list_2_set_str(int_list):
    int_list = list(set(int_list))
    str_list = [str(item) for item in int_list]
    return "set([%s])" % ','.join(str_list)


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def match_main_file_path(name):
    try:
        import __main__
        path = __main__.__file__
        while True:
            path, tail = os.path.split(path)
            if tail == name:
                return True
            if not tail:
                break
        return False
    except:
        return False
    

if __name__ == '__main__':
    emails = ['alan@snsanalytics.com',
              'Abc+def.efg-1@Abcdef-1.efg',
              'Abc+def.efg-1@abcdef-1.efg',
              'Abc@+def.efg-1@abcdef.efg',
              'abc@def+h.com',
              None,
              '',
              'abc',
              'def@',
              ]
    for email in emails:
        print email, is_valid_email(email)
        

     
    