# -*- coding: utf-8 -*-

import unittest

from common.utils import image as image_util


IMAGES = [
          "http://www.washingtonpost.com/blogs/plum-line/files/2014/12/Senators_2016-0efe5_image.jpg",
          "https://img.washingtonpost.com/rw/2010-2019/WashingtonPost/2015/04/30/Health-Environment-Science/Images/7187958018_1276684eb8_o1430352851.jpg",
          ]


class TestImage(unittest.TestCase):
    def test_size_and_dimension(self):
        image_url = IMAGES[0]
        image_data = image_util.data_by_url(image_url)
        image_size = image_util.size_by_data(image_data)
        image_dimension = image_util.dimension_by_data(image_data)
        self.assertTrue(image_size==3575174 and image_dimension==(3000, 2083))
        new_image_data = image_util.resize_data(image_data, maxdim=2000)
        new_image_size = image_util.size_by_data(new_image_data)
        new_image_dimension = image_util.dimension_by_data(new_image_data)
        print new_image_size, new_image_dimension
        self.assertTrue(image_size==201656 and image_dimension==(2000, 1388))

    
if __name__ == '__main__':
    unittest.main()

