"""AskTrabaajo canonical backend package (v2.0 foundation).

This package is the single authoritative backend. It does not import from
the legacy ``backend.api`` tree (migration source only) and is safe to
import alongside it during the strangler migration.
"""

__version__ = "0.3.0"
