# BAD: Command injection vulnerabilities
# Expected issues: command injection, shell=True, subprocess, shlex
import os
import subprocess


def run_command(user_input: str) -> str:
    """Run command - VULNERABLE to command injection."""
    # BAD: shell=True with user input
    result = subprocess.run(f"echo {user_input}", shell=True, capture_output=True, text=True)
    return result.stdout


def list_files(directory: str) -> str:
    """List files - VULNERABLE to command injection."""
    # BAD: os.system with user input
    os.system(f"ls -la {directory}")
    return "done"


def ping_host(hostname: str) -> str:
    """Ping host - VULNERABLE to command injection."""
    # BAD: Popen with shell=True and user input
    proc = subprocess.Popen(f"ping -c 1 {hostname}", shell=True, stdout=subprocess.PIPE)
    output, _ = proc.communicate()
    return output.decode()
