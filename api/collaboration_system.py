"""
Multi-User & Collaboration System for BAEL

User management, role-based access control (RBAC), team collaboration,
shared workspaces, and permission matrices.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class Role(Enum):
    """User roles in system."""
    ADMIN = "admin"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"
    GUEST = "guest"


class Permission(Enum):
    """Granular permissions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SHARE = "share"
    MANAGE_USERS = "manage_users"
    MANAGE_WORKSPACE = "manage_workspace"
    EXPORT = "export"


@dataclass
class User:
    """System user."""
    user_id: str
    username: str
    email: str
    role: Role
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    preferences: Dict = field(default_factory=dict)
    workspace_ids: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "is_active": self.is_active
        }


@dataclass
class Team:
    """User team."""
    team_id: str
    name: str
    description: str
    owner_id: str
    created_at: datetime = field(default_factory=datetime.now)
    members: Set[str] = field(default_factory=set)
    workspace_ids: Set[str] = field(default_factory=set)

    def add_member(self, user_id: str) -> None:
        """Add member to team."""
        self.members.add(user_id)

    def remove_member(self, user_id: str) -> None:
        """Remove member from team."""
        self.members.discard(user_id)

    def get_member_count(self) -> int:
        """Get number of members."""
        return len(self.members)


@dataclass
class Workspace:
    """Shared workspace."""
    workspace_id: str
    name: str
    description: str
    owner_id: str
    created_at: datetime = field(default_factory=datetime.now)
    members: Dict[str, Role] = field(default_factory=dict)
    documents: Set[str] = field(default_factory=set)
    settings: Dict = field(default_factory=dict)
    is_public: bool = False

    def add_member(self, user_id: str, role: Role) -> None:
        """Add member to workspace."""
        self.members[user_id] = role

    def remove_member(self, user_id: str) -> None:
        """Remove member from workspace."""
        if user_id in self.members:
            del self.members[user_id]

    def change_role(self, user_id: str, role: Role) -> bool:
        """Change member role."""
        if user_id in self.members:
            self.members[user_id] = role
            return True
        return False

    def get_member_count(self) -> int:
        """Get member count."""
        return len(self.members)


