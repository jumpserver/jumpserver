import os


def fs_standard_access(attr, path, volume):
    """
    Make dotfiles not readable, not writable, hidden and locked.
    Should return None to allow for original attribute value, boolean otherwise.
    This can be used in the :ref:`setting-accessControl` setting.
    
    Args:
        :attr: One of `read`, `write`, `hidden` and `locked`.
        :path: The path to check against.
        :volume: The volume responsible for managing the path.

    Returns:
        ``True`` if `path` has `attr` permissions, ``False`` if not and
        ``None`` to apply the default permission rules.
    """

    if os.path.basename(path) in ['.tmb', '.quarantine']:
        #keep reserved folder names intact
        return None

    if volume.name() == 'localfilesystem':
        if attr in ['read', 'write'] and os.path.basename(path).startswith('.'):
            return False
        elif attr in ['hidden', 'locked'] and os.path.basename(path).startswith('.'):
            return True
