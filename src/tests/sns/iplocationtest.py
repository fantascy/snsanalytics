import unittest

from common.utils import iplocation


class IpLocationTest(unittest.TestCase):
#    def testDnsLookup(self):
#        self.assertEquals("net",iplocation.get_tld_bydns("64.233.169.147"))
#        self.assertEquals(None,iplocation.get_tld_bydns("128.121.254.201"))
#        self.assertEquals("org",iplocation.get_tld_bydns("132.174.1.212"))
#        self.assertEquals("edu",iplocation.get_tld_bydns("128.103.60.28"))
#        self.assertEquals("cn",iplocation.get_tld_bydns("202.120.2.102"))
#        self.assertEquals("ca",iplocation.get_tld_bydns("142.150.210.13"))
    
    def _countryLookup(self, lookup_function=iplocation.get_country_by_qqlib):
        self.assertEquals("US",lookup_function("64.233.169.147"))
        self.assertEquals("US",lookup_function("128.121.254.201"))
        self.assertEquals("US",lookup_function("132.174.1.212"))
        self.assertEquals("US",lookup_function("128.103.60.28"))
        self.assertEquals("CN",lookup_function("202.120.2.102"))
        self.assertEquals("CA",lookup_function("142.150.210.13"))
        self.assertEquals("US",lookup_function("128.121.254.201"))
        self.assertEquals("XX",lookup_function("192.168.0.1"))
        
    def testLookupByHostIpDotCom(self):
        self._countryLookup(lookup_function=iplocation.get_country_by_hostip_urllib)
        self.assertEquals("UK",iplocation.get_country_by_hostip_urllib("83.138.163.176"))
        self.assertEquals("US",iplocation.get_country_by_hostip_urllib("1.2.3.4"))

    def testLookupByQQLib(self):
        self._countryLookup(lookup_function=iplocation.get_country_by_qqlib)
        self.assertEquals("US",iplocation.get_country_by_qqlib("83.138.163.176"))
        self.assertEquals("XX",iplocation.get_country_by_qqlib("1.2.3.4"))

