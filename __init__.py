import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set

from nonebot import on_message, get_driver, logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.message import run_postprocessor
from nonebot.matcher import Matcher

from .storage import load_history, load_notices, save_json

# --- 插件元数据 ---
__plugin_meta__ = PluginMetadata(
    name="公告",
    description="Mizuki 智能公告系统",
    usage=(
        "直接发送：\n"
        "• 公告 增加 [内容] - 新增一条\n"
        "• 公告 修改 [序号] [内容] - 修改某条\n"
        "• 公告 删除 [序号] - 删除某条\n"
        "• 公告 查看 - 查看列表\n"
        "• 公告 统计 - 查看公告发送进度"
    )
)

# 路径设置
DATA_DIR = Path("data/mizuki_notice")
NOTICES_FILE = DATA_DIR / "notices.json"
HISTORY_FILE = DATA_DIR / "sent_history.json"

# --- 全局内存锁 (修复并发重复发送的核心) ---
# 记录当前正在发送公告的目标 ID，防止多个插件同时触发时重复发送
_sending_lock: Set[str] = set()

def get_content_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()

# --- 1. 公告管理指令 (管理员用) ---
notice_manage = on_message(priority=5, block=True)

@notice_manage.handle()
async def _(bot: Bot, event: MessageEvent):
    raw_text = event.get_plaintext().strip()
    if not raw_text.startswith("公告"):
        await notice_manage.skip()
        return

    parts = raw_text.split(maxsplit=2)
    notices = load_notices(NOTICES_FILE)

    # [统计]
    if len(parts) > 1 and parts[1] == "统计":
        if not await SUPERUSER(bot, event):
            await notice_manage.finish("你没有权限查看公告统计。")
        if not notices: await notice_manage.finish("目前没有公告，无法统计。")
        group_list = await bot.get_group_list()
        total_groups = len(group_list)
        latest_hash = get_content_hash(notices[-1])
        history = load_history(HISTORY_FILE)
        sent_count = sum(1 for gid, h in history.items() if h == latest_hash and gid.startswith("group"))
        await notice_manage.finish(f"最新公告覆盖: {sent_count} / {total_groups}")

    # [查看]
    if len(parts) == 1 or parts[1] == "查看":
        if not notices: await notice_manage.finish("当前暂无公告。")
        if len(parts) > 2 and parts[2].isdigit():
            idx = int(parts[2]) - 1
            if 0 <= idx < len(notices):
                await notice_manage.finish(f"--- 公告 {idx+1} ---\n{notices[idx]}")
            else:
                await notice_manage.finish(f"序号错误。")
        else:
            preview = "\n".join([f"{i+1}. {msg[:20]}..." for i, msg in enumerate(notices)])
            await notice_manage.finish(f"--- 公告列表 ---\n{preview}\n发送 [公告 查看 序号] 看全文")

    # --- 管理员操作 ---
    if not await SUPERUSER(bot, event): return

    if parts[1] == "增加":
        if len(notices) >= 5: await notice_manage.finish("位置已满(5/5)")
        content = parts[2] if len(parts) > 2 else ""
        if not content: await notice_manage.finish("内容不能为空")
        notices.append(content)
        save_json(NOTICES_FILE, notices)
        await notice_manage.finish("写入成功。")

    elif parts[1] == "修改":
        sub_parts = parts[2].split(maxsplit=1) if len(parts) > 2 else []
        if len(sub_parts) < 2 or not sub_parts[0].isdigit():
            await notice_manage.finish("格式错误")
        idx = int(sub_parts[0]) - 1
        if 0 <= idx < len(notices):
            notices[idx] = sub_parts[1]
            save_json(NOTICES_FILE, notices)
            await notice_manage.finish(f"公告 {idx+1} 已修改。")
        await notice_manage.finish("序号错误")

    elif parts[1] == "删除":
        if len(parts) <= 2 or not parts[2].isdigit():
            await notice_manage.finish("格式错误")
        idx = int(parts[2]) - 1
        if 0 <= idx < len(notices):
            notices.pop(idx)
            save_json(NOTICES_FILE, notices)
            await notice_manage.finish("已删除。")
        await notice_manage.finish("序号错误")

# --- 2. 核心逻辑：自动广播钩子 ---
@run_postprocessor
async def _(bot: Bot, event: MessageEvent, matcher: Matcher, exception: Optional[Exception]):
    if exception: return
    # 排除自身
    if matcher.plugin_name == "公告" or matcher.plugin_name == "notice": return
    if matcher == notice_manage: return

    notices = load_notices(NOTICES_FILE)
    if not notices: return

    latest_notice = notices[-1]
    latest_hash = get_content_hash(latest_notice)

    # 确定 ID
    if isinstance(event, GroupMessageEvent):
        target_id = f"group_{event.group_id}"
    else:
        target_id = f"private_{event.user_id}"

    # ---------------------------------------------------
    # [关键修复] 内存锁检查：如果已经在发了，直接跳过
    # ---------------------------------------------------
    if target_id in _sending_lock:
        return

    # 文件检查：如果以前发过，跳过
    history = load_history(HISTORY_FILE)
    if history.get(target_id) == latest_hash:
        return

    # [加锁] 标记这个 ID 正在处理中
    _sending_lock.add(target_id)

    try:
        # 发送公告
        await bot.send(event, f"【Mizuki 公告】\n{latest_notice}")
        
        # 写入文件记录
        history[target_id] = latest_hash
        save_json(HISTORY_FILE, history)
    except Exception as exc:
        logger.warning(f"公告补发失败 target={target_id}: {exc}")
    finally:
        # [解锁] 无论成功失败，处理完后移除锁
        # 即使文件保存失败，内存锁解除了，下次还会尝试发送（符合预期）
        # 如果文件保存成功，下次进文件检查就会被拦截
        if target_id in _sending_lock:
            _sending_lock.remove(target_id)