class RoleBasedAccessControl:
    """Role-based access control system."""

    def __init__(self):
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.ADMIN: {
                Permission.CREATE, Permission.READ, Permission.UPDATE,
                Permission.DELETE, Permission.SHARE, Permission.MANAGE_USERS,
                Permission.MANAGE_WORKSPACE, Permission.EXPORT
            },
            Role.MANAGER: {
                Permission.CREATE, Permission.READ, Permission.UPDATE,
                Permission.DELETE, Permission.SHARE, Permission.MANAGE_USERS,
                Permission.EXPORT
            },
            Role.CONTRIBUTOR: {
                Permission.CREATE, Permission.READ, Permission.UPDATE,
                Permission.SHARE, Permission.EXPORT
            },
            Role.VIEWER: {
                Permission.READ, Permission.EXPORT
            },
            Role.GUEST: {
                Permission.READ
            }
        }

    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check if role has permission."""
        return permission in self.role_permissions.get(role, set())

    def get_role_permissions(self, role: Role) -> Set[str]:
        """Get all permissions for role."""
        return {p.value for p in self.role_permissions.get(role, set())}

    def get_roles_with_permission(self, permission: Permission) -> List[Role]:
        """Get roles that have permission."""
        return [
            role for role, perms in self.role_permissions.items()
            if permission in perms
        ]


class UserManager:
    """Manages users and authentication."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.email_to_user: Dict[str, str] = {}
        self.username_to_user: Dict[str, str] = {}

    def create_user(self, username: str, email: str,
                   role: Role = Role.CONTRIBUTOR) -> User:
        """Create new user."""
        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role
        )

        self.users[user_id] = user
        self.email_to_user[email] = user_id
        self.username_to_user[username] = user_id

        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        user_id = self.email_to_user.get(email)
        return self.users.get(user_id) if user_id else None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_id = self.username_to_user.get(username)
        return self.users.get(user_id) if user_id else None

    def update_user_role(self, user_id: str, new_role: Role) -> bool:
        """Update user role."""
        if user_id in self.users:
            self.users[user_id].role = new_role
            return True
        return False

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user."""
        if user_id in self.users:
            self.users[user_id].is_active = False
            return True
        return False

    def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())

    def get_user_count(self) -> int:
        """Get total user count."""
        return len(self.users)


class TeamManager:
    """Manages teams."""

    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.user_teams: Dict[str, Set[str]] = {}

    def create_team(self, name: str, description: str, owner_id: str) -> Team:
        """Create team."""
        team_id = str(uuid.uuid4())
        team = Team(
            team_id=team_id,
            name=name,
            description=description,
            owner_id=owner_id
        )
        team.add_member(owner_id)

        self.teams[team_id] = team

        if owner_id not in self.user_teams:
            self.user_teams[owner_id] = set()
        self.user_teams[owner_id].add(team_id)

        return team

    def get_team(self, team_id: str) -> Optional[Team]:
        """Get team."""
        return self.teams.get(team_id)

    def add_team_member(self, team_id: str, user_id: str) -> bool:
        """Add member to team."""
        if team_id in self.teams:
            self.teams[team_id].add_member(user_id)

            if user_id not in self.user_teams:
                self.user_teams[user_id] = set()
            self.user_teams[user_id].add(team_id)

            return True
        return False

    def get_user_teams(self, user_id: str) -> List[Team]:
        """Get teams for user."""
        team_ids = self.user_teams.get(user_id, set())
        return [self.teams[tid] for tid in team_ids if tid in self.teams]

    def list_teams(self) -> List[Team]:
        """List all teams."""
        return list(self.teams.values())


class WorkspaceManager:
    """Manages shared workspaces."""

    def __init__(self, rbac: RoleBasedAccessControl):
        self.workspaces: Dict[str, Workspace] = {}
        self.rbac = rbac
        self.user_workspaces: Dict[str, Set[str]] = {}

    def create_workspace(self, name: str, description: str,
                        owner_id: str) -> Workspace:
        """Create workspace."""
        workspace_id = str(uuid.uuid4())
        workspace = Workspace(
            workspace_id=workspace_id,
            name=name,
            description=description,
            owner_id=owner_id
        )
        workspace.add_member(owner_id, Role.ADMIN)

        self.workspaces[workspace_id] = workspace

        if owner_id not in self.user_workspaces:
            self.user_workspaces[owner_id] = set()
        self.user_workspaces[owner_id].add(workspace_id)

        return workspace

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get workspace."""
        return self.workspaces.get(workspace_id)

    def add_member(self, workspace_id: str, user_id: str,
                   role: Role) -> bool:
        """Add member to workspace."""
        if workspace_id in self.workspaces:
            self.workspaces[workspace_id].add_member(user_id, role)

            if user_id not in self.user_workspaces:
                self.user_workspaces[user_id] = set()
            self.user_workspaces[user_id].add(workspace_id)

            return True
        return False

    def can_user_access(self, workspace_id: str, user_id: str,
                       permission: Permission) -> bool:
        """Check if user can access workspace with permission."""
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return False

        if workspace.is_public and permission == Permission.READ:
            return True

        if user_id not in workspace.members:
            return False

        user_role = workspace.members[user_id]
        return self.rbac.has_permission(user_role, permission)

    def get_user_workspaces(self, user_id: str) -> List[Workspace]:
        """Get workspaces for user."""
        workspace_ids = self.user_workspaces.get(user_id, set())
        return [self.workspaces[wid] for wid in workspace_ids
                if wid in self.workspaces]

    def list_workspaces(self) -> List[Workspace]:
        """List all workspaces."""
        return list(self.workspaces.values())


class AuditLog:
    """Tracks user actions for compliance."""

    def __init__(self):
        self.logs: List[Dict] = []

    def log_action(self, user_id: str, action: str, resource_id: str,
                   details: Optional[Dict] = None) -> None:
        """Log user action."""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource_id": resource_id,
            "details": details or {}
        })

    def get_logs(self, user_id: Optional[str] = None,
                 action: Optional[str] = None) -> List[Dict]:
        """Get audit logs."""
        filtered = self.logs

        if user_id:
            filtered = [l for l in filtered if l["user_id"] == user_id]

        if action:
            filtered = [l for l in filtered if l["action"] == action]

        return filtered

    def get_log_count(self) -> int:
        """Get total log count."""
        return len(self.logs)


class MultiUserCollaborationSystem:
    """Main multi-user collaboration orchestrator."""

    def __init__(self):
        self.rbac = RoleBasedAccessControl()
        self.user_manager = UserManager()
        self.team_manager = TeamManager()
        self.workspace_manager = WorkspaceManager(self.rbac)
        self.audit_log = AuditLog()

    def get_system_stats(self) -> Dict:
        """Get system statistics."""
        return {
            "total_users": self.user_manager.get_user_count(),
            "total_teams": len(self.team_manager.teams),
            "total_workspaces": len(self.workspace_manager.workspaces),
            "audit_logs": self.audit_log.get_log_count(),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_collab_system = None


def get_collaboration_system() -> MultiUserCollaborationSystem:
    """Get or create global collaboration system."""
    global _collab_system
    if _collab_system is None:
        _collab_system = MultiUserCollaborationSystem()
    return _collab_system
