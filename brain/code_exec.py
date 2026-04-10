"""Secure Python code execution within project scopes."""

import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from brain.fs import validate_path

logger = logging.getLogger("jarvis.code_exec")

def run_python(code: str, timeout: int = 30) -> str:
    """Execute arbitrary Python code and return stdout/stderr."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tf:
        tf.write(code.encode("utf-8"))
        temp_path = tf.name

    try:
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        return output if output else "(No output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: Execution timed out after {timeout} seconds."
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        try:
            Path(temp_path).unlink()
        except:
            pass

def run_python_file(path: str, timeout: int = 30) -> str:
    """Execute a Python file within a project scope."""
    valid_path = validate_path(path)
    if not valid_path:
        return "ERROR: Access denied. File must be within a registered project."
    
    if valid_path.suffix != ".py":
        return "ERROR: Only .py files can be executed."

    try:
        result = subprocess.run(
            [sys.executable, str(valid_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(valid_path.parent)
        )
        output = result.stdout + result.stderr
        return output if output else "(No output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: Execution timed out after {timeout} seconds."
    except Exception as e:
        return f"ERROR: {e}"
