import json
import os
import time
import threading
import requests
from datetime import datetime

# =========================================================
# STATE
# =========================================================

STATE = {
    "running": True,
    "mode": "ACTIVE",
    "last_reflection": None
}

LOOP_INTERVAL = 8

# =========================================================
# FILES
# =========================================================

MEMORY_FILE = "memory.json"
TASKS_FILE = "tasks.json"
GOALS_FILE = "goals.json"

def init_files():
    defaults = {
        MEMORY_FILE: {"events": []},
        TASKS_FILE: {"tasks": []},
        GOALS_FILE: {"goals": []}
    }

    for f, d in defaults.items():
        if not os.path.exists(f):
            with open(f, "w") as x:
                json.dump(d, x, indent=2)

init_files()

def load(f):
    with open(f, "r") as x:
        return json.load(x)

def save(f, d):
    with open(f, "w") as x:
        json.dump(d, x, indent=2)

# =========================================================
# MEMORY LAYER (ENHANCED)
# =========================================================

def add_memory(text):
    m = load(MEMORY_FILE)
    m["events"].append({
        "time": str(datetime.now()),
        "text": text
    })
    save(MEMORY_FILE, m)

def get_memory(n=10):
    return load(MEMORY_FILE)["events"][-n:]

def memory_signal():
    """
    Extracts repeated concepts → influences reasoning
    """
    words = {}

    for e in get_memory(20):
        for w in e["text"].lower().split():
            words[w] = words.get(w, 0) + 1

    return sorted(words.items(), key=lambda x: x[1], reverse=True)[:5]

# =========================================================
# GOAL SYSTEM (PERSISTENT)
# =========================================================

def add_goal(goal):
    g = load(GOALS_FILE)

    g["goals"].append({
        "id": len(g["goals"]) + 1,
        "text": goal,
        "created": datetime.now().isoformat(),
        "strength": 5,   # importance weight
        "last_seen": datetime.now().isoformat()
    })

    save(GOALS_FILE, g)

def get_goals():
    return load(GOALS_FILE)["goals"]

def update_goal_activity(goal_id):
    g = load(GOALS_FILE)

    for goal in g["goals"]:
        if goal["id"] == goal_id:
            goal["last_seen"] = datetime.now().isoformat()
            goal["strength"] += 1

    save(GOALS_FILE, g)

def decay_goals():
    """
    Slowly reduces importance of unused goals
    """
    g = load(GOALS_FILE)

    for goal in g["goals"]:
        age = (datetime.now() - datetime.fromisoformat(goal["last_seen"])).total_seconds()
        goal["strength"] -= age / 3600  # decay per hour

        if goal["strength"] < 1:
            goal["strength"] = 1

    save(GOALS_FILE, g)

# =========================================================
# TASK SYSTEM
# =========================================================

def create_task(goal, parent=None):
    t = load(TASKS_FILE)

    task = {
        "id": len(t["tasks"]) + 1,
        "goal": goal,
        "parent": parent,
        "status": "active",
        "created": datetime.now().isoformat()
    }

    t["tasks"].append(task)
    save(TASKS_FILE, t)

    return task["id"]

def get_tasks():
    return load(TASKS_FILE)["tasks"]

# =========================================================
# REASONING CORE (LLM)
# =========================================================

LLM_URL = "http://localhost:11434/api/generate"

def think(prompt):
    try:
        r = requests.post(
            LLM_URL,
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False
            }
        )
        return r.json().get("response", "")
    except:
        return ""

# =========================================================
# GOAL DECOMPOSITION (LONG-TERM AWARE)
# =========================================================

def decompose(goal):
    prompt = f"""
Break this into steps:

Goal: {goal}

Return JSON list of 3–5 steps only.
"""

    result = think(prompt)

    try:
        steps = json.loads(result)
        if isinstance(steps, list):
            return steps
    except:
        pass

    return ["understand", "plan", "execute", "review"]

# =========================================================
# DECISION ENGINE (NOW LONG-TERM AWARE)
# =========================================================

def decide():
    decay_goals()

    goals = get_goals()
    mem = get_memory(10)
    signals = memory_signal()

    ranked = sorted(goals, key=lambda g: g["strength"], reverse=True)

    context = {
        "top_goals": ranked[:3],
        "memory": mem,
        "signals": signals
    }

    prompt = f"""
You are a long-term planning system.

You must decide what matters MOST over time.

GOALS:
{json.dumps(context["top_goals"], indent=2)}

MEMORY SIGNALS:
{json.dumps(context["signals"], indent=2)}

RECENT MEMORY:
{json.dumps(context["memory"], indent=2)}

Respond with:
- what is most important right now
- what is fading
- what should be reinforced
"""

    output = think(prompt)

    print("\n🧠 LONG-TERM REFLECTION")
    print(output)

    STATE["last_reflection"] = output

# =========================================================
# GOAL HANDLING
# =========================================================

def process_input(user):
    add_memory(user)
    add_goal(user)

# =========================================================
# LOOP
# =========================================================

def loop():
    while STATE["running"]:

        try:
            goals = get_goals()

            print("\n🧠 CYCLE")

            if goals:
                top = sorted(goals, key=lambda g: g["strength"], reverse=True)[0]
                print(f"Top goal: {top['text']} (strength {top['strength']:.2f})")
            else:
                print("No goals")

            decide()

        except Exception as e:
            print("Loop error:", e)

        time.sleep(LOOP_INTERVAL)

# =========================================================
# CHAT
# =========================================================

def chat():
    print("\n🚀 v7.5 LONG-TERM REASONING CORE\n")

    while True:
        user = input("You: ")

        if user == "/exit":
            STATE["running"] = False
            break

        process_input(user)

        decide()

# =========================================================
# START
# =========================================================

def start():
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    chat()

if __name__ == "__main__":
    start()