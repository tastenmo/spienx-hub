# Django Guardian Permission Simplification

## Summary of Changes

This update refactors the accounts app to use **django-guardian** for simplified, object-level permission management instead of custom role fields.

### Key Changes:

#### 1. **Dependencies** (`pyproject.toml`)
- Added `django-guardian = "^2.4.0"`

#### 2. **Models** (`src/accounts/models.py`)
- **Removed** hardcoded `PERMISSION_CHOICES`
- **Added** `PERMISSIONS` dict mapping permission levels to Django permission codenames
- **Organisation model**:
  - New methods: `grant_permission()` and `user_permission()` for guardian integration
  - Removed custom permission fields (handled via guardian)
- **OrganisationMembership model**:
  - Removed redundant role storage; role is stored in `role` field but synced to guardian permissions on save
  - Added `save()` override to sync with guardian permissions
- **UserProfile model**:
  - Removed custom `role` field (now managed via OrganisationMembership)
- **OrganisationInvite model**:
  - Updated ROLE_CHOICES locally (kept for invite workflow)

#### 3. **Settings** (`src/config/settings.py`)
- Added `'guardian'` to `INSTALLED_APPS`
- Added Guardian backend to `AUTHENTICATION_BACKENDS`:
  ```python
  AUTHENTICATION_BACKENDS = [
      'django.contrib.auth.backends.ModelBackend',
      'guardian.backends.ObjectPermissionBackend',
      'allauth.account.auth_backends.AuthenticationBackend',
  ]
  ```

### How It Works:

**Before:** Permission levels stored as text fields on multiple models  
**After:** Permissions managed via Django's permission framework + guardian

1. User's role in `OrganisationMembership` is stored as text ('read', 'write', 'admin')
2. On save, the membership syncs the role to guardian object-level permissions
3. Permission checks: `has_perm(user, 'accounts.view_organisation', org_obj)`
4. Helper methods on Organisation handle grant/revoke in one place

### Benefits:

✅ Centralized permission logic (no duplicated role fields)  
✅ Uses Django's standard permission system  
✅ Object-level permissions (per-org, per-repo granularity)  
✅ Easier auditing via django-admin  
✅ Scales better for complex permission hierarchies  

### Next Steps:

1. Install dependencies: `poetry install`
2. Create migrations: `poetry run python manage.py makemigrations`
3. Apply migrations: `poetry run python manage.py migrate`
4. Update views/serializers to use `has_perm()` instead of checking role strings

### Permission Mapping:

| Level | Codename |
|-------|----------|
| read  | view     |
| write | change   |
| admin | delete   |
