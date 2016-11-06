import getopt
import sys

from client import apiclient
from client.acctmgmt.api import AcctMgmtApi
from client.acctmgmt import csvhandler


def usage():
    r"""
    usage information
    """

    usage=r"""
    NAME
        google2csv.py [-d delimiter] 
        
    SYNOPSIS
        dump.py
        
    DESCRIPTION
        Download google data store into a csv file

        """
    print usage
    

def dump(delimiter):
    db = AcctMgmtApi()
    records = db.query_all()
    csvhandler.write(records, sys.stdout, ",")
    
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:H")
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    delimiter = ","
    for o, a in opts:
        if o == "-d":
            delimiter = a
        elif o == "-H":
            usage()
            sys.exit()
    apiclient.login_as_admin()
    dump(delimiter)
        
