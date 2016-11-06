#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
IP to location translation
"""

import os
#import logging
import socket
import urllib2
import re

from google.appengine.api.urlfetch import fetch as urlfetch

LOCALHOST_IP = "127.0.0.1"
COMMON_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PROJECT_DIR = os.path.dirname(COMMON_DIR)
QQWRY_ABS_PATH = PROJECT_DIR+'/ip/qqwry/QQWry.Dat'

_THE_IP_LOCATOR = None
def getIPLocator():
    global _THE_IP_LOCATOR
    if _THE_IP_LOCATOR is None :
        from ip.api import IPLocator
        _THE_IP_LOCATOR = IPLocator(QQWRY_ABS_PATH) 
    return _THE_IP_LOCATOR

"""
CN_LOCATION=("中国","北京","上海","天津","重庆","河北","河南","湖北","湖南","江苏","江西","辽宁","吉林","黑龙江","陕西","山西","山东",
          "四川","青海","安徽","海南","广东","贵州","浙江","福建","台湾","甘肃","云南","西藏","宁夏","广西","新疆","内蒙古","香港","澳门")
"""

UNKNOWN_COUNTRY_CHINESE_CODES = ["IANA","APNIC","BITS","欧洲","联合国","北美","AsiaNetcom","Concert","Firebrand","Heartlandis","Intelsat","Microsoft","雅虎","奇虎qihoo蜘蛛","Teleglobe","Yahoo","Sprint","Equinix","非公网地址",]
COUNTRY_CHINESE_CODE_CN = "中国"
COUNTRY_CHINESE_CODE_US = "美国"
COUNTRY_CODE_CN = "CN"
COUNTRY_CODE_US = "US"
COUNTRY_CODE_UNKNOWN = "XX"
COUNTRY_NAME_UNKNOWN = "Unknown Countries"
COUNTRY_NAME_OTHERS = "Other Countries"
COUNTRY_INFO = {"中国":("CN","CHN","156","China"),"台湾":("TW","TWN","158","Taiwan"),"香港":("HK","HKG","344","Hong Kong"),"澳门":("MO","MAC","446","Macao"),
                 "蒙古":("MN","MNG","496","Mongolia"),"朝鲜":("KP","PRK","408","North Korea"),"韩国":("KR","KOR","410","Korea"),
                 "日本":("JP","JPN","392","Japan"),"菲律宾":("PH","PHL","608","Philippines"),"越南":("VN","VNM","704","Vietnam "),
                 "老挝":("LA","LAO","418","Laos"),"柬埔寨":("KH","KHM","116","Cambodia"),"缅甸":("MM","MMR","104","Myanmar"),
                 "泰国":("TH","THA","764","Thailand"),"马来西亚":("MY","MYS","458","Malaysia"),"文莱":("BN","BRN","096","Brunei Darussalam"),
                 "新加坡":("SG","SGP","702","Singapore"),"印度尼西亚":("ID","IDN","360","Indonesia"),"东帝汶":("TL","TLS","626","Timor-Leste"),
                 "尼泊尔":("NP","NPL","524","Nepal"),"不丹":("BT","BTN","064","Bhutan"),"孟加拉国":("BD","BGD","050","Bangladesh"),
                 "印度":("IN","IND","356","India"),"巴基斯坦":("PK","PAK","586","Pakistan"),"斯里兰卡":("LK","LKA","144","Sri Lanka"),
                 "马尔代夫":("MV","MDV","462","Maldives"),"哈萨克斯坦":("KZ","KAZ","398","Kazakhstan"),"吉尔吉斯斯坦":("KG","KGZ","417","Kyrgyzstan"),                 
                 "塔吉克斯坦":("TJ","TJK","762","Tajikistan"),"乌兹别克斯坦":("UZ","UZB","860","Uzbekistan"),"土库曼斯坦":("TM","TKM","795","Turkmenistan"),
                 "阿富汗":("AF","AFG","004","Afghanistan"),"伊拉克":("IQ","IRQ","368","Iraq"),"伊朗":("IR","IRN","364","Iran"),
                 "叙利亚":("SY","SYR","760","Syria"),"约旦":("JO","JOR","400","Jordan"),"黎巴嫩":("LB","LBN","422","Lebanon"),
                 "以色列":("IL","ISR","376","Israel"),"巴勒斯坦":("PS","PSE","275","Palestine"),"沙特阿拉伯":("SA","SAU","682","Saudi Arabia"),                 
                 "巴林":("BH","BHR","048","Bahrain"),"卡塔尔":("QA","QAT","634","Qatar"),"科威特":("KW","KWT","414","Kuwait"),
                 "阿联酋":("AE","ARE","784","United Arab Emirates"),"阿拉伯联合酋长国":("AE","ARE","784","United Arab Emirates"),"阿曼":("OM","OMN","512","Oman"),
                 "也门":("YE","YEM","887","Yemen"),"格鲁吉亚":("GE","GEO","268","Georgia"),"亚美尼亚":("AM","ARM","051","Armenia"),
                 "阿塞拜疆":("AZ","AZE","031","Azerbaijan"),"土耳其":("TR","TUR","792","Turkey"),"塞浦路斯":("CY","CYP","196","Cyprus"),
                 "瑞典":("SE","SWE","752","Sweden"),"芬兰":("FI","FIN","246","Finland"),"挪威":("NO","NOR","578","Norway"),
                 "冰岛":("IS","ISL","352","Iceland"),"丹麦":("DK","DNK","208","Denmark"),"法罗群岛":("FO","FRO","234","Faroe Islands"),
                 "爱沙尼亚":("EE","EST","233","Estonia"),"拉脱维亚":("LV","LVA","428","Latvia"),"立陶宛":("LT","LTU","440","Lithuania"),
                 "白俄罗斯":("BY","BLR","112","Belarus"),"俄罗斯":("RU","RUS","643","Russia"),"乌克兰":("UA","UKR","804","Ukraine"),
                 "摩尔多瓦":("MD","MDA","498","Moldova"),"波兰":("PL","POL","616","Poland"),"捷克":("CZ","CZE","203","Czech Republic"),
                 "斯洛伐克":("SK","SVK","703","Slovakia"),"匈牙利":("HU","HUN","348","Hungary"),"德国":("DE","DEU","276","Germany"),
                 "奥地利":("AU","AUS","036","Austria"),"瑞士":("CH","CHE","756","Switzerland"),"列支敦士登":("LI","LIE","438","Liechtenstein"),
                 "英国":("UK","GBR","826","United Kingdom"),"爱尔兰":("IE","IRL","372","Ireland"),"荷兰":("NL","NLD","528","Netherlands"),
                 "比利时":("BE","BEL","056","Belgium"),"卢森堡":("LU","LUX","442","Luxembourg"),"法国":("FR","FRA","250","France"),                 
                 "摩纳哥":("MC","MCO","492","Monaco"),"罗马尼亚":("RO","ROU","642","Romania"),"保加利亚":("BG","BGR","100","Bulgaria"),
                 "塞尔维亚":("RS","SRB","688","Serbia"),"马其顿":("MK","MKD","807","Macedonia"),"阿尔巴尼亚":("AL","ALB","008","Albania"),
                 "希腊":("GR","GRC","300","Greece"),"斯洛文尼亚":("SI","SVN","705"," Slovenia"),"克罗地亚":("HR","HRV","191","Croatia"),
                 "波斯尼亚和墨塞哥维那":("BA","BIH","070","Bosnia and Herzegovina"),"意大利":("IT","ITA","380","Italy"),"梵蒂冈":("VA","VAT","336","Vatican"),
                 "圣马力诺":("SM","SMR","674","San Marino"),"马耳他":("MT","MLT","470","Malta"),"西班牙":("ES","ESP","724","Spain"),
                 "葡萄牙":("PT","PRT","620","Portugal"),"安道尔":("AD","AND","020","Andorra"),"埃及":("EG","EGY","818","Egypt"),
                 "利比亚":("LY","LBY","434","Libya"),"苏丹":("SD","SDN","736","Sudan"),"突尼斯":("TN","TUN","788","Tunisia"),                 
                 "阿尔及利亚":("DZ","DZA","012","Algeria"),"摩洛哥":("MA","MAR","504","Morocco"),"亚速尔群岛":("XX","XXX","0",COUNTRY_NAME_UNKNOWN),
                 "马德拉群岛":("XX","XXX","0","Unknown Country"),"埃塞俄比亚":("ET","ETH","231","Ethiopia"),"厄立特里亚":("ER","ERI","232","Eritrea"),
                 "索马里":("SO","SOM","706","Somalia"),"吉布提":("DJ","DJI","262","Djibouti"),"肯尼亚":("KE","KEN","404","Kenya"),
                 "坦桑尼亚":("TZ","TZA","834","Tanzania"),"乌干达":("UG","UGA","800","Uganda"),"卢旺达":("RW","RWA","646","Rwanda"),
                 "布隆迪":("BI","BDI","108","Burundi"),"塞舌尔":("SC","SYC","690","Seychelles"),"乍得":("TD","TCD","148","Chad"),
                 "中非":("CF","CAF","140","Central African Republic"),"喀麦隆":("CM","CMR","120","Cameroon"),"赤道几内亚":("GQ","GNQ","226","Equatorial Guinea"),
                 "加蓬":("GA","GAB","266","Gabon"),"刚果":("CG","COG","178","Congo"),"刚果民主共和国":("CD","COD","180","Congo, the Democratic Republic of"),
                 "圣多美和普林西比":("ST","STP","678","Sao Tome and Principe"),"毛里塔尼亚":("MR","MRT","478","Mauritania"),"塞内加尔":("SN","SEN","686","Senegal"),
                 "冈比亚":("GM","GMB","270","Gambia"),"马里":("ML","MLI","466","Mali"),"布基纳法索":("BF","BFA","854","Burkina Faso"),          
                 "几内亚":("GN","GIN","324","Guinea"),"几内亚比绍":("GW","GNB","624","Guinea-Bissau"),"佛得角":("CV","CPV","132"," Cape Verde"),
                 "塞拉利昂":("SL","SLE","694","Sierra Leone"),"利比里亚":("LR","LBR","430","Liberia"),"科特迪瓦":("CI","CIV","384","Côte d'Ivoire"),                
                 "加纳":("GH","GHA","288","Ghana"),"多哥":("TG","TGO","768","Togo"),"贝宁":("BJ","BEN","204","Benin"),
                 "尼日尔":("NE","NER","562","Niger"),"加那利群岛":("XX","XXX","0","Unknown Country"),"赞比亚":("ZM","ZMB","894","Zambia"),
                 "安哥拉":("AO","AGO","024","Angola"),"津巴布韦":("ZW","ZWE","716","Zimbabwe"),"马拉维":("MW","MWI","454","Malawi"),
                 "莫桑比克":("MZ","MOZ","508","Mozambique"),"博茨瓦纳":("BW","BWA","072","Botswana"),"纳米比亚":("NA","NAM","516","Namibia"),
                 "南非":("ZA","ZAF","710","South Africa"),"斯威士兰":("SZ","SWZ","748","Swaziland"),"莱索托":("LS","LSO","426"," Lesotho"),
                 "马达加斯加":("MG","MDG","450","Madagascar"),"科摩罗":("KM","COM","174","Comoros"),"毛里求斯":("MU","MUS","480","Mauritius"),
                 "澳大利亚":("AU","AUS","036","Australia"),"新西兰":("NZ","NZL","554","New Zealand"),"巴布亚新几内亚":("PG","PNG","598","Papua New Guinea"),
                 "所罗门群岛":("SB","SLB","090","Solomon Islands"),"瓦努阿图":("VU","VUT","548","Vanuatu"),"密克罗尼西亚":("FM","FSM","583","Micronesia, Federated States of"),                
                 "马绍尔群岛":("MH","MHL","584","Marshall Islands"),"帕劳":("PW","PLW","585","Palau"),"瑙鲁":("NR","NRU","520","Nauru"),
                 "基里巴斯":("KI","KIR","296","Kiribati"),"图瓦卢":("TV","TUV","798","Tuvalu"),"萨摩亚":("WS","WSM","882","Samoa"),
                 "斐济群岛":("FJ","FJI","242","Fiji"),"汤加":("TO","TON","776","Tonga"),"关岛":("GU","GUM","316","Guam"),
                 "新喀里多尼亚":("NC","NCL","540","New Caledonia"),"法属波利尼西亚":("PF","PYF","258","French Polynesia"),"皮特凯恩岛":("PN","PCN","612","Pitcairn"),
                 "瓦利斯":("XX","XXX","0","Unknown Country"),"纽埃":("NU","NIU","570","Niue"),"托克劳":("TK","TKL","772","Tokelau"),
                 "美属萨摩亚":("AS","ASM","016","American Samoa"),"北马里亚纳":("MP","MNP","580","Northern Mariana Islands"),"加拿大":("CA","CAN","124","Canada"),
                 "美国":("US","USA","840","United States"),"墨西哥":("MX","MEX","484","Mexico"),"格陵兰":("GL","GRL","304","Greenland"),
                 "危地马拉":("GT","GTM","320","Guatemala"),"伯利兹":("BZ","BLZ","084","Belize"),"萨尔瓦多":("SV","SLV","222","El Salvador"),
                 "洪都拉斯":("HN","HND","340","Honduras"),"尼加拉瓜":("NI","NIC","558","Nicaragua"),"哥斯达黎加":("CR","CRI","188","Costa Rica"),                 
                 "巴拿马":("PA","PAN","591","Panama"),"巴哈马":("BS","BHS","044","Bahamas"),"古巴":("CU","CUB","192","Cuba"),
                 "牙买加":("JM","JAM","388","Jamaica"),"海地":("HT","HTI","332","Haiti"),"多米尼加":("DO","DOM","214","Dominican Republic"),
                 "安提瓜":("AG","ATG","028","Antigua and Barbuda"),"多米尼克":("DM","DMA","212","Dominica"),"圣卢西亚":("LC","LCA","662","Saint Lucia"),
                 "巴巴多斯":("BB","BRB","052","Barbados"),"特立尼达和多巴哥":("TT","TTO","780","Trinidad and Tobago"),"波多黎各":("PR","PRI","630","Puerto Rico"),
                 "安圭拉":("AO","AGO","024","Angola"),"瓜德罗普":("GP","GLP","312","Guadeloupe"),"马提尼克":("MQ","MTQ","474","Martinique"),
                 "阿鲁巴":("AW","ABW","533","Aruba"),"特克斯和凯科斯群岛":("TC","TCA","796","Turks and Caicos Islands"),"开曼群岛":("KY","CYM","136","Cayman Islands"),
                 "百慕大":("BM","BMU","060","Bermuda"),"哥伦比亚":("CO","COL","170","Colombia"),"委内瑞拉":("VE","VEN","862","Venezuela, Bolivarian Republic of"),
                 "圭亚那":("GF","GUF","254","French Guiana"),"苏里南":("SR","SUR","740","Suriname"),"厄瓜多尔":("EC","ECU","218","Ecuador"),
                 "秘鲁":("PE","PER","604","Peru"),"玻利维亚":("BO","BOL","068","Bolivia, Plurinational State of"),"巴西":("BR","BRA","076","Brazil"),
                 "智利":("CL","CHL","152","Chile"),"阿根廷":("AR","ARG","032","Argentina"),"乌拉圭":("UY","URY","858","Uruguay"),
                 "巴拉圭":("PY","PRY","600","Paraguay"),}

_COUNTRY_INFO_ENGLISH = None
def get_country_info_english():
    global _COUNTRY_INFO_ENGLISH
    if _COUNTRY_INFO_ENGLISH is None :
        _COUNTRY_INFO_ENGLISH = {}
        for key, country_info in COUNTRY_INFO.items() :
            _COUNTRY_INFO_ENGLISH[country_info[0]] = country_info 
    return _COUNTRY_INFO_ENGLISH

def isValidCountryCode(country_code):
    return country_code is not None and get_country_info_english().has_key(country_code.upper())
    
def get_country_name(country_code):
    if country_code is None:
        return COUNTRY_NAME_UNKNOWN 
    country_info_english = get_country_info_english()
    country_code_upper = country_code.upper()
    if country_info_english.has_key(country_code_upper) :
        return country_info_english[country_code_upper][3]
    else :
        return COUNTRY_NAME_UNKNOWN 

def get_tld_bydns(ipaddress):
    r"""
    get top layer domain name by dnslookup, None if no match
    """
    
    try:
        host=socket.gethostbyaddr(ipaddress)[0]
        return host.split(".")[-1]
    except:
        """
        when dnslookup cannot find it, nothing we can do
        """
        return None

def get_location_by_qqlib(ipaddress):
    try:
        if ipaddress==LOCALHOST_IP :
            return "Localhost"
        ipLocator = getIPLocator()
        location = ipLocator.getIpAddr(ipLocator.str2ip(ipaddress))
        return location
    except Exception, ex:
        return "Exception: %s" % str(ex)
 
def matchUnknownCountryChineseCode(countryChineseCode):
    """
    It is likely there is a bug in the IP lib. Shouldn't there be a white space after 'IANA' in 'IANA美洲及南部非洲IP分布'?
    """ 
    for unknownCountryChineseCode in UNKNOWN_COUNTRY_CHINESE_CODES :
        if countryChineseCode.find(unknownCountryChineseCode)==0 :
            return True
    return False 
        
def get_country_info_by_qqlib(ipaddress,treatLocalhostIPAsCN=True):
    r"""
    Get country info by QQ IP lib.
    Return format sample ("CN", "CHN", 156, "China", "中国 上海交通大学"), ("XX", "XXX", -1, "Unknown Country", "Whatever...")
    """
    try:        
        if LOCALHOST_IP==ipaddress :
            location = "Localhost"
            if treatLocalhostIPAsCN :
                countryChineseCode = COUNTRY_CHINESE_CODE_CN
            else :
                countryChineseCode = COUNTRY_CHINESE_CODE_US
        else :
            if ipaddress.startswith('99.'):
                return (get_country_by_hostip(ipaddress), "XXX", -1, "Unknown Country", "Unknown Location")
            ipProcessor = getIPLocator()
            location = ipProcessor.getIpAddr(ipProcessor.str2ip(ipaddress))
            countryChineseCode = location.split(" ")[0]
            countryChineseCode = countryChineseCode.split("/")[0]
        if not COUNTRY_INFO.has_key(countryChineseCode) and matchUnknownCountryChineseCode(countryChineseCode):
            return (COUNTRY_CODE_UNKNOWN, "XXX", -1, "Unknown Country", location)
        if not COUNTRY_INFO.has_key(countryChineseCode) :
            countryChineseCode = COUNTRY_CHINESE_CODE_CN
        countryInfo = COUNTRY_INFO.get(countryChineseCode)
        return (countryInfo[0], countryInfo[1], countryInfo[2], countryInfo[3], location)
    except :
        try:
            ipv6_country=get_ipv6_address_country(ipaddress)
            if ipv6_country:
                return ipv6_country
            else:
                return (COUNTRY_CODE_UNKNOWN, "XXX", -1, "Unknown Country", "Unknown Location") 
        except:        
            #logging.exception("Unexpected error when resolving country info for IP address '%s'." % ipaddress)
            return (COUNTRY_CODE_UNKNOWN, "XXX", -1, "Unknown Country", "Unknown Location")
    
def get_country_by_qqlib(ipaddress,treatLocalhostIPAsCN=True):
    r"""
    Get country by QQ IP lib.
    """
    try:
        return get_country_info_by_qqlib(ipaddress,treatLocalhostIPAsCN)[0]
    except :
        #logging.exception("Unexpected error when resolving country code for IP address '%s'." % ipaddress)
        return COUNTRY_CODE_UNKNOWN
    
def isCNUser(ipaddress, treatLocalhostIPAsCN=True):
    r"""
    Decide whether the ip address is from China or not.
    The local host "127.0.0.1" is treated by the flag param 'treatLocalhostIPAsCN'.
    """  
    return get_country_by_qqlib(ipaddress,treatLocalhostIPAsCN)==COUNTRY_CODE_CN
        
def get_random_country_code():
    r"""
    Get a random country code.
    """
    import random
    country_list = COUNTRY_INFO.keys()
    index=random.randrange(0,len(country_list))
    return COUNTRY_INFO[country_list[index]][0]

def get_ipv6_address_country(ipaddress):
    p=re.compile('^([\da-fA-F]{1,4}:){6}((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$|^::([\da-fA-F]{1,4}:){0,4}((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$|^([\da-fA-F]{1,4}:):([\da-fA-F]{1,4}:){0,3}((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$|^([\da-fA-F]{1,4}:){2}:([\da-fA-F]{1,4}:){0,2}((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$|^([\da-fA-F]{1,4}:){3}:([\da-fA-F]{1,4}:){0,1}((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$|^([\da-fA-F]{1,4}:){4}:((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$|^([\da-fA-F]{1,4}:){7}[\da-fA-F]{1,4}$|^:((:[\da-fA-F]{1,4}){1,6}|:)$|^[\da-fA-F]{1,4}:((:[\da-fA-F]{1,4}){1,5}|:)$|^([\da-fA-F]{1,4}:){2}((:[\da-fA-F]{1,4}){1,4}|:)$|^([\da-fA-F]{1,4}:){3}((:[\da-fA-F]{1,4}){1,3}|:)$|^([\da-fA-F]{1,4}:){4}((:[\da-fA-F]{1,4}){1,2}|:)$|^([\da-fA-F]{1,4}:){5}:([\da-fA-F]{1,4})?$|^([\da-fA-F]{1,4}:){6}:$')  
    if p.match(ipaddress):
        return ('US', "XXX", -1, "Unknown Country", "Unknown Location")
    else:
        return (COUNTRY_CODE_UNKNOWN, "XXX", -1, "Unknown Country", "Unknown Location")

"""
Timeout is used for urlfetch based IP resolution. 
"""
TIMEOUT=10

def get_country_by_hostip(ipaddress):
    r"""
    get country by hostip.info web service, use google's urlfetch
    http://www.hostip.info/
    """
    try:
        country=urlfetch("http://api.hostip.info/country.php?ip=%s"%(ipaddress,),deadline=TIMEOUT).content
        return country
    except :
        #logging.exception("Unexpected error when resolving country code for IP address '%s'." % ipaddress)
        return COUNTRY_CODE_UNKNOWN
    
def get_country_by_hostip_urllib(ipaddress):
    r"""
    get country by hostip.info web service
    http://www.hostip.info/
    """
    try:
        country=urllib2.urlopen("http://api.hostip.info/country.php?ip=%s"%(ipaddress,)).read()
        return country
    except :
        #logging.exception("Unexpected error when resolving country code for IP address '%s'." % ipaddress)
        return COUNTRY_CODE_UNKNOWN
    
def main():
    print getIPLocator().about()
    try:
        domainIPMap = {
                     "ipv6": "2001:470:1f04:bf3::2",
                     "ipv6_illegal": "2001::25de::cade",
                     "Unknown host": "79.106.255.255",
                     "localhost" : "127.0.0.1",
                     "sjtu.edu.cn" : "202.120.0.80",
                     "att.com" : "76.254.23.119", 
                     "alanxing.att.com" : "99.169.82.200", 
                     "google.com" : "74.125.19.99", 
                     "google.de" : "216.239.59.104",
                     "xing.de" : "213.238.60.192", 
                     "www.direct.gov.uk" : "77.67.85.9", 
                     "www.bbc.co.uk" : "212.58.244.143", 
                     "news.ru" : "194.87.12.13",
                     "open.by" : "193.232.92.14",
                     "baidu.com" : "220.181.6.184",
                     "美国/加拿大" : "216.231.95.255",
                     "奥地利/德国" : "217.13.199.127",
                     }
        
        for domain, ip in domainIPMap.items() :
            tup = get_country_info_by_qqlib(ip)
            countryCodeByHostIP = get_country_by_hostip_urllib(ip)
            print "%s %s (%s) %s" % (domain, ip, countryCodeByHostIP, ("%s %s %s %s %s" % tup))

    except Exception, ex:
        print "Exception: %s" % str(ex)
        pass
 

if __name__ == "__main__" :
    main()