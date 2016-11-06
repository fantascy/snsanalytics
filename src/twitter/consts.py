USER_AGENT = 'SNS Analytics'


POST_ACTIONS = [
    # Status Methods
    'update', 'retweet', 'update_with_media',

    # Direct Message Methods
    'new', 

    # Account Methods
    'update_profile_image', 'update_delivery_device', 'update_profile', 
    'update_profile_background_image', 'update_profile_colors', 
    'update_location', 'end_session', 

    # Notification Methods
    'leave', 'follow', 

    # Status Methods, Block Methods, Direct Message Methods, 
    # Friendship Methods, Favorite Methods
    'destroy', 

    # Block Methods, Friendship Methods, Favorite Methods
    'create', 
    ]


ID_IN_URI_ACTIONS = set([
    '/saved_searches/destroy',
    '/saved_searches/show',
    '/statuses/destroy',
    '/statuses/retweet',
    '/statuses/retweets',
    '/statuses/show',
    ])


CONNECTIONS_FOLLOWING = 'following'
CONNECTIONS_FOLLOWING_REQUESTED = 'following_requested'
CONNECTIONS_FOLLOWED_BY = 'followed_by'
CONNECTIONS_NONE = 'none'
CONNECTIONS_TYPES = (CONNECTIONS_FOLLOWING, CONNECTIONS_FOLLOWING_REQUESTED, CONNECTIONS_FOLLOWED_BY, CONNECTIONS_NONE)


MINIMUM_IMAGE_WIDTH = 251
MINIMUM_IMAGE_HEIGHT = 201


