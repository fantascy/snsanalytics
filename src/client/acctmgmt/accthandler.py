import time
import random

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from sns.acctmgmt import consts as acctmgmt_const
from client.acctmgmt import consts as acctmgmt_client_const
from client.acctmgmt.api import AcctMgmtApi

    
def get_handler_by_type(acctType):
    if acctType==acctmgmt_const.ACCT_TYPE_YAHOO:
        return YahooHandler()
    else:
        return TwitterHandler()


class AccountHandler():
    def __init__(self):
        self.db = AcctMgmtApi()

    def start(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(acctmgmt_client_const.SELENIUM_IMPLICITLY_WAIT)

    def stop(self):
        self.driver.stop_client()
        self.driver.quit()

    def selenium_login(self, user, password):
        pass
    
    def selenium_change_password(self, user, password, new_password):
        pass
            
    def login(self, account):
        pass
    
    def change_password(self, account):
        pass
        
    def create_new_password(self):
        pass


class YahooHandler(AccountHandler):
    def selenium_login(self, user, password):
        base_url = "https://login.yahoo.com/"
        try:
            self.driver.get(base_url + "/config/login_verify2?&.src=ym")
            print "Clear username"
            self.driver.find_element_by_id("username").clear()
            print "Type username"
            self.driver.find_element_by_id("username").send_keys(user)
            print "Clear password"
            self.driver.find_element_by_id("passwd").clear()
            print "Type password"
            self.driver.find_element_by_id("passwd").send_keys(password)
            print "Click '.save'"
            self.driver.find_element_by_id(".save").click()
            self.driver.get("https://mail.yahoo.com/")
            
#            #handle the case yahoo asks for "Upgrade Now", click it if yahoo asks
#            try:
#                print "Click 'Upgrade Now'"
#                self.driver.find_element_by_link_text("Upgrade Now").click()
#            except NoSuchElementException: 
#                pass
#
#            try:
#                print "Click 'Let's go'"
#                self.driver.find_element_by_link_text("Let's Go").click()
#            except NoSuchElementException: 
#                pass
#            
#            ############may need to handle the continue case here
#            try:
#                print "Click 'remind'"
#                self.driver.find_element_by_id("remind").click()
#            except NoSuchElementException: 
#                pass

            #handle the case of captcha, return error if captcha is asked
            try:
                print "Check captcha"
                self.driver.find_element_by_id("captchaV5Header")
                return acctmgmt_const.YAHOO_STATE_CAPTCHA
            except NoSuchElementException: 
                pass
    
            #handle the case yahoo asks for browser upgrade
            try:
                print "Click 'No thanks, go to my inbox'"
                self.driver.find_element_by_id("skip").click()
            except NoSuchElementException: 
                pass

            print "Click inbox"
            self.driver.find_element_by_id("inbox").click()
        except:
            return acctmgmt_const.YAHOO_STATE_FAILURE
        finally:
            try:
                print "Click 'Sign Out'"
                self.driver.find_element_by_link_text("Sign Out").click()
            except:
                pass
        return acctmgmt_const.YAHOO_STATE_SUCCESS
    
    
    def selenium_change_password(self, user, password, new_password):
        r"""
        change yahoo password, return success or fail
        """
        print "Changing Yahoo password for user '%s' from '%s' to '%s'..." % (user, password, new_password)
        try:
            base_url = "https://login.yahoo.com/"
            self.driver.get(base_url + "/config/login?.src=fpctx&.intl=us&.done=http%3A%2F%2Fwww.yahoo.com%2F")
            self.driver.find_element_by_id("username").clear()
            self.driver.find_element_by_id("username").send_keys(user)
            self.driver.find_element_by_id("passwd").clear()
            self.driver.find_element_by_id("passwd").send_keys(password)
            self.driver.find_element_by_id(".save").click()
            self.driver.find_element_by_css_selector("em.strong.y-txt-4.medium").click()
            self.driver.find_element_by_css_selector("span.yuhead-name").click()
            self.driver.find_element_by_xpath("//a[contains(text(),'Account Info')]").click()
            self.driver.find_element_by_id("passwd").clear()
            self.driver.find_element_by_id("passwd").send_keys(password)
            self.driver.find_element_by_id(".save").click()
            self.driver.find_element_by_id("changepwd").click()
            self.driver.find_element_by_name(".opw").clear()
            self.driver.find_element_by_name(".opw").send_keys(password)
            self.driver.find_element_by_name(".pw1").clear()
            self.driver.find_element_by_name(".pw1").send_keys(new_password)
            self.driver.find_element_by_name(".pw2").clear()
            self.driver.find_element_by_name(".pw2").send_keys(new_password)
            self.driver.find_element_by_id("ContinueBtn").click()
            self.driver.find_element_by_name("PwBtn").click()
        except:
            return False
        finally:
            try:
                self.driver.find_element_by_id("ygmasignout").click()
            except:
                pass
        return True
            
    def login(self, account):
        user = account["name"]
        password = account["password"]
        account["acctType"] =  acctmgmt_const.ACCT_TYPE_YAHOO
        account["action"] =  acctmgmt_const.ACTION_YAHOO_LOGIN
        account["state"] = self.selenium_login(user, password)
        try:
            account = self.db.update(account)
        except Exception, ex:
            print str(ex)
        finally:
            print ", ".join(map(str, (account["state"], account['num'], user, password, account["lastLoginTime"])))
        time.sleep(random.randint(1, acctmgmt_client_const.YAHOO_LOGIN_TIME_INTERVAL))
    
    def change_password(self, account):
        user = account["name"]
        password = account["password"]
        if account["state"] == acctmgmt_const.YAHOO_STATE_SUCCESS:
            new_password = self.create_new_password()
            print "Started changing Yahoo password from '%s' to '%s' for user '%s'..." % (password, new_password, user)
            account["acctType"] =  acctmgmt_const.ACCT_TYPE_YAHOO
            account["action"] =  acctmgmt_const.ACTION_YAHOO_CHANGE_PASSWORD_BEGIN
            account["newPassword"] = new_password
            account = self.db.update(account)
            if self.selenium_change_password(user, password, new_password):
                account["state"] =  acctmgmt_const.YAHOO_STATE_SUCCESS
                print "Finished changing Yahoo password for user '%s'!" % user
            else:
                account["state"] =  acctmgmt_const.YAHOO_STATE_FAILURE
                print "Failed changing Yahoo password for user '%s'!" % user
            try:
                account["acctType"] =  acctmgmt_const.ACCT_TYPE_YAHOO
                account["action"] =  acctmgmt_const.ACTION_TWITTER_CHANGE_PASSWORD_END
                account = self.db.update(account)
            except:
                print "Completed changing Yahoo password for user '%s', but datastore udpate failed!" % user
            finally:
                print ", ".join(map(str, (account["state"], account['num'], user, password, new_password, account["lastPasswdChangeTime"])))
        time.sleep(random.randint(1, acctmgmt_client_const.YAHOO_PASSWD_CHANGE_TIME_INTERVAL))
        
    def create_new_password(self):
        return  "aNs%d" % random.randint(1000, 100000)


class TwitterHandler(AccountHandler):
    def __init__(self):
        self.base_url = "https://twitter.com/"
        AccountHandler.__init__(self)     
           
    def selenium_login(self, user, password):
        r"""
        login to twitter, return login status. Twitter randomly returns CAPTCHA. In manual verification, CAPTCHA is
        always challenged when the account was re-tried immediately, but it's not challenged one day later.
        """
        result = self._selenium_login_screen(user,password)
        self._selenium_logout_screen()
        return result
            
    
    def selenium_change_password(self,user, password, new_password):
        r"""
        change password. 
        return true if the password is changed. This method uses the same login/logout process, with an extra step of
        changing password.
        """
        print "Changing Twitter password for user '%s' from '%s' to '%s'..." % (user, password, new_password)
        result = False 
        if self._selenium_login_screen(user,password)==acctmgmt_const.TWITTER_STATE_SUCCESS:
            if self._selenium_change_password_screen(password, new_password):
                result = True
        self._selenium_logout_screen()
        return result

    def _selenium_login_screen(self, user, password):
        r"""
        dealing with login screen
        """
        try:
            driver = self.driver
            driver.get(self.base_url + "/?lang=en&logged_out=1#!/download")
            time.sleep(10)
            driver.find_element_by_id("signin-link").click()
            driver.find_element_by_name("session[username_or_email]").clear()
            driver.find_element_by_name("session[username_or_email]").send_keys(user)
            driver.find_element_by_name("session[password]").clear()
            driver.find_element_by_name("session[password]").send_keys(password)
            driver.find_element_by_css_selector("button.btn.submit").click()
            try: 
                driver.find_element_by_link_text("Suspended Accounts")
                return acctmgmt_const.TWITTER_STATE_SUSPENDED
            except NoSuchElementException: 
                pass
            try: 
                driver.find_element_by_id("recaptcha_response_field")
                return acctmgmt_const.TWITTER_STATE_CAPTCHA
            except NoSuchElementException: 
                pass
            try: 
                driver.find_element_by_id("global-new-tweet-button")
                self._selenium_reset_email_bounce()
                return acctmgmt_const.TWITTER_STATE_SUCCESS
            except NoSuchElementException: 
                pass
        except:
            pass
        return acctmgmt_const.TWITTER_STATE_FAILURE

    def _selenium_reset_email_bounce(self):    
        try: 
            self.driver.find_element_by_css_selector("a.reset-bounce-link").click()
            time.sleep(2)
            print "Successfully clicked to reset email bounce link!"
        except NoSuchElementException: 
            pass

    def _selenium_logout_screen(self):
        try:
            driver = self.driver
            driver.find_element_by_id("user-dropdown-toggle").click()
            driver.find_element_by_id("signout-button").click()
        except:
            pass
    
    def _selenium_change_password_screen(self, password, new_password):
        result = False
        try:
            driver = self.driver
            driver.find_element_by_id("user-dropdown-toggle").click()
            driver.find_element_by_link_text("Settings").click()
            driver.find_element_by_link_text("Password").click()
            driver.find_element_by_name("current_password").clear()
            driver.find_element_by_name("current_password").click()    
            driver.find_element_by_name("current_password").send_keys(password)
            driver.find_element_by_id("user_password").clear()
            driver.find_element_by_id("user_password").send_keys(new_password)
            driver.find_element_by_id("user_password_confirmation").clear()
            driver.find_element_by_id("user_password_confirmation").send_keys(new_password)
            driver.find_element_by_id("settings_save").click()
            result = True
            driver.find_element_by_link_text("No thanks").click()
        except:
            pass
        return result
    
    def login(self, account):
        user = account["tHandle"]
        password = account["tPassword"]
        account["acctType"] =  acctmgmt_const.ACCT_TYPE_TWITTER
        account["action"] =  acctmgmt_const.ACTION_TWITTER_LOGIN
        account["tState"] = self.selenium_login(user, password)
        try:
            account = self.db.update(account)
        except Exception, ex:
            print str(ex)
        finally:
            print ", ".join(map(str, (account["tState"], account['num'], user, password, account["tLastLoginTime"])))
        time.sleep(random.randint(1, acctmgmt_client_const.TWITTER_LOGIN_TIME_INTERVAL))
    
    def change_password(self, account):
        user = account["tHandle"]
        password = account["tPassword"]
        if account["state"] == acctmgmt_const.TWITTER_STATE_SUCCESS:
            new_password = self.create_new_password()
            print "Started changing Twitter password from '%s' to '%s' for handle '%s'..." % (password, new_password, user)
            account["acctType"] =  acctmgmt_const.ACCT_TYPE_TWITTER
            account["action"] =  acctmgmt_const.ACTION_TWITTER_CHANGE_PASSWORD_BEGIN
            account["tNewPassword"] = new_password
            account = self.db.update(account)
            if self.selenium_change_password(user, password, new_password):
                account["tSate"] =  acctmgmt_const.TWITTER_STATE_SUCCESS
                print "Finished changing Twitter password for user '%s'!" % user
            else:
                account["tState"] =  acctmgmt_const.TWITTER_STATE_FAILURE
                print "Failed changing Twitter password for user '%s'!" % user
            try:
                account["acctType"] =  acctmgmt_const.ACCT_TYPE_TWITTER
                account["action"] =  acctmgmt_const.ACTION_TWITTER_CHANGE_PASSWORD_END
                account = self.db.update(account)
            except:
                print "Completed changing Twitter password for user '%s', but datastore udpate failed!" % user
            finally:
                print ", ".join(map(str, (account["tState"], account['num'], user, password, new_password, account["tLastPasswdChangeTime"])))
        time.sleep(random.randint(1, acctmgmt_client_const.TWITTER_PASSWD_CHANGE_TIME_INTERVAL))

    def create_new_password(self):
        return  "rOne%d" % random.randint(1000, 100000)

