import subprocess
import sys

PLINK_PATH = r"C:\Program Files\PuTTY\plink.exe"
HOSTKEY = "SHA256:csiG0+qUBwQEy2+aYR0ZbEeZwpJDpmCH6wrLbxr39Ls"
PASSWORD = "Sriganesh@712"
CANDIDATE_HOSTS = ["root@10.50.27.58", "root@10.57.135.57", "root@10.158.208.57"]

def run_ssh(cmd_str):
    for host in CANDIDATE_HOSTS:
        try:
            res = subprocess.run(
                [PLINK_PATH, "-hostkey", HOSTKEY, "-batch", "-pw", PASSWORD, host, cmd_str],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30
            )
            return res.returncode, res.stdout, res.stderr
        except Exception:
            continue
    return 1, "", "Failed to connect to any candidate host"

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
