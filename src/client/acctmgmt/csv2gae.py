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
        csv2google.py
        
    SYNOPSIS
        csv2google.py  FILE
        
    DESCRIPTION
        load cvs file into google app engine
        

        FILE
           input file, csv file with yahoo account and password. example: 
           john,j123
           tom,tom123

        """
    print usage
    

def load(filepath):
    records = csvhandler.read(filepath)
    ds = AcctMgmtApi()
    total = 0
    for record in records:
        print record
        ds.create(record)
        total +=1
    print "load %s records "%(total,)

if __name__ == "__main__":
    if len(sys.argv)!=2:
        usage()
        sys.exit(2)
    filepath = sys.argv[1]
    apiclient.login_as_admin()
    load(filepath)
        
