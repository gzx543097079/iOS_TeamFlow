# 历史工作流资料

现行需求使用 REQ-0001 形式编号。旧版需求、delivery、review 回执和 BUGFIX-HISTORY 共 255 个文件已从当前目录移除；现行需求与验证证据保留。

清理前的完整资料保存在 Git 提交 `a8617dde5ee1c46f6aed4e726e9d545a096980fa`。旧日志中的路径与指纹是当时的快照，不改写为当前路径，也不作为当前代码验证结果。

```sh
# 列出历史需求与回执
git ls-tree -r --name-only a8617dde5ee1c46f6aed4e726e9d545a096980fa -- requirements logs/reviews
# 查看具体历史需求
git show a8617dde5ee1c46f6aed4e726e9d545a096980fa:requirements/REQ-20260915-074941506Z-ea88625b.md
```

按实际文件名替换第二条命令的路径。历史记录不再参与日常需求列表或维护。
