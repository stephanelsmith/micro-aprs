
import vfs
from flashbdev import bdev

try:
    vfs.mount(bdev, '/')
except OSError:
    vfs.VfsLfs2.mkfs(bdev)
    _vfs = vfs.VfsLfs2(bdev)
    vfs.mount(_vfs, '/')

