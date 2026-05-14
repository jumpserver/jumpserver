#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: validate_custom_script_path
short_description: Validate custom automation script path under allowed root
description:
  - Resolves C(path) with C(os.path.realpath), requires a regular readable file, and checks that it
    lies under the allowed directory prefix (also resolved).
  - Intended for local execution of interpreter-driven scripts (e.g. C(python <path> ...)); does not
    require a C(.py) suffix.
  - Returns C(resolved_path) only; the playbook should build C(argv) (e.g. interpreter + path + extras).
options:
  path:
    description: Absolute path to the script file (symlinks resolved).
    type: str
    required: true
  allowed_root:
    description: Allowed directory prefix for the script, typically from JumpServer C(CUSTOM_SCRIPT_ROOT).
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Validate custom script path
  validate_custom_script_path:
    path: "{{ params.script_path }}"
    allowed_root: "{{ custom_script_root }}"
  register: website_script_path
"""

RETURN = r"""
resolved_path:
  description: Canonical script path after symlink resolution.
  returned: success
  type: str
"""

import os

from ansible.module_utils.basic import AnsibleModule


def _resolve_root(raw_root):
    root = (raw_root or "").strip()
    if not root:
        raise ValueError("allowed_root must be a non-empty string")
    return os.path.realpath(os.path.expanduser(root))


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            allowed_root=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )
    raw_path = module.params["path"] or ""
    path = raw_path.strip()
    if not path:
        module.fail_json(msg="path must be a non-empty string")

    try:
        root = _resolve_root(module.params["allowed_root"])
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    try:
        resolved = os.path.realpath(os.path.expanduser(path))
    except Exception as exc:
        module.fail_json(msg="cannot resolve path: %s" % (exc,))

    if not os.path.isfile(resolved):
        module.fail_json(
            msg="path is not a regular file (after symlink resolution): %s" % (resolved,),
        )

    if not os.access(resolved, os.R_OK):
        module.fail_json(msg="script is not readable: %s" % (resolved,))

    if resolved != root and not resolved.startswith(root + os.sep):
        module.fail_json(
            msg="path %s is not under allowed root %s" % (resolved, root),
        )

    module.exit_json(changed=False, resolved_path=resolved)


if __name__ == "__main__":
    main()
