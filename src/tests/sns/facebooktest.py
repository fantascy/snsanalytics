from common.utils.facebook import GraphAPI


ouath = '123930350960849|54e597cd9d6f63bd30989443-100001037863235|q8tSjcFhJJbHUVZnLgC6gE5WMlo.'

'''
path = "stream.publish"
args = {}
args['access_token']=ouath
args['uid']='129132637096954'
args['message']='just try'
file = urllib.urlopen("https://api.facebook.com/method/" + path + "?" +
                              urllib.urlencode(args))
a=file.read()
print a
'''

graph = GraphAPI(ouath)
a = graph.get_connections('me','likes')
t= a['id']
print t