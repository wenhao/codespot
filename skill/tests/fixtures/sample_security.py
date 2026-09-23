import subprocess

DB_PASSWORD = "s3cr3tpw"  # B105 hardcoded password -> critical


def run(cmd):
    return subprocess.call(cmd, shell=True)  # B602 shell=True -> major
