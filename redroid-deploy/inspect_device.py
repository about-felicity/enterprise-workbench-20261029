"""Capture the current Android screen and accessible UI without sending a question."""
import os
import sys
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
os.environ["ADBUTILS_ADB_PATH"] = str(ROOT / "artifacts" / "platform-tools" / "adb.exe")

import uiautomator2 as u2

parser = argparse.ArgumentParser()
parser.add_argument('--serial', default='127.0.0.1:15557')
device = u2.connect(parser.parse_args().serial)
print("Foreground:", device.app_current())
xml = device.dump_hierarchy()
(ROOT / "artifacts" / "screen.xml").write_text(xml, encoding="utf-8")
device.screenshot().save(ROOT / "artifacts" / "screen.png")
for node in ET.fromstring(xml).iter("node"):
    a = node.attrib
    if a.get("text") or a.get("content-desc") or a.get("class", "").endswith("EditText"):
        print({k: a.get(k, "") for k in ["text", "content-desc", "resource-id", "class", "bounds"]})
