import csv
import logging

from client.acctmgmt import consts as acctmgmt_client_const


def attr_info(row):
    attrInfo = []
    for i, header in enumerate(row):
        if acctmgmt_client_const.HEADER_2_ATTR_MAP.has_key(header):
            attrInfo.append(acctmgmt_client_const.HEADER_2_ATTR_MAP[header])
        else:
            logging.error("Wrong column header: %s" % header)
            attrInfo.append(None)
    return attrInfo
    

def read(filepath):
    r"""
    read a csv file and return a list of records
    """    
    accountReader = csv.reader(open(filepath, 'rbU'))
    is_header = True
    records = []
    attrInfo = []
    for row in accountReader:
        if is_header:
            is_header = False
            attrInfo = attr_info(row) 
            continue
        record = {}
        rowInvalid = False
        for i, v in enumerate(row):
            if i>=len(attrInfo):
                logging.error("Row has more columns than header: %s" % row)
                rowInvalid = True
                break
            if attrInfo[i] is None:
                continue
            record[attrInfo[i]] = v 
        if rowInvalid:
            continue
        records.append(record)
    return records


def write(records, filepath, delimiter):
    r"""
    write records into a csv file
    """
    print delimiter.join(acctmgmt_client_const.DEFAULT_HEADERS)
    for record in records:
        r = []
        for header in acctmgmt_client_const.DEFAULT_HEADERS:
            attr = acctmgmt_client_const.HEADER_2_ATTR_MAP[header]
            r.append(unicode(record.get(attr)).encode('utf-8'))
        print delimiter.join(r)
        
