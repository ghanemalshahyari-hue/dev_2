"""
LDAP Client Module — Enterprise Authentication

Handles LDAP authentication (Active Directory / OpenLDAP).
In LDAP_SIMULATION_MODE=True it authenticates test accounts locally.
"""

from __future__ import annotations
from typing import Optional, Tuple
from dataclasses import dataclass, field

from flask import current_app


@dataclass
class LDAPUser:
    """User record returned from LDAP directory."""

    dn:         str
    username:   str
    email:      str
    full_name:  str
    groups:     list = field(default_factory=list)
    department: Optional[str] = None
    title:      Optional[str] = None


# ─── Test accounts for simulation mode ────────────────────────────────────────
_SIMULATION_USERS = {
    'dev': {
        'password':  'dev123',
        'email':     'dev@company.local',
        'full_name': 'المطور / Developer',
        'role_code': 'DEVELOPER',
        'department': 'التطوير',
    },
    'director': {
        'password':  'director123',
        'email':     'director@company.local',
        'full_name': 'المدير العام',
        'role_code': 'DIRECTOR',
        'department': 'الإدارة',
    },
    'secretary': {
        'password':  'secretary123',
        'email':     'secretary@company.local',
        'full_name': 'السكرتير',
        'role_code': 'SECRETARY',
        'department': 'الإدارة',
    },
    'deputy': {
        'password':  'deputy123',
        'email':     'deputy@company.local',
        'full_name': 'نائب المدير',
        'role_code': 'DEPUTY',
        'department': 'الإدارة',
    },
    'groupadmin': {
        'password':  'groupadmin123',
        'email':     'groupadmin@company.local',
        'full_name': 'مدير المجموعة الأولى',
        'role_code': 'GROUP_ADMIN',
        'department': 'GRP1',
    },
    'user': {
        'password':  'user123',
        'email':     'user@company.local',
        'full_name': 'مستخدم عادي',
        'role_code': 'USER',
        'department': 'GRP1',
    },
}


class LDAPClient:
    """
    LDAP authentication client.

    Supports:
    - Active Directory (sAMAccountName)
    - OpenLDAP
    - Simulation mode for development (LDAP_SIMULATION_MODE=True)
    """

    def __init__(self) -> None:
        self.server        = current_app.config.get('LDAP_SERVER')
        self.base_dn       = current_app.config.get('LDAP_BASE_DN')
        self.bind_dn       = current_app.config.get('LDAP_BIND_DN')
        self.bind_password = current_app.config.get('LDAP_BIND_PASSWORD')
        self.search_base   = current_app.config.get('LDAP_USER_SEARCH_BASE')
        self.search_filter = current_app.config.get('LDAP_USER_SEARCH_FILTER')
        self.use_ssl       = current_app.config.get('LDAP_USE_SSL', True)
        self.sim_mode      = current_app.config.get('LDAP_SIMULATION_MODE', False)

    def authenticate(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[LDAPUser], str]:
        """
        Authenticate user credentials.

        Returns:
            (success, LDAPUser|None, error_message)
        """
        if self.sim_mode:
            return self._simulate(username, password)
        return self._ldap_auth(username, password)

    # ── Simulation mode ───────────────────────────────────────────────────────

    def _simulate(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[LDAPUser], str]:
        """Authenticate against in-memory test accounts."""
        key = username.strip().lower()
        data = _SIMULATION_USERS.get(key)

        if data is None:
            return False, None, 'User not found'

        if password != data['password']:
            return False, None, 'Invalid credentials'

        ldap_user = LDAPUser(
            dn        = f'CN={username},OU=Users,DC=company,DC=local',
            username  = key,
            email     = data['email'],
            full_name = data['full_name'],
            groups    = [f'CN={data["role_code"]},OU=Groups,DC=company,DC=local'],
            department = data.get('department'),
        )
        return True, ldap_user, ''

    # ── Real LDAP authentication ──────────────────────────────────────────────

    def _ldap_auth(
        self, username: str, password: str
    ) -> Tuple[bool, Optional[LDAPUser], str]:
        """Perform actual LDAP bind against the directory server."""
        try:
            from ldap3 import Server, Connection, ALL, SIMPLE
            from ldap3.core.exceptions import LDAPBindError, LDAPException

            server = Server(self.server, get_info=ALL, use_ssl=self.use_ssl)

            # ── Step 1: Find user DN via service account ──
            if self.bind_dn and self.bind_password:
                svc = Connection(
                    server,
                    user=self.bind_dn,
                    password=self.bind_password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )
                full_base   = f'{self.search_base},{self.base_dn}'
                user_filter = self.search_filter.format(username=username)
                svc.search(
                    search_base=full_base,
                    search_filter=user_filter,
                    attributes=[
                        'distinguishedName', 'sAMAccountName', 'mail',
                        'displayName', 'memberOf', 'department', 'title',
                    ],
                )
                if not svc.entries:
                    svc.unbind()
                    return False, None, 'User not found in directory'
                entry    = svc.entries[0]
                user_dn  = str(entry.distinguishedName)
                svc.unbind()
            else:
                user_dn = f'cn={username},{self.search_base},{self.base_dn}'

            # ── Step 2: Bind as user to verify password ──
            try:
                conn = Connection(
                    server,
                    user=user_dn,
                    password=password,
                    authentication=SIMPLE,
                    auto_bind=True,
                )
            except LDAPBindError:
                return False, None, 'Invalid credentials'

            # ── Step 3: Fetch full attributes ──
            conn.search(
                search_base=user_dn,
                search_filter='(objectClass=*)',
                attributes=[
                    'sAMAccountName', 'mail', 'displayName',
                    'memberOf', 'department', 'title',
                ],
            )

            if conn.entries:
                e = conn.entries[0]
                ldap_user = LDAPUser(
                    dn        = user_dn,
                    username  = str(e.sAMAccountName) if e.sAMAccountName else username,
                    email     = str(e.mail) if e.mail else f'{username}@company.local',
                    full_name = str(e.displayName) if e.displayName else username,
                    groups    = list(e.memberOf)  if e.memberOf   else [],
                    department = str(e.department) if e.department else None,
                    title     = str(e.title)       if e.title      else None,
                )
            else:
                ldap_user = LDAPUser(
                    dn=user_dn, username=username,
                    email=f'{username}@company.local', full_name=username,
                )

            conn.unbind()
            return True, ldap_user, ''

        except LDAPBindError:
            return False, None, 'Invalid credentials'
        except Exception as exc:
            current_app.logger.error(f'LDAP error: {exc}')
            return False, None, 'Authentication service unavailable'

    # ── Connectivity test ─────────────────────────────────────────────────────

    def test_connection(self) -> Tuple[bool, str]:
        """Quick connectivity check — used by the login page status indicator."""
        if self.sim_mode:
            return True, 'Simulation mode active'
        try:
            from ldap3 import Server, Connection, ALL
            s = Server(self.server, get_info=ALL, use_ssl=self.use_ssl)
            c = Connection(s, auto_bind=True)
            c.unbind()
            return True, 'Connected'
        except Exception as exc:
            return False, f'Unreachable: {exc}'


def get_ldap_client() -> LDAPClient:
    """Factory — returns a configured LDAPClient for the current app context."""
    return LDAPClient()
