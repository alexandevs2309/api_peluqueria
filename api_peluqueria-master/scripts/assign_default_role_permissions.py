from apps.roles_api.default_permissions import sync_all_default_role_permissions


synced = sync_all_default_role_permissions()

if not synced:
    print("No system roles found to sync")
else:
    total = sum(synced.values())
    for role_name, count in synced.items():
        print(f"{role_name}: {count} permissions assigned")
    print(f"\nTotal assigned: {total}")
