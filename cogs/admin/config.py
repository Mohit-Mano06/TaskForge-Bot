DEV_GUILD_ID = 1470000357332484164
ANNOUNCEMENT_CHANNEL_ID = 1091579772213153863
OWNER_IDS = {450626076079554573}
OWNER_ID = next(iter(OWNER_IDS))

# Keep admin roles centralized so bot-level admin checks stay consistent.
ADMIN_ROLE_IDS = {
    1471835077787783270,
    1470002009812766751,
}


def user_has_admin_access(user, *, include_owner=True):
    if include_owner and user and user.id in OWNER_IDS:
        return True
    if not user:
        return False
    return any(getattr(role, "id", None) in ADMIN_ROLE_IDS for role in getattr(user, "roles", []))


def user_is_owner(user):
    return bool(user) and user.id in OWNER_IDS
