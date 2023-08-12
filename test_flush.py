
import sys
import subprocess
import tempfile
with tempfile.NamedTemporaryFile('w') as fp:
    fp.write('''
import sys
sys.stdout.write('hello world')
sys.stdout.flush()
''')
    fp.flush()
    o = subprocess.check_output('python {}'.format(fp.name).split())
    print(o)
