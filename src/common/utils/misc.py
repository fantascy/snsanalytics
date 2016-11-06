"""
Here is the place for all util functions that don't belong to an obvious category.
"""

def pop_keys(d, keys):
    if d is None:
        return
    for key in keys:
        if d.has_key(key):
            d.pop(key)


def long_2_int_list(objs):
    if objs is None:
        return None
    return [None if obj is None else int(obj) for obj in objs]


def list_dedupe_preserve_order(lists):
    if not lists:
        return []
    all_items = []
    for l in lists:
        all_items.extend(l)
    all_items = set(all_items) 
    result = []
    for l in lists:
        for item in l:
            if item in all_items:
                result.append(item)
                all_items.remove(item)
    return result
    
    