"""Authentication: password hashing, session cookies, password reset, roles.

Design notes (WP 0.3):

- Sessions are server-side rows (``sessions`` table) keyed by the SHA-256
  hash of an opaque token; the raw token lives only in an HttpOnly cookie.
- A user row is per-org (email unique per org, not globally), so a session
  pins both identity and organisation. One email in several orgs = several
  user rows; login for such an email requires ``org_slug`` to disambiguate
  (deterministic, documented behaviour — an org-switcher endpoint can come
  later by just creating a session for the sibling user row).
- ``repositories.deps.get_current_org_id`` resolves from the session cookie,
  so every OrgContext-scoped repository is auth-derived.
"""

from autoinsight.auth.passwords import hash_password, verify_password
from autoinsight.auth.service import AuthService

__all__ = ["AuthService", "hash_password", "verify_password"]
