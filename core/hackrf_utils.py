import subprocess
import re

def reset_hackrf():
    """Reset the HackRF device."""
    subprocess.run(["hackrf_transfer", "-r", "/dev/null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["hackrf_transfer", "-t", "/dev/null"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("HackRF reset completed.")

def list_hackrf_devices():
    """List all connected HackRF devices using hackrf_info."""
    try:
        result = subprocess.run(['hackrf_info', '-s'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"hackrf_info error: {result.stderr}")
            return []

        devices = []
        lines = result.stdout.splitlines()
        current_device = None
        for line in lines:
            index_match = re.match(r'Index:\s+(\d+)', line)
            if index_match:
                current_device = {'index': int(index_match.group(1)), 'serial': None}
                devices.append(current_device)
            serial_match = re.match(r'Serial number:\s+([0-9a-fA-F]+)', line)
            if serial_match and current_device:
                current_device['serial'] = serial_match.group(1)
        print(f"Detected HackRF devices: {devices}")
        return devices
    except FileNotFoundError:
        print("hackrf_info not found. Ensure HackRF tools are installed.")
        return []
    except Exception as e:
        print(f"Error listing HackRF devices: {e}")
        return []
