"""项目内工具共享的路径边界。"""
from pathlib import Path


def local_path(root, name):
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('路径必须位于项目内：' + name)
    for node in (path, *path.parents):
        if node == root:
            break
        if node.is_symlink():
            raise ValueError('路径不能含符号链接：' + name)
    return path
