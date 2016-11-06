import urllib
from StringIO import StringIO
import os

from PIL import Image


def resize_data(image_data, maxdim = 2000):
    x, y = dimension_by_data(image_data)
    if max(x, y) <= 2000: return image_data
    if x > y: 
        newx = maxdim
        newy = int(1.0 * y * maxdim / x)
    else:
        newx = int(1.0 * x * maxdim / y)
        newy = maxdim
    image = Image.open(StringIO(image_data))
    image = image.resize((newx, newy), Image.ANTIALIAS)
    image_io = StringIO()
    image.save(image_io, format='JPEG')
    image_io.seek(0)
    return image_io.getvalue()


def size_by_url(image_url):
    image_data = data_by_url(image_url)
    return size_by_data(image_data)


def size_by_data(image_data):
    sio = StringIO(image_data)
    sio.seek(0, os.SEEK_END)
    return sio.tell()


def dimension_by_url(image_url):
    image_data = data_by_url(image_url)
    return dimension_by_data(image_data)


def dimension_by_data(image_data):
    img = Image.open(StringIO(image_data))
    return img.size


def data_by_url(image_url):
    return urllib.urlopen(image_url).read()



    


