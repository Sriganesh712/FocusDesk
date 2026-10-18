import serial
import time
import sys
import base64

def send_cmd(cmd, timeout=15):
    s = serial.Serial("COM4", 115200, timeout=0.5)
    s.reset_input_buffer()
    s.write(b"\x03\x03\nq\n\n")
    time.sleep(0.3)
    s.read(s.in_waiting or 1)
    
    full_cmd = f"PAGER=cat {cmd}\n"
    s.write(full_cmd.encode("utf-8"))
    
    start_time = time.time()
    buf = b""
    prompt = b"root@stm32mp1-e3-72-e5:"
    
    while time.time() - start_time < timeout:
        chunk = s.read(s.in_waiting or 1)
        if chunk:
            buf += chunk
            if prompt in buf[len(full_cmd):]:
                break
        else:
            time.sleep(0.1)
            
    s.close()
    return buf.decode("utf-8", errors="replace")

def run_py_remote(script_code, timeout=20):
    b64 = base64.b64encode(script_code.encode("utf-8")).decode("ascii")
    cmd = f"python3 -c \"import base64; exec(base64.b64decode('{b64}').decode())\""
    return send_cmd(cmd, timeout=timeout)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-py" and len(sys.argv) > 2:
        with open(sys.argv[2], "r", encoding="utf-8") as f:
            code = f.read()
        print(run_py_remote(code))
    elif len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        print(send_cmd(cmd))
    else:
        cmd = sys.stdin.read().strip()
        print(send_cmd(cmd))
