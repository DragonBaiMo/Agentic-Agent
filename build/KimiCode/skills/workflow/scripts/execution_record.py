"""SPDX-License-Identifier: MIT

Record caller-visible image arguments separately from the immutable prepared job.
The public evidence does not prove backend reference binding or hidden prompts.
"""

from pathlib import Path

from project_io import digest, read_json


def public_arguments(file):
    """Validate a narrow public-argument file and hash real reference attachments.

    Paths resolve relative to this JSON. Unknown fields are rejected to prevent
    accidentally packaging credentials or an entire tool response.
    """
    file = Path(file)
    value = read_json(file)
    allowed = {"prompt", "referenced_image_paths", "transparent_background"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("execution_public_fields_only")
    if not isinstance(value.get("prompt"), str) or not value["prompt"].strip():
        raise ValueError("execution_prompt_required")
    if type(value.get("transparent_background")) is not bool:
        raise ValueError("execution_transparency_required")
    paths = value.get("referenced_image_paths", [])
    if not isinstance(paths, list) or any(not isinstance(path, str) for path in paths):
        raise ValueError("execution_reference_paths")
    references = []
    for relative in paths:
        source = (file.parent / relative).resolve()
        if not source.is_file():
            raise ValueError("execution_reference_missing")
        # NOTE: Retain content identity, not a machine-specific absolute path.
        references.append({"name": source.name, "sha256": digest(source)})
    return {"submitted_prompt": value["prompt"], "submitted_references": references,
            "submitted_transparent_background": value["transparent_background"],
            "evidence_source": "caller_reported_public_arguments"}


def execution_result(source, origin, tool, call_id, public_file=None):
    """Describe the returned/imported bytes; missing call metadata stays unknown."""
    result = {"status": "result_recorded", "origin": origin, "tool": tool,
              "call_id": call_id, "result_sha256": digest(source),
              "public_arguments": "not_recorded", "backend_binding_observed": "not_exposed",
              "effective_backend_prompt": "not_exposed"}
    if public_file is not None:
        if origin != "generated":
            raise ValueError("execution_arguments_require_generated_origin")
        result["public_arguments"] = public_arguments(public_file)
    return result
