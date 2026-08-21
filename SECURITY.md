# Security Policy

## Supported Versions

qBraid actively supports security updates for the latest minor release line of `pyqasm`:
the most recent `MAJOR.MINOR` version together with every patch release within it. For
example, if the current release is `1.2.3`, then `1.2.x` is supported and `1.1.x` is not.

Older minor lines receive fixes only where an issue is judged severe and a straightforward
backport exists.

## Reporting a Vulnerability

The qBraid team takes the security of our software seriously, across every repository in
this organization. We encourage responsible disclosure of any security vulnerability.

### How to report

Use GitHub's private security advisory form for this repository:

[Report a security vulnerability](https://github.com/qBraid/pyqasm/security/advisories/new)

Please **do not** report security vulnerabilities through public GitHub issues, pull
requests, or discussions.

### Vulnerabilities in dependencies

If an issue originates in an upstream dependency rather than in `pyqasm` itself, whether a
direct dependency or one reached through an optional extra, please report it to that
project as well and tell us here. We will assess whether users are exposed through a path
this package creates, and advise them accordingly.

### What to expect

- Acknowledgment of your report within two business days.
- An assessment of severity and scope, and a request for any further detail we need.
- Progress updates while we work on a fix.
- Notification when the issue is resolved, including the release carrying the fix, and
  credit in the advisory unless you prefer otherwise.

### What to include

- The type of issue and its impact.
- The version of `pyqasm` affected, and the Python version and platform.
- Full paths of the source files involved, if known.
- Steps to reproduce, ideally a minimal example.
- Any proof-of-concept or exploit code you are willing to share.
