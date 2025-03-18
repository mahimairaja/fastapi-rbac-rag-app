# Define roles and their permissions
# Resource types: "user", "document", "rag"

# Admin role can do anything
allow(user: User, _action, _resource) if
    user.role = "admin";

# User permissions
# Users can read and update their own profiles
allow(user: User, "read", resource: User) if
    user.id = resource.id;

allow(user: User, "update", resource: User) if
    user.id = resource.id;

# Users can read and search documents
allow(user: User, "read", _resource) if
    user.is_active = true and
    _resource = "document";

allow(user: User, "search", _resource) if
    user.is_active = true and
    _resource = "document";

# RAG permissions - all active users can use the RAG service
allow(user: User, "use", _resource) if
    user.is_active = true and
    _resource = "rag";

# Moderator role permissions
# Moderators can read all user profiles
allow(user: User, "read", _resource: User) if
    user.role = "moderator";

# Moderators can upload documents
allow(user: User, "upload", _resource) if
    (user.role = "moderator" or user.role = "admin") and
    _resource = "document";

# Role management - only admin can update roles
allow(user: User, "update", _resource) if
    user.role = "admin" and
    _resource = "user_role";

# Default deny - if no rule matches, access is denied 