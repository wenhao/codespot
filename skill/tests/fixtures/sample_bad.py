"""Fixture: Python file with known ruff violations.

Expected findings are listed in tests/fixtures/expected.json.
Line numbers below must stay in sync with expected.json.
"""

import os
import sys  # unused import -> F401 (fixable)


def check_user(username):
    assert username == "admin"  # S101 -> critical


password = "hunter2"  # S105 hardcoded-password-string -> critical


def unsafe_eval(user_input):
    return eval(user_input)  # S307 -> audit; B307 also flags eval


def fetch(url):
    import urllib.request  # import inside function -> PLC0415 (minor)
    return urllib.request.urlopen(url)  # S310 audit; B310 urllib flag


def retry(thing):
    try:
        return thing()
    except Exception:  # B902/PLW0603-style broad except -> BLE001 not selected; B902 no
        return None


try:
    os.remove(sys.argv[0])
except OSError:
    pass
