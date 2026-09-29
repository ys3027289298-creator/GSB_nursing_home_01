"""养老院核心逻辑：老人、床位、护工和药品。"""

import json


def new_game():
    return {
        "elders": {},
        "beds": {"B1": None, "B2": None},
        "medicine": 50,
        "nurses": {"N1": True, "N2": False},
        "day": 1,
        "shift_id": 0,
    }


def save_state(state):
    return json.dumps(state, ensure_ascii=False)


def load_state(text):
    state = json.loads(text)
    return state


def admit(state, elder_id):
    if elder_id in state["elders"]:
        return False
    if None not in state["beds"].values():
        return False
    for bed, occupant in state["beds"].items():
        if occupant is None:
            state["beds"][bed] = elder_id
            break
    state["elders"][elder_id] = {"health": 100}
    return True


def fee(state, elder_id, end_day):
    return end_day - state["day"]


def cancel_care(state, elder_id):
    state["medicine"] += 10
    return True


def schedule(state, elder_id, nurse):
    return bool(state["nurses"].get(nurse))


def medicate(state, elder_id):
    if state["medicine"] <= 0:
        return False
    state["medicine"] -= 1
    return True


def fall(state, elder_id):
    elder = state["elders"].get(elder_id)
    if elder is None:
        return False
    elder["health"] -= 10
    return True


def main():
    print("养老院 - 命令: admit/fee/cancel/schedule/medicate/fall/quit")
    state = new_game()
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw or raw == "quit":
            break
        parts = raw.split()
        cmd, args = parts[0], parts[1:]
        try:
            if cmd == "admit" and len(args) == 1:
                print("ok" if admit(state, args[0]) else "失败: 重复入住或床位已满")
            elif cmd == "fee" and len(args) == 2:
                print(fee(state, args[0], int(args[1])))
            elif cmd == "cancel" and len(args) == 1:
                print("ok" if cancel_care(state, args[0]) else "失败")
            elif cmd == "schedule" and len(args) == 2:
                print("ok" if schedule(state, args[0], args[1]) else "失败: 护工请假或不存在")
            elif cmd == "medicate" and len(args) == 1:
                print("ok" if medicate(state, args[0]) else "失败: 药品不足")
            elif cmd == "fall" and len(args) == 1:
                print("ok" if fall(state, args[0]) else "失败: 老人未入住")
            else:
                print("非法命令")
        except (ValueError, KeyError) as exc:
            print(f"错误: {exc}")


if __name__ == "__main__":
    main()
