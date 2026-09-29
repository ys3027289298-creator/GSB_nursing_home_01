"""养老院核心逻辑：老人、床位、护工和药品。

只依赖标准库；日期由 state["day"] 显式驱动（固定日期），
存档为 JSON。入住、用药、结算、取消、排班、跌倒事件均幂等：
同一业务键重复提交不会产生第二次副作用。
"""

import json

MEDICINE_CAP = 50          # 药品库存上限
REFUND_DOSES = 10          # 取消一次护理返还的药品数
FALL_DAMAGE = 10           # 一次跌倒扣除的健康值
SAVE_PATH = "nursing_home.json"

_REQUIRED_KEYS = ("elders", "beds", "medicine", "nurses", "day", "shift_id")


def _valid_id(value):
    return isinstance(value, str) and value.strip() != ""


def new_game():
    return {
        "elders": {},
        "beds": {"B1": None, "B2": None},
        "medicine": 50,
        "nurses": {"N1": True, "N2": False},  # True = 在岗, False = 请假
        "day": 1,
        "shift_id": 0,
        "assignments": {},   # elder_id -> nurse_id，当前排班
        "shift_log": [],     # 交班记录：[{"shift_id": n, "elder": .., "nurse": ..}]
        "cancelled": [],     # 已取消（已退药）的老人，保证取消幂等
        "med_events": {},    # med_event_id -> elder_id，用药去重
        "fall_events": {},   # fall_event_id -> elder_id，跌倒事件去重
    }


