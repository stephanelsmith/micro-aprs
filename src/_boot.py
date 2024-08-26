
import vfs
from esp32 import Partition

bdev = Partition.find(Partition.TYPE_DATA, label="vfs")
bdev = bdev[0] if bdev else None

try:
    vfs.mount(bdev, '/')
except OSError:
    vfs.VfsLfs2.mkfs(bdev)
    _vfs = vfs.VfsLfs2(bdev)
    vfs.mount(_vfs, '/')

