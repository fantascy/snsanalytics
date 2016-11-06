 #! /usr/bin/env python
 # -*- coding: utf-8 -*-

""" IPLocator: locate IP in the QQWry.dat.
     Usage:
         python IPLocator.py 
     Create and test with Python 2.2.3.
     spadger@bmy <[email]echo.xjtu@gmail.com[/email]> 2008-2-19
 """
 
from binascii import b2a_hex 
import socket,string,struct,sys

class IPLocator :
    def __init__( self, ipdbFile ):
        self.ipdb = open( ipdbFile, "rb" )
        str = self.ipdb.read( 8 )
        (self.firstIndex,self.lastIndex) = struct.unpack('II',str)
        self.indexCount = (self.lastIndex - self.firstIndex)/7+1
        
    def about(self):
        return "%s。 纪录总数: %d 条 。" % (self.getVersion(), self.indexCount)
        
    def getVersion(self):
        s = self.getIpAddr(0xffffff00L)
        return s

    def getAreaAddr(self,offset=0):
        if offset :
            self.ipdb.seek( offset )
        str = self.ipdb.read( 1 )
        (byte,) = struct.unpack('B',str)
        if byte == 0x01 or byte == 0x02:
            p = self.getLong3()
            if p:
                return self.getString( p )
            else:
                return ""
        else:
            self.ipdb.seek(-1,1)
            return self.getString( offset )

    def getAddr(self,offset,ip=0):
        self.ipdb.seek( offset + 4)
        countryAddr = ""
        areaAddr = ""
        str = self.ipdb.read( 1 )
        (byte,) = struct.unpack('B',str)
        if byte == 0x01:
            countryOffset = self.getLong3()
            self.ipdb.seek( countryOffset )
            str = self.ipdb.read( 1 )
            (b,) = struct.unpack('B',str)
            if b == 0x02:
                countryAddr = self.getString( self.getLong3() )
                self.ipdb.seek( countryOffset + 4 )
            else:
                countryAddr = self.getString( countryOffset )
            areaAddr = self.getAreaAddr()
        elif byte == 0x02:
            countryAddr = self.getString( self.getLong3() )
            areaAddr = self.getAreaAddr( offset + 8 )
        else:
            countryAddr = self.getString( offset + 4 )
            areaAddr = self.getAreaAddr()
        return countryAddr + " " + areaAddr

    def dump(self, first ,last ):
        if last > self.indexCount :
            last = self.indexCount
        for index in range(first,last):
            offset = self.firstIndex + index * 7
            self.ipdb.seek( offset )
            buf = self.ipdb.read( 7 )
            (ip,of1,of2) = struct.unpack("IHB",buf)
            print "%d\t%s\t%s" %(index, self.ip2str(ip), \
                self.getAddr( of1 + (of2 << 16) ) )

    def setIpRange(self,index):
        offset = self.firstIndex + index * 7
        self.ipdb.seek( offset )
        buf = self.ipdb.read( 7 )
        (self.curStartIp,of1,of2) = struct.unpack("IHB",buf)
        self.curEndIpOffset = of1 + (of2 << 16)
        self.ipdb.seek( self.curEndIpOffset )
        buf = self.ipdb.read( 4 )
        (self.curEndIp,) = struct.unpack("I",buf)

    def getIpAddr(self,ip):
        L = 0
        R = self.indexCount - 1
        while L < R-1:
            M = (L + R) / 2
            self.setIpRange(M)
            if ip == self.curStartIp:
                L = M
                break
            if ip > self.curStartIp:
                L = M
            else:
                R = M
        self.setIpRange( L )
        #version information,255.255.255.X,urgy but useful
        if ip&0xffffff00L == 0xffffff00L:
            self.setIpRange( R )
        if self.curStartIp <= ip <= self.curEndIp:
            address = self.getAddr( self.curEndIpOffset )
            #把GBK转为utf-8
            address=unicode(address,'GBK').encode("utf-8")
            #把GB2312转为utf-8
            #address = unicode(address,'gb2312').encode("utf-8")
        else:
            address = "未找到该IP的地址"
        return address

    def getIpRange(self,ip):
        self.getIpAddr(ip)
        range = self.ip2str(self.curStartIp) + ' - ' \
            + self.ip2str(self.curEndIp)
        return range
    
    def getString(self,offset = 0):
        if offset :
            self.ipdb.seek( offset )
        str = ""
        ch = self.ipdb.read( 1 )
        (byte,) = struct.unpack('B',ch)
        while byte != 0:
            str = str + ch
            ch = self.ipdb.read( 1 )
            (byte,) = struct.unpack('B',ch)
        return str

    def ip2str(self,ip):
        return str(ip>>24)+'.'+str((ip>>16)&0xffL)+'.' \
            +str((ip>>8)&0xffL)+'.'+str(ip&0xffL)

    #def str2ip(self,s):
        #(ip,) = struct.unpack('L',socket.inet_aton(s))
        #return ((ip>>24)&0xffL)|((ip&0xffL)<<24) \
            #|((ip>>8)&0xff00L)|((ip&0xff00L)<<8)
    
    def str2ip(self,s):
        ips = s.split('.') 
        theIP = (int(ips[0]) << 24) | (int(ips[1]) << 16) | (int(ips[2]) << 8) | (int(ips[3]))
        return theIP
    
    def getLong3(self,offset = 0):
        if offset :
            self.ipdb.seek( offset )
        str = self.ipdb.read(3)
        (a,b) = struct.unpack('HB',str)
        return (b << 16) + a

#Demo
def main():
    import logging
    IPL = IPLocator("qqwry/QQWry.dat")
    ip = "138.89.40.230"
    address = IPL.getIpAddr( IPL.str2ip(ip) )
    range = IPL.getIpRange( IPL.str2ip(ip) )
    print "此IP %s 属于 %s\n所在网段: %s" % (ip,address, range)
 

if __name__ == "__main__" :
    main()