def save_state(state, path=SAVE_PATH):
    text = json.dumps(state, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def load_state(text=None, path=SAVE_PATH):
    """读档必须是纯函数式恢复：不改写交班编号，避免读档后编号重复/跳号。"""
    if text is None:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    if not isinstance(text, str) or not text.strip():
        raise ValueError("存档为空")
    state = json.loads(text)
    if not isinstance(state, dict):
        raise ValueError("存档格式错误")
    for key in _REQUIRED_KEYS:
        if key not in state:
            raise ValueError("存档缺少字段: %s" % key)
    # 兼容旧存档：补齐幂等与交班相关字段
    state.setdefault("assignments", {})
    state.setdefault("shift_log", [])
    state.setdefault("cancelled", [])
    state.setdefault("med_events", {})
    state.setdefault("fall_events", {})
    return state


def admit(state, elder_id):
    """入住：同一老人不能重复入住；床位满时拒收。成功占用第一张空床。"""
    if not _valid_id(elder_id):
        return False
    elder_id = elder_id.strip()
    if elder_id in state["elders"]:
        return False
    free_bed = next((bed for bed, who in state["beds"].items() if who is None), None)
    if free_bed is None:
        return False
    state["elders"][elder_id] = {"health": 100, "bed": free_bed}
    state["beds"][free_bed] = elder_id
    return True


def fee(state, elder_id, end_day):
    """护理费按跨住天数计费：end_day - day。纯计算，可重复调用。"""
    if not _valid_id(elder_id):
        raise ValueError("老人编号非法")
    if not isinstance(end_day, int) or isinstance(end_day, bool):
        raise ValueError("结束日期非法")
    start_day = state["day"]
    if end_day < start_day:
        raise ValueError("结束日期早于当前日期")
    return end_day - start_day


def cancel_care(state, elder_id):
    """取消护理：释放床位与排班并返还药品；重复取消不再返还（幂等）。"""
    if not _valid_id(elder_id):
        return False
    elder_id = elder_id.strip()
    if elder_id in state.get("cancelled", []):
        return True
    state["cancelled"].append(elder_id)
    if elder_id in state["elders"]:
        bed = state["elders"][elder_id].get("bed")
        if bed is not None and state["beds"].get(bed) == elder_id:
            state["beds"][bed] = None
        del state["elders"][elder_id]
    state["assignments"].pop(elder_id, None)
    state["medicine"] = min(MEDICINE_CAP, state["medicine"] + REFUND_DOSES)
    return True


def schedule(state, elder_id, nurse):
    """排班：老人必须在住、护工必须存在且在岗；重复提交同一排班幂等返回成功。"""
    if not _valid_id(elder_id) or not _valid_id(nurse):
        return False
    elder_id = elder_id.strip()
    nurse = nurse.strip()
    if elder_id not in state["elders"]:
        return False
    if nurse not in state["nurses"] or not state["nurses"][nurse]:
        return False
    if state["assignments"].get(elder_id) == nurse:
        return True
    state["assignments"][elder_id] = nurse
    state["shift_id"] += 1
    state["shift_log"].append(
        {"shift_id": state["shift_id"], "elder": elder_id, "nurse": nurse}
    )
    return True


def medicate(state, elder_id, med_event_id=None):
    """用药：库存为 0 时失败且绝不扣库存；同一用药事件重复提交只扣一次。"""
    if not _valid_id(elder_id):
        return False
    elder_id = elder_id.strip()
    # 先判库存：库存为 0 时任何用药都失败且绝不扣库存
    if med_event_id is not None and med_event_id in state["med_events"]:
        return True
    if state["medicine"] <= 0:
        return False
    if elder_id not in state["elders"]:
        return False
    if med_event_id is not None:
        state["med_events"][med_event_id] = elder_id
    state["medicine"] -= 1
    return True


def fall(state, elder_id, event_id=None):
    """跌倒：扣一次健康；同一跌倒事件重复上报只扣一次；健康不低于 0。"""
    if not _valid_id(elder_id):
        return False
    elder_id = elder_id.strip()
    if elder_id not in state["elders"]:
        return False
    if event_id is not None:
        if event_id in state["fall_events"]:
            return True
        state["fall_events"][event_id] = elder_id
    health = state["elders"][elder_id]["health"]
    state["elders"][elder_id]["health"] = max(0, health - FALL_DAMAGE)
    return True


HELP = (
    "养老院 - 命令:\n"
    "  admit <老人编号>          入住\n"
    "  fee <老人编号> <结束日>   结算护理费\n"
    "  cancel <老人编号>         取消护理并退药\n"
    "  schedule <老人编号> <护工> 排班交班\n"
    "  medicate <老人编号> [事件号] 用药\n"
    "  fall <老人编号> [事件号]  上报跌倒\n"
    "  save / load / demo / quit"
)


def _run_command(state, parts):
    cmd = parts[0]
    if cmd == "admit":
        if len(parts) != 2:
            return "用法: admit <老人编号>", None
        return ("入住成功" if admit(state, parts[1]) else "入住失败：重复入住或床位已满"), None
    if cmd == "fee":
        if len(parts) != 3:
            return "用法: fee <老人编号> <结束日>", None
        try:
            return "护理费: %d" % fee(state, parts[1], int(parts[2])), None
        except ValueError as exc:
            return "结算失败: %s" % exc, None
    if cmd == "cancel":
        if len(parts) != 2:
            return "用法: cancel <老人编号>", None
        return ("已取消护理并返还药品" if cancel_care(state, parts[1]) else "取消失败"), None
    if cmd == "schedule":
        if len(parts) != 3:
            return "用法: schedule <老人编号> <护工>", None
        return ("排班成功" if schedule(state, parts[1], parts[2]) else "排班失败：护工请假或不存在"), None
    if cmd == "medicate":
        if len(parts) not in (2, 3):
            return "用法: medicate <老人编号> [事件号]", None
        event_id = parts[2] if len(parts) == 3 else None
        return ("用药成功" if medicate(state, parts[1], event_id) else "用药失败：无库存或老人不存在"), None
    if cmd == "fall":
        if len(parts) not in (2, 3):
            return "用法: fall <老人编号> [事件号]", None
        event_id = parts[2] if len(parts) == 3 else None
        return ("已记录跌倒" if fall(state, parts[1], event_id) else "上报失败：老人不存在"), None
    if cmd == "save":
        return "已存档: " + save_state(state), None
    if cmd == "load":
        return None, load_state()
    return "未知命令，输入 help 查看用法", None


def demo(path="nursing_home_demo.json"):
    """固定演示脚本：不读网络、不等待输入，展示幂等与边界行为。"""
    state = new_game()
    lines = []

    def step(label, ok, detail=""):
        lines.append("%-34s -> %s %s" % (label, "成功" if ok else "失败", detail))

    step("admit E1", admit(state, "E1"))
    step("admit E1(重复)", admit(state, "E1"))
    step("admit E2", admit(state, "E2"))
    step("admit E3(床位满)", admit(state, "E3"))
    lines.append("第1天入住、第4天退住护理费 = %d" % fee(state, "E1", 4))
    step("schedule E1 N2(请假护工)", schedule(state, "E1", "N2"))
    step("schedule E1 N1", schedule(state, "E1", "N1"))
    step("schedule E1 N1(重复)", schedule(state, "E1", "N1"))
    lines.append("交班编号 = %d" % state["shift_id"])
    step("medicate E1 m1", medicate(state, "E1", "m1"))
    step("medicate E1 m1(重复)", medicate(state, "E1", "m1"))
    lines.append("用药后库存 = %d" % state["medicine"])
    state["medicine"] = 0
    step("medicate E1(库存0)", medicate(state, "E1", "m2"))
    lines.append("失败后库存 = %d" % state["medicine"])
    state["elders"]["E1"]["health"] = 80
    step("fall E1 f1", fall(state, "E1", "f1"))
    step("fall E1 f1(重复事件)", fall(state, "E1", "f1"))
    lines.append("E1 健康 = %d" % state["elders"]["E1"]["health"])
    step("cancel E1", cancel_care(state, "E1"))
    step("cancel E1(重复取消)", cancel_care(state, "E1"))
    lines.append("取消后库存 = %d, B1 = %r" % (state["medicine"], state["beds"]["B1"]))
    save_state(state, path)
    loaded = load_state(path=path)
    lines.append("读档后交班编号 = %d (应仍为 %d)" % (loaded["shift_id"], state["shift_id"]))
    report = "\n".join(lines)
    print(report)
    return report


def main(argv=None):
    print(HELP)
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "demo":
        demo()
        return
    state = new_game()
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw:
            continue
        if raw == "quit":
            break
        if raw == "help":
            print(HELP)
            continue
        parts = raw.split()
        try:
            message, loaded = _run_command(state, parts)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print("操作失败: %s" % exc)
            continue
        if loaded is not None:
            state = loaded
            print("读档成功")
        elif message is not None:
            print(message)


if __name__ == "__main__":
    main()
