from common.utils import iplocation
import unittest
from google.appengine.ext import db
from sns.api import errors as api_error


class GeoCounter(db.Model):
    countryBracket = db.TextProperty(default="{}",required=True)
    
    def incrementGeoByCode(self,country_code):
        """
        increment geo, country_code is two char country code 
        """
        if not iplocation.isValidCountryCode(country_code) :
            return
        code=country_code.lower()
        counterMap=eval(self.countryBracket)
        counterMap[code]=counterMap.setdefault(code,0)+1
        self.countryBracket=str(counterMap)
    
    def incrementGeoByIpaddress(self,ipaddress):
        """
        increment by geo by an IP reverse lookup. ip address is requestor's ip address
        throws out an API_ERROR_GEO_NOT_FOUND location is not found
        """
        country=iplocation.get_country_by_qqlib(ipaddress)
        if not country:
            raise api_error.ApiError(api_error.API_ERROR_GEO_NOT_FOUND,ipaddress,"cannot find geolocation %s"%(ipaddress,))
        self.incrementGeoByCode(country)
        
    def getAllAsMap(self):
        return eval(self.countryBracket)
    
    def getSortedTopLocation(self,size=3,others=True):
        """
        return sorted top location and their counter
        size: number of records to return
        others: whether to count remaining records as one "others" category 
        """
        counterMap=eval(self.countryBracket)
        result=[]
        otherTotal=0
        for k,v in sorted(counterMap.items(), lambda x, y: cmp(x[1], y[1]),reverse=True):
            if size>0:
                result.append((k,v))
                size=size-1
            elif others:
                otherTotal=otherTotal+v
            else:
                break
        
        if others:
            result.append(("others",otherTotal))
        return result
                    
            
class GeoCounterTest(unittest.TestCase):
    def testIncrementGeoByCode(self):
        counter=GeoCounter()
        self.assertEquals(0,len(counter.getAllAsMap()))
        counter.incrementGeoByCode("us")
        self.assertEquals({"us":1},counter.getAllAsMap())
        counter.incrementGeoByCode("cn")
        self.assertEquals({"us":1,"cn":1},counter.getAllAsMap())
        counter.incrementGeoByCode("cn")
        self.assertEquals({"us":1,"cn":2},counter.getAllAsMap())
        counter.incrementGeoByCode("ca")
        self.assertEquals({"us":1,"cn":2,"ca":1},counter.getAllAsMap())
        counter.incrementGeoByCode("uk")
        self.assertEquals({"us":1,"cn":2,"ca":1,"uk":1},counter.getAllAsMap())
        self.assertEquals([("cn",2),("others",3)],counter.getSortedTopLocation(1))
        self.assertEquals([("cn",2)],counter.getSortedTopLocation(1,False))
        
    def testIncrementGeoByIpaddress(self):
        counter=GeoCounter()
        self.assertEquals(0,len(counter.getAllAsMap()))
        counter.incrementGeoByIpaddress("64.233.169.147")
        self.assertEquals({"us":1},counter.getAllAsMap())
        counter.incrementGeoByIpaddress("202.120.2.102")
        self.assertEquals({"us":1,"cn":1},counter.getAllAsMap())
        counter.incrementGeoByIpaddress("202.120.2.102")
        self.assertEquals({"us":1,"cn":2},counter.getAllAsMap())
        counter.incrementGeoByIpaddress("142.150.210.13")
        self.assertEquals({"us":1,"cn":2,"ca":1},counter.getAllAsMap())
        counter.incrementGeoByIpaddress("212.58.244.143")
        self.assertEquals({"us":1,"cn":2,"ca":1,"uk":1},counter.getAllAsMap())
        self.assertEquals([("cn",2),("others",3)],counter.getSortedTopLocation(1))
        self.assertEquals([("cn",2)],counter.getSortedTopLocation(1,False))
            
    def testExceptions(self):
        counter=GeoCounter()
        self.assertEquals(0,len(counter.getAllAsMap()))
        try:
            counter.incrementGeoByIpaddress("")
            self.fail("should throw exception")
        except:  
            pass
        

class CountryTest(unittest.TestCase):
    def testCountryCode(self):
        self.assertEquals("China", iplocation.get_country_name("CN"))
        self.assertEquals("United States", iplocation.get_country_name("us"))
        self.assertEquals("United Kingdom", iplocation.get_country_name("Uk"))

    
if __name__ == "__main__":
    unittest.main()
