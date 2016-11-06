import logging
import csv
from common.utils import string as str_util
from common.utils import url as url_util
from common.content.trove import consts as trove_const


DOMAIN_MAP = {}
SNS_BLACKLIST = []
SNS_BLACKLIST_YES = 'Yes'

def read_domains(dfile):
    line_number = 0
    reader = csv.reader(open(dfile, 'r'))
    is_header = True
    for row in reader:
        line_number += 1
        if is_header:
            is_header = False
            continue
        domain = str_util.lower_strip(row[0])
        if not domain:
            logging.error("Empty domain at line #%d!" % line_number)
            return False
        if not domain.startswith('cs_') and not url_util.is_valid_domain(domain):
            logging.error("Invalid domain %s at line #%d!" % (domain, line_number))
            return False
        sns_blacklisted = str_util.strip(row[4])
        if sns_blacklisted:
            if sns_blacklisted == SNS_BLACKLIST_YES:
                SNS_BLACKLIST.append(domain)
            else:
                logging.error("Invalid blacklist status %s at line #%d!" % (sns_blacklisted, line_number))
                return False
        visor_status = str_util.strip(row[5])
        if not visor_status: visor_status = trove_const.VISOR_NA
        if visor_status not in trove_const.VISOR_STATES:
            logging.error("Invalid visor status %s at line #%d!" % (visor_status, line_number))
            return False
        v_domains = DOMAIN_MAP.get(visor_status, [])
        v_domains.append(domain)
        DOMAIN_MAP[visor_status] = v_domains
    return True
        

def print_results():
    print "SNS_BLACKLIST = ["
    print _list_2_string(SNS_BLACKLIST)
    print ']'
    print ''
    print "VISOR_UNFRIENDLY_LIST = ["
    print _list_2_string(DOMAIN_MAP.get(trove_const.VISOR_FRAME_KILLER)
                    + DOMAIN_MAP.get(trove_const.VISOR_PAGE_KILLER)
                    + DOMAIN_MAP.get(trove_const.VISOR_BAD)
                    + DOMAIN_MAP.get(trove_const.VISOR_AWFUL)
                         )
    print ']'
    print ''
    print "VISOR_PHONE_UNFRIENDLY_LIST = ["
    print _list_2_string(DOMAIN_MAP.get(trove_const.VISOR_PHONE_KILLER))
    print ']'
    print ''
    print "VISOR_IPHONE_UNFRIENDLY_LIST = ["
    print _list_2_string(DOMAIN_MAP.get(trove_const.VISOR_IPHONE_UNFRIENDLY))
    print ']'
    print ''
    print "VISOR_FRIENDLY_LIST = ["
    print _list_2_string(DOMAIN_MAP.get(trove_const.VISOR_GREAT)
                    + DOMAIN_MAP.get(trove_const.VISOR_GOOD)
                    + DOMAIN_MAP.get(trove_const.VISOR_OK)
                         )
    print ']'
    print ''


def _list_2_string(l):
    return ', '.join(["'%s'" % item for item in l])
    
    
def execute(args):
    if read_domains(args.dfile):
        print_results()
    

def add_subparser(parsers): 
    parser = parsers.add_parser('domainqualifier', description="Qualify domains", help='qualify domains')
    parser.add_argument('--dfile', required=True, help='domains file name')
    parser.set_defaults(func=execute)


