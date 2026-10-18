import sys
import base64
import subprocess

PLINK_PATH = r"C:\Program Files\PuTTY\plink.exe"
HOSTKEY = "SHA256:csiG0+qUBwQEy2+aYR0ZbEeZwpJDpmCH6wrLbxr39Ls"
PASSWORD = "Sriganesh@712"
CANDIDATE_HOSTS = ["root@10.50.27.58", "root@10.57.135.57", "root@10.158.208.57"]

def deploy_file(local_path, remote_path, mode="0755", owner="weston:weston"):
    with open(local_path, "rb") as f:
        data = f.read()
    b64_data = base64.b64encode(data).decode("ascii")
    
    remote_cmd = (
        f"python3 -c \"import sys, base64, os; "
        f"b64 = sys.stdin.read().strip(); "
        f"open('{remote_path}', 'wb').write(base64.b64decode(b64)); "
        f"os.chmod('{remote_path}', int('{mode}', 8)); "
        f"os.system('chown {owner} {remote_path}'); "
        f"print('Deployed {remote_path} ({len(data)} bytes)');\""
    )
    
    for host in CANDIDATE_HOSTS:
        try:
            proc = subprocess.Popen(
                [PLINK_PATH, "-hostkey", HOSTKEY, "-batch", "-pw", PASSWORD, host, remote_cmd],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            stdout, stderr = proc.communicate(input=b64_data, timeout=5)
            if proc.returncode == 0:
                print(f"Connected to {host}")
                print("RETURN CODE: 0")
                if stdout:
                    print("STDOUT:\n" + stdout)
                return
        except Exception:
            continue
    print("Could not deploy over SSH to any candidate host.")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        deploy_file(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python deploy_to_board.py <local_path> <remote_path>")
