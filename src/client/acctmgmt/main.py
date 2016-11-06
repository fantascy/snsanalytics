import optparse
import datetime
import sys

from sns.acctmgmt import consts as acctmgmt_const
from client import apiclient
from client.acctmgmt.api import AcctMgmtApi
from client.acctmgmt import csvhandler, accthandler


def main():
    p = optparse.OptionParser(
        description=r"""yahoo login check.""",
        prog="yahoo.py",
        version="0.1",
        usage=""" %prog [OPTION] """,
        )
    p.add_option("--file", "-f", action="store",
                 help="Acct csv file. Use file if specified, otherwise use GAE datastore.")
    p.add_option("--type", "-t", action="store", default='0',
                 help="Acct type: 0 - Yahoo, 1 - Twitter. Default to 0.")
    p.add_option("--operation", "-o", action="store", type="choice", choices=['0', '1', '2'], default='0', 
                 help="Select operation: 0 - login, 1 - change password, default to 0.")
    p.add_option("--states","-s",action="store", 
                 help="Multiple states separated in comma, for instance: 0,2,3. Default to all.")
    p.add_option("--days", "-d", action="store", 
                 help="Any account not updated within given days will be checked.") 
    p.add_option("--num", "-n", action="store", 
                 help="Work on a specific number range of accounts, for instance, 1-400, default to all.")
    options = p.parse_args()[0]
    acctType = int(options.type)
    operation = int(options.operation)
    if operation==acctmgmt_const.ACCT_MGMT_OP_CHANGE_PASSWORD:
        states = '1'
    else:
        states = options.states
    if options.days:
        days = int(options.days)
    else:
        days = None
    apiclient.login_as_admin()
    if options.file:
        filepath = options.file
        accounts = csvhandler.read(filepath)
    else:
        db = AcctMgmtApi()
        params = {
                  'acctType': acctType,
                  'operation': operation,
                  'states': states,
                  'num': options.num,
                  'days': days,
                  }
        accounts = db.query_all(params)
    if len(accounts)==0:
        print "No account is due for processing."
        return
    if operation==acctmgmt_const.ACCT_MGMT_OP_DUMP:
        csvhandler.write(accounts, sys.stdout, ",")
        return
    acctHandler = accthandler.get_handler_by_type(acctType)
    acctHandler.start()
    startTime = datetime.datetime.now()
    count = 0
    for account in accounts:
        if count%10==0 and count!=0:
            currentTime = datetime.datetime.now()
            print "Processed %d accounts in %s. Restarting browser..." % (count, str(currentTime-startTime))
            acctHandler.stop()
            acctHandler.start()
        if operation==acctmgmt_const.ACCT_MGMT_OP_LOGIN:
            acctHandler.login(account)
        else:
            acctHandler.change_password(account)
        count += 1
    acctHandler.stop()
    endTime = datetime.datetime.now()
    print "Processed %d accounts in %s." % (count, str(endTime-startTime))

if __name__ == "__main__":
    main()
