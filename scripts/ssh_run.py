import subprocess
import sys

PLINK_PATH = r"C:\Program Files\PuTTY\plink.exe"
HOSTKEY = "SHA256:csiG0+qUBwQEy2+aYR0ZbEeZwpJDpmCH6wrLbxr39Ls"
PASSWORD = "Sriganesh@712"
HOST = "root@10.57.135.57"

def run_ssh(cmd_str):
    res = subprocess.run(
        [PLINK_PATH, "-hostkey", HOSTKEY, "-batch", "-pw", PASSWORD, HOST, cmd_str],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return res.returncode, res.stdout, res.stderr

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) > 1:
        if sys.argv[1] == "-f" and len(sys.argv) > 2:
            with open(sys.argv[2], "r", encoding="utf-8") as f:
                cmd = f.read()
        else:
            cmd = " ".join(sys.argv[1:])
    else:
        cmd = sys.stdin.read()
    code, out, err = run_ssh(cmd)
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    sys.exit(code)
