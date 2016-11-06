from PIL import Image
import urllib
import StringIO

from common.s3 import S3
from common import consts as common_const
import context


conn = S3.AWSAuthConnection(common_const.AWS_ACCESS_KEY_ID, common_const.AWS_SECRET_ACCESS_KEY)

url = 'http://www.allnewsoup.com/media/201/soup/images/no_image.png'

data = urllib.urlopen(url).read()

img = Image.open(StringIO.StringIO(data))

img.thumbnail((60,60)) 

output = StringIO.StringIO() 
img.save(output,format="PNG") 
contents = output.getvalue() 
output.close() 

conn.put(context.get_context().amazon_bucket(), 'huhu.png', contents)

print 'ok'