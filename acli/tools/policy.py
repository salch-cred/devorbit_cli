"""Permission policy helpers for files and network/browser domains."""
import fnmatch
from urllib.parse import urlparse


class PermissionDenied(Exception):
    pass


def domain_matches(host, rule):
    host = (host or "").lower().strip(".")
    rule = (rule or "").lower().strip().strip(".")
    if not rule:
        return False
    if rule.startswith("*."):
        rule = rule[2:]
    return host == rule or host.endswith("." + rule)


def ensure_network_allowed(url, settings, browser_actuation=False):
    host = urlparse(url).hostname or ""
    denied = list(getattr(settings, "denied_domains", []) or [])
    allowed = list(getattr(settings, "allowed_domains", []) or [])
    default = getattr(settings, "network_default", "allow")
    if browser_actuation:
        denied += list(getattr(settings, "browser_denied_domains", []) or [])
        browser_allowed = list(getattr(settings, "browser_allowed_domains", []) or [])
        if browser_allowed:
            allowed = browser_allowed
    if any(domain_matches(host, rule) for rule in denied):
        raise PermissionDenied("Network access denied for domain: " + host)
    if allowed and not any(domain_matches(host, rule) for rule in allowed):
        raise PermissionDenied("Domain is not on the allow list: " + host)
    if str(default).lower() == "deny" and not any(domain_matches(host, rule) for rule in allowed):
        raise PermissionDenied("Network default is deny; add this domain to permissions.allowed_domains: " + host)


def ensure_file_allowed(relative_path, settings, write=False):
    if settings is None:
        return
    if write and not getattr(settings, "allow_file_writes", True):
        raise PermissionDenied("File writes are disabled in Settings > Permissions")
    if not write and not getattr(settings, "allow_file_reads", True):
        raise PermissionDenied("File reads are disabled in Settings > Permissions")
    normalized = str(relative_path).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    basename = normalized.rsplit("/", 1)[-1]
    patterns = getattr(settings, "denied_file_patterns", []) or []
    for pattern in patterns:
        if fnmatch.fnmatch(normalized.lower(), str(pattern).lower()) or fnmatch.fnmatch(basename.lower(), str(pattern).lower()):
            raise PermissionDenied("File path is denied by pattern '" + str(pattern) + "': " + relative_path)
