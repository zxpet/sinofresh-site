import subprocess, time, os

AB = "agent-browser"
OUT = "/Users/meng/WorkBuddy/sinofresh外贸网站建设/_backup/db-trash-templates-20260917-183841/shots"
os.makedirs(OUT, exist_ok=True)

def run(*args, timeout=60):
    r = subprocess.run([AB, *args], capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode, out.strip()

steps = [
    # 登录
    ("open login", ["open", "http://sinofresh.local/wp-login.php"]),
    ("viewport", ["set", "viewport", "1440", "900"]),
    ("snapshot", ["snapshot", "-i"]),
]
for name, args in steps:
    rc, out = run(*args)
    print(f"[{name}] rc={rc}")
    print(out[:1500])
    print("---")
