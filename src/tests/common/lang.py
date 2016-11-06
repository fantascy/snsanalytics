import unittest


class Base:
    DEFAULT = None
    def name(self, v=None):
        return v if v else self.default_value()
    
    @classmethod
    def default_value(cls):
        return cls.DEFAULT
    
    
class Child(Base):
    DEFAULT = 'child'
        
    
class Parent(Child):
    DEFAULT = 'parent'
        

class TestPython(unittest.TestCase):
    def test_default_param_inheritance(self):
        self.assertEqual(Child().name(), Child.DEFAULT)
        self.assertEqual(Parent().name(), Parent.DEFAULT)


if __name__ == '__main__':
    unittest.main()

