# Builtin tools package
from ..registry import registry
from .user_profiler import UserProfiler

# Auto-register all builtin tools
registry.auto_register(UserProfiler)
