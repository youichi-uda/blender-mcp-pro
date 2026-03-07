"""Blender addon handler for Python code execution."""

import io
import sys
import traceback
import math
import os

import bpy
import mathutils


def execute_python(code: str) -> dict:
    """Execute arbitrary Python code in Blender's context.

    Args:
        code: Python source code to execute.

    Returns:
        dict with stdout, stderr, and optional result.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    namespace = {
        "bpy": bpy,
        "mathutils": mathutils,
        "math": math,
        "os": os,
    }

    result = None

    try:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            exec(code, namespace)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        if "__result__" in namespace:
            result = namespace["__result__"]

        response = {
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
        }

        if result is not None:
            response["result"] = result

        return response

    except Exception:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        tb = traceback.format_exc()
        hint = _get_error_hint(tb)

        response = {
            "stdout": stdout_capture.getvalue(),
            "stderr": stderr_capture.getvalue(),
            "error": tb,
        }

        if hint:
            response["hint"] = hint

        return response


def _get_error_hint(error_text: str) -> str:
    """Return a helpful hint based on the error type.

    Args:
        error_text: The full traceback string.

    Returns:
        A hint string, or empty string if no matching hint.
    """
    if "poll() failed" in error_text:
        return (
            "The operation requires specific context. "
            "Try selecting the object first or changing mode."
        )
    if "not found" in error_text:
        return (
            "The named item doesn't exist. "
            "Use get_scene_info() to see available objects."
        )
    if "restricted context" in error_text:
        return (
            "This operation can't run from a background thread. "
            "Use dedicated tools instead."
        )
    return ""


HANDLERS = {
    "execute_python": execute_python,
}
