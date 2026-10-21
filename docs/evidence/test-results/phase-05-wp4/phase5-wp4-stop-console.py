"""Send ordinary Ctrl+C to the independently identified WP3 Uvicorn console."""
import ctypes, json, sys, time, socket
from pathlib import Path
from datetime import datetime, timezone
pid=int(sys.argv[1]); output=Path(sys.argv[2]); port=int(sys.argv[3]) if len(sys.argv)>3 else 8000; assert not output.exists()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.FreeConsole()
attached=bool(k.AttachConsole(pid)); attach_error=ctypes.get_last_error()
result={'at':datetime.now(timezone.utc).isoformat(),'targetPid':pid,'port':port,'method':'AttachConsole then CTRL_C_EVENT; no terminate/kill','attached':attached,'attachError':0 if attached else attach_error}
if attached:
    k.SetConsoleCtrlHandler(None,True)
    result['ctrlCSent']=bool(k.GenerateConsoleCtrlEvent(0,0))
    result['controlError']=0 if result['ctrlCSent'] else ctypes.get_last_error()
    time.sleep(1);k.FreeConsole()
for _ in range(60):
    with socket.socket() as s:
        s.settimeout(.25); listening=s.connect_ex(('127.0.0.1',port))==0
    if not listening: break
    time.sleep(.5)
result['portClosed']=not listening
k.OpenProcess.restype=ctypes.c_void_p
handle=k.OpenProcess(0x100000,False,pid)
if handle:
    k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    result['targetProcessExited']=k.WaitForSingleObject(handle,3000)==0
    k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle(handle)
else:
    result['targetProcessExited']=ctypes.get_last_error()==87
output.write_text(json.dumps(result,indent=2),encoding='utf-8')
sys.exit(0 if result.get('ctrlCSent') and not listening and result['targetProcessExited'] else 1)
