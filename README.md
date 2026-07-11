# Amia-plugin-group

`Amia-plugin-group` 当前实际实现是 Mizuki Bot 的群聊公告管理与自动分发插件。它允许超管维护最多 5 条公告，并在群聊或私聊中其他 matcher 成功处理消息后，向尚未收到最新公告的目标自动补发一次。

仓库名虽然是 `group`，但当前代码职责并不是通用群管理框架；后续扩展前应先决定是否继续保留“公告插件”定位。

## 当前功能

### 公告管理

```text
公告 查看
公告 查看 <序号>
公告 增加 <内容>
公告 修改 <序号> <内容>
公告 删除 <序号>
公告 统计
```

权限：

- 查看公告：所有用户。
- 增加、修改、删除：NoneBot `SUPERUSER`。
- 统计：当前代码未单独限制为超管，维护时应确认是否符合预期。

最多保存：

```text
5 条公告
```

### 自动分发

插件通过 `run_postprocessor` 在其他 matcher 成功执行后检查最新公告：

```text
任意指令成功处理
      ↓
检查最新公告内容哈希
      ↓
当前群/私聊是否已发送
      ↓
未发送则补发一次
```

目标标识：

```text
group_<group_id>
private_<user_id>
```

同一最新公告在每个目标中只发送一次。

## 数据文件

默认目录：

```text
data/mizuki_notice/
```

文件：

```text
notices.json
sent_history.json
```

- `notices.json` 保存公告列表。
- `sent_history.json` 保存每个目标最后收到的公告哈希。
- 运行数据不应提交到 Git。

## 并发处理

当前使用进程内 `_sending_lock` 防止同一目标被多个 matcher 同时触发重复发送。

限制：

- 只在单进程内有效。
- 多进程/多实例部署时不能保证全局唯一。
- JSON 文件写入没有跨进程文件锁。

如果以后运行多个 Worker，应改用 SQLite 或共享存储，并在存储层实现唯一约束或事务锁。

## 当前已知风险

### 1. 宽泛异常吞掉

当前部分代码使用裸 `except:`，会隐藏：

- JSON 解析错误。
- 文件权限问题。
- OneBot 发送失败。
- 代码逻辑异常。

后续应改为明确异常类型并记录日志，但自动公告失败不应阻断用户原指令。

### 2. 序号解析

`公告 修改` 直接执行 `int()`，非法序号可能触发异常。应先校验 `isdigit()` 并给出格式提示。

### 3. 公告统计口径

当前统计通过：

```python
gid.startswith("group")
```

计算群覆盖数，并与 `get_group_list()` 总群数比较。需要补测试确认历史文件格式与前缀一致。

### 4. Plugin 名称判断

Postprocessor 当前通过 matcher/plugin 名称排除自身。插件重命名后可能失效，建议优先比较 matcher 对象或稳定插件名。

## 后续最小重构建议

1. 把 JSON 存储拆到 `storage.py`。
2. 增加原子写入：临时文件写完后替换。
3. 为管理命令拆出解析函数。
4. 给所有文件和发送异常增加限流日志。
5. 增加群/私聊发送策略配置。
6. 接入 `AuditLogger("sqlite")` 记录公告增删改。
7. 接入 PermissionProvider，逐步替换只有 `SUPERUSER` 的粗粒度权限。
8. 再决定是否扩展为通用群基础插件。

## 审计建议

管理操作建议记录：

```text
group.notice.create
group.notice.update
group.notice.delete
```

示例目标：

```text
notice:<index 或 hash>
```

`details` 可包含操作前后内容摘要，但不应记录不必要的用户聊天内容。

## 测试建议

至少覆盖：

- 空公告列表。
- 新增达到 5 条上限。
- 非超管不能增删改。
- 非法序号不会崩溃。
- 同一目标同一公告只发送一次。
- 公告内容修改后会重新发送。
- 群聊和私聊历史相互隔离。
- 发送失败后锁能释放。
- JSON 损坏时安全降级并记录错误。

## 依赖

```text
nonebot2
nonebot-adapter-onebot
```

可选后续集成：

```text
src.plugins.amia_core
Amia-plugin-audit
Amia-plugin-permission
```

## 维护边界

- 不把公告历史文件提交到 Git。
- 不在 Postprocessor 中执行耗时网络请求。
- 不因公告发送失败影响原业务 matcher。
- 不把本插件描述成已经具备完整群权限、禁言或成员管理能力。
- 当前仓库尚未确定公开许可证。