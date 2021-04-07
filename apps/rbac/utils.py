

def convert_action(view_action):
    if view_action in ['create']:
        return 'add'
    if view_action in ['list', 'retrieve']:
        return 'view'
    if view_action in ['update', 'partial_update', 'bulk_update', 'partial_bulk_update']:
        return 'change'
    if view_action in ['destroy', 'bulk_destroy']:
        return 'delete'
    return view_action
