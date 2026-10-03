def folder_activity_timestamps(folders, direct_activity: dict[str, int]) -> dict[str, int]:
    """Roll chat activity up ancestors, using creation time only for empty subtrees."""
    parents = {folder['id']: folder.get('parent_id') for folder in folders}
    activity = {}
    for folder_id, timestamp in direct_activity.items():
        seen = set()
        while folder_id in parents and folder_id not in seen:
            seen.add(folder_id)
            activity[folder_id] = max(activity.get(folder_id, 0), timestamp)
            folder_id = parents[folder_id]
    return {
        folder['id']: activity.get(folder['id'], folder.get('created_at') or 0)
        for folder in folders
    }
