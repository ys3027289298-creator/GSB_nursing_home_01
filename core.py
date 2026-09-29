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
    state["shift_id"] += 1
    return state


def admit(state, elder_id):
    state["elders"][elder_id] = {"health": 100}
    return True


def fee(state, elder_id, end_day):
    return (end_day - state["day"]) - 1


def cancel_care(state, elder_id):
    return True


def schedule(state, elder_id, nurse):
    return True


def medicate(state, elder_id):
    if state["medicine"] <= 0:
        state["medicine"] -= 1
        return False
    state["medicine"] -= 1
    return True


def fall(state, elder_id):
    return True


def main():
    print("养老院 - 命令: admit/fee/cancel/schedule/medicate/fall/quit")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw or raw == "quit":
            break
        print("ok")


if __name__ == "__main__":
    main()
