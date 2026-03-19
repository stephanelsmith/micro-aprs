
from json import loads
from json import dumps

def memoize_loads(name, *args):
    j = {}
    # raise Exception('failed to memoize')

    try:
        # with open('memoize.json', 'r') as f:
            # j = loads(f.read())
        from lib.memoizedat import j
    except:
        return None

    if name in j:
        for r in j[name]:
            if len(r['args'])==len(args) and all([a==b for a,b in zip(r['args'], args)]):
                return r['res']

    return None

def memoize_dumps(name, res, *args):
    j = {}
    # return

    try:
        # with open('memoize.json', 'r') as f:
            # j = loads(f.read())
        from lib.memoizedat import j
    except:
        pass

    if name not in j:
        j[name] = []

    j[name] = [r for r in j[name] if not (len(args)==len(r['args']) and all([a==b for a,b in zip(r['args'], args)])) ]
    j[name].append({
        'args' : args,
        'res'  : res,
    })

    try:
        with open('lib/memoizedat.py', 'w') as f:
            f.write('j=')
            f.write(dumps(j))
    except:
        # failed to memoize save
        pass


