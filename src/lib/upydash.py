

# @micropython.native
def get(obj, val):
    if isinstance(obj, dict):
        if val in obj.keys():
            return obj[val]
        return None
    if hasattr(obj, val):
        return getattr(obj, val)
    return None

# @micropython.native
def find(coll, itertee):
    for el in coll:
        if itertee(el):
            return el
    return None
# @micropython.native
def find_index(coll, itertee):
    for i,el in enumerate(coll):
        if callable(itertee):
            if itertee(el):
                return i
        else:
            if itertee == el:
                return i
    return None

# @micropython.native
def first(coll):
    try:
        return coll[0]
    except:
        return None

# @micropython.native
def any(coll, itertee=None, emptylistval=False):
    if len(coll) == 0:
        return emptylistval
    for el in coll:
        if callable(itertee):
            if itertee(el):
                return True
        else:
            if el:
                return True
    return False
# @micropython.native
def some(coll, itertee=None,emptylistval=False):
    return any(coll, itertee=itertee, emptylistval=emptylistval)

# @micropython.native
def all(coll, itertee=None, emptylistval=True):
    if len(coll) == 0:
        return emptylistval
    for el in coll:
        if itertee:
            if not itertee(el):
                return False
        else:
            if not el:
                return False
    return True
# @micropython.native
def every(coll, itertee=None, emptylistval=True):
    return all(coll, itertee=itertee, emptylistval=emptylistval)

# @micropython.native
def filter(coll, itertee):
    return [el for el in coll if itertee(el)]

# @micropython.native
def map(coll, itertee):
    return [itertee(el) for el in coll]

# @micropython.native
def each(coll, itertee):
    for el in coll:
        itertee(el)
# @micropython.native
def for_each(coll, itertee):
    for el in coll:
        itertee(el)

# @micropython.native
def uniq(coll):
    return uniq_by(coll)

# @micropython.native
def uniq_by(coll, itertee):
    o = []
    u = []
    _get = get
    for el in coll:
        if callable(itertee):
            i = itertee(el)
        elif itertee == None:
            i = el
        else:
            i = _get(el, itertee)
        if i not in u:
            u.append(i)
            o.append(el)
    return o

# @micropython.native
def sort_by(coll, itertee):
    return sorted(coll, key=itertee)

# @micropython.native
def without(coll, values):
    if not isinstance(values, (list,tuple,)):
        values = [values]
    if isinstance(coll, (str,)):
        r = ''.join([el for el in coll if el not in values])
        return r
    else:
        r =  [el for el in coll if el not in values]
        return r

# @micropython.native
def reduce(coll, itertee, acc=0):
    for el in coll:
        acc = itertee(acc, el)
    return acc

# @micropython.native
def hexstr(num, size=4):
    hexstr = hex(num)[2:]
    return '0x' + '0'*(size-len(hexstr)) + hexstr

# @micropython.native
def bytes_str_debug(byts, replace='.'):
    conv = lambda y:chr(y) if y <128 and y>=32 else replace
    return ''.join([conv(x) for x in byts])


