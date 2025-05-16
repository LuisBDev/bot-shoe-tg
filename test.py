import subprocess
import os

def toggle_tunnelbear():
    ahk_path = r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe"
    script_path = os.path.abspath("scripttunnelbear.ahk")
    print(f"Running AutoHotkey script: {script_path}")
    subprocess.run([ahk_path, script_path], check=True)

toggle_tunnelbear()
