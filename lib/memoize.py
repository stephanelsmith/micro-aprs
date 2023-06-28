
from json import loads
from json import dumps


def memoize_loads(name, *args):

    j = {}

    try:
        with open('memoize.json', 'r') as f:
            j = loads(f.read())
    except:
        raise Exception('failed to memoize')

    if name in j:
        for r in j[name]:
            if len(r['args'])==len(args) and all([a==b for a,b in zip(r['args'], args)]):
                return r['res']

    raise Exception('failed to memoize')

def memoize_dumps(name, res, *args):
    j = {}

    try:
        with open('memoize.json', 'r') as f:
            j = loads(f.read())
    except:
        pass

    if name not in j:
        j[name] = []

    j[name] = [r for r in j[name] if not (len(args)==len(r['args']) and all([a==b for a,b in zip(r['args'], args)])) ]
    j[name].append({
        'args' : args,
        'res'  : res,
    })

    with open('memoize.json', 'w') as f:
        f.write(dumps(j))


