import subprocess

print("[DEBUG] Force-closing Hay Day...")
subprocess.run(
    ['adb', '-s', '127.0.0.1:7555', 'shell', 'am', 'force-stop', 'com.supercell.hayday']
)
print("[DEBUG] Hay Day closed.")
