import argparse
import re
import subprocess
import time
import xml.etree.ElementTree as ET


ADB = r"C:\Program Files\Netease\MuMu\nx_device\15.0\shell\adb.exe"
DEVICE = "127.0.0.1:16384"
DEEPSEEK_PACKAGE = "com.deepseek.chat"


def adb(*args, timeout=20, check=True):
    cmd = [ADB, "-s", DEVICE, *args]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError("ADB failed:\n" + " ".join(cmd) + "\n" + p.stdout + "\n" + p.stderr)
    return p.stdout.strip()


def connect():
    subprocess.run([ADB, "connect", DEVICE], capture_output=True, text=True, encoding="utf-8", errors="ignore")


def bounds_center(bounds):
    nums = [int(x) for x in re.findall(r"\d+", bounds or "")]
    if len(nums) != 4:
        return None
    x1, y1, x2, y2 = nums
    return (x1 + x2) // 2, (y1 + y2) // 2


def dump_ui():
    adb("shell", "uiautomator", "dump", "/sdcard/window.xml", timeout=10, check=False)
    xml = adb("exec-out", "cat", "/sdcard/window.xml", timeout=10)
    return ET.fromstring(xml)


def iter_nodes(root):
    yield root
    for child in root:
        yield from iter_nodes(child)


def node_text(node):
    return (node.attrib.get("text") or "") + " " + (node.attrib.get("hint") or "") + " " + (node.attrib.get("content-desc") or "")


def find_node(root, predicate):
    for node in iter_nodes(root):
        if predicate(node):
            return node
    return None


def tap(x, y):
    adb("shell", "input", "tap", str(int(x)), str(int(y)))
    time.sleep(0.25)


def find_input(root):
    candidates = []
    for node in iter_nodes(root):
        if node.attrib.get("class") == "android.widget.EditText":
            text = node_text(node)
            center = bounds_center(node.attrib.get("bounds"))
            if not center:
                continue
            score = 0
            if "发消息" in text:
                score += 100
            if node.attrib.get("focused") == "true":
                score += 30
            # DeepSeek input box is normally on the right half and near the bottom in MuMu tablet layout.
            if center[0] > 500:
                score += 10
            if center[1] > 700:
                score += 10
            candidates.append((score, center, node))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def find_button_by_desc(root, desc):
    node = find_node(root, lambda n: desc in (n.attrib.get("content-desc") or ""))
    if node is None:
        return None
    return bounds_center(node.attrib.get("bounds"))


def clear_input(max_delete=80):
    # Move cursor to end, then backspace enough times. This avoids relying on clipboard or IME shortcuts.
    adb("shell", "input", "keyevent", "123")  # KEYCODE_MOVE_END
    for _ in range(max_delete):
        adb("shell", "input", "keyevent", "67", check=False)  # KEYCODE_DEL
    time.sleep(0.2)


def input_text(text):
    # Android input text treats spaces specially; %s is converted to a space by input command.
    text_arg = text.replace(" ", "%s")
    adb("shell", "input", "text", text_arg, timeout=30)
    time.sleep(0.4)


def click_send():
    root = dump_ui()
    center = find_button_by_desc(root, "发送")
    if center:
        tap(*center)
        return True
    # Fallback for current MuMu DeepSeek landscape layout.
    tap(1782, 1019)
    return True


def click_new_chat():
    root = dump_ui()
    center = find_button_by_desc(root, "开启新对话")
    if center:
        tap(*center)
        return True
    # Fallback top-right plus button.
    tap(1877, 84)
    return True


def focus_input():
    root = dump_ui()
    center = find_input(root)
    if not center:
        raise RuntimeError("没有找到 DeepSeek 输入框")
    tap(*center)
    return center


def wait_answer(seconds):
    # Simple demo wait. The real loop can replace this with a stronger completion detector later.
    time.sleep(seconds)


def ask_once(text, wait_seconds=30, new_chat_after=True):
    focus_input()
    clear_input()
    input_text(text)
    click_send()
    wait_answer(wait_seconds)
    if new_chat_after:
        click_new_chat()
        time.sleep(1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="帮我推荐一款防过敏的白发染发剂")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--wait", type=int, default=30)
    parser.add_argument("--no-new-chat", action="store_true")
    parser.add_argument("--no-send", action="store_true", help="只测试输入，不点击发送")
    args = parser.parse_args()

    connect()
    for i in range(args.rounds):
        print(f"round {i + 1}/{args.rounds}")
        focus_input()
        clear_input()
        input_text(args.text)
        if not args.no_send:
            click_send()
            wait_answer(args.wait)
            if not args.no_new_chat:
                click_new_chat()
                time.sleep(1.0)
    print("done")


if __name__ == "__main__":
    main()
