# Amia-plugin-group

`Amia-plugin-group` 当前是 Mizuki Bot 的群公告管理与自动分发插件。

仓库名虽然是 `group`，但当前代码并不提供完整的群管理能力；它暂时只负责维护公告、查看公告和向尚未收到最新公告的群聊或私聊补发一次。

## 插件作用

```text
超级用户维护公告
        ↓
notices.json
        ↓
其他 matcher 成功处理消息
        ↓
run_postprocessor 检查发送历史
        ↓
未收到最新公告的目标补发一次
```

当前不包含：

- 禁言；
- 踢人；
- 群成员权限管理；
- 入群审批；
- 完整群配置中心。

## 当前指令

```text
公告 查看
公告 查看 <序号>
公告 增加 <内容>
公告 修改 <序号> <内容>
公告 删除 <序号>
公告 统计
```

当前权限：

- 查看公告：所有用户；
- 增加、修改、删除：NoneBot `SUPERUSER`；
- 公告统计：当前代码未单独限制，需要后续确认是否应公开。

最多保存：

```text
5 条公告
```

## 自动分发机制

插件通过 `run_postprocessor` 在其他 matcher 成功处理后检查最新公告：

```text
任意指令成功执行
      ↓
读取最新公告
      ↓
计算公告内容哈希
      ↓
检查当前目标发送历史
      ↓
未发送则补发一次
```

目标标识：

```text
group_<group_id>
private_<user_id>
```

同一个目标只会收到同一版本公告一次。公告内容发生变化后，哈希变化，目标可以再次收到新版本。

公告发送失败不应影响用户原本执行的指令。

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

用途：

- `notices.json`：公告列表；
- `sent_history.json`：各目标最后收到的公告哈希。

这些文件属于运行数据，不应提交到 Git。

## 当前并发模型

当前使用进程内 `_sending_lock` 防止同一目标被多个 matcher 同时触发重复发送。

该方案只适用于单进程运行：

- 多 Worker 之间不能共享锁；
- 多实例之间不能保证唯一发送；
- JSON 写入没有跨进程文件锁；
- 进程异常退出时可能留下不完整文件。

需要多进程部署时，应改用 SQLite 或共享存储，并在存储层增加事务、唯一约束和原子更新。

## Permission 对接目标

当前增删改仍使用 `SUPERUSER`。后续应接入：

```text
group.notice.view
group.notice.manage
group.notice.stats
```

推荐调用：

```python
provider = registry.get_permission_provider("static")

if provider is None:
    allowed = False
else:
    result = await call_provider_safe(
        provider.has_permission,
        identity,
        "group.notice.manage",
        f"group:{event.group_id}",
        timeout=0.5,
    )
    allowed = bool(result.success and result.value)
```

Provider 缺失、超时或异常时必须默认拒绝。

当前代码尚未完成这项接入，README 中的权限节点是后续开发契约，不代表已经上线。

## Audit 对接目标

公告管理操作应写入：

```text
group.notice.create
group.notice.update
group.notice.delete
```

示例：

```python
audit = registry.get_audit_logger("sqlite")
if audit is not None:
    await audit.log_action(
        actor=identity,
        action="group.notice.update",
        target="notice:<index-or-hash>",
        details={
            "result": "success",
            "before": old_summary,
            "after": new_summary,
        },
    )
```

不应把完整无关聊天内容写入审计。

当前代码尚未完成 Audit 接入。

## 已确认的问题

### 宽泛异常捕获

部分代码使用裸 `except:`，可能隐藏：

- JSON 解析错误；
- 文件权限错误；
- OneBot 发送失败；
- 代码逻辑异常。

后续应捕获明确异常并记录限流日志，同时保持公告失败不影响原业务指令。

### 序号解析

`公告 修改` 等操作需要在执行 `int()` 前校验格式，非法序号必须返回提示，不能让 matcher 抛出异常。

### 统计权限

`公告 统计` 的访问范围尚未明确。接入 Permission 前，应先决定普通用户是否允许查看群覆盖情况。

### 多进程安全

当前 JSON 和进程锁方案不支持多 Worker，不能在未改存储的情况下宣称支持分布式部署。

### 插件自身排除

Postprocessor 通过 matcher 或插件名称排除自身时，应使用稳定标识，避免仓库或模块重命名后产生递归触发。

## 推荐重构顺序

1. 将 JSON 存储拆到 `storage.py`；
2. 使用临时文件写入后原子替换；
3. 拆出公告命令解析函数；
4. 修复非法序号和宽泛异常捕获；
5. 明确公告统计权限；
6. 接入 `PermissionProvider("static")`；
7. 接入 `AuditLogger("sqlite")`；
8. 增加完整测试；
9. 最后再决定是否扩展为通用群基础插件。

## 依赖

当前依赖：

```text
nonebot2
nonebot-adapter-onebot
```

后续对接：

```text
src.plugins.amia_core
Amia-plugin-permission
Amia-plugin-audit
```

## 测试

至少覆盖：

- 空公告列表；
- 新增达到 5 条上限；
- 非超管不能增删改；
- 非法序号不会崩溃；
- 同一目标同一公告只发送一次；
- 公告修改后重新发送；
- 群聊和私聊历史隔离；
- 发送失败后锁正常释放；
- JSON 损坏时安全降级并记录错误；
- Permission 缺失时默认拒绝；
- Audit 可用和不可用两种情况。

## 已知限制

- 当前仍使用 JSON 存储；
- 只保证单进程内的发送去重；
- 权限仍主要依赖 `SUPERUSER`；
- 尚未接入 Audit；
- 不具备完整群管理能力。

## 维护边界

- 不提交公告运行数据；
- 不在 Postprocessor 中执行耗时操作；
- 不因公告发送失败影响原 matcher；
- 不把本插件宣传成完整群管理框架；
- 当前仓库尚未确定公开许可证。