#!/usr/bin/env python3
"""Publish guard: the author attribution must be a real GitHub username.

Checks the `creator` / `maintainer` fields in SKILL.md's metadata block and
fails the build if any of them is still a placeholder, is an email address, or
is not a syntactically valid GitHub username.

This is a *semantic* check on the field values rather than a repo-wide grep for
a placeholder string. The grep version was self-defeating: the workflow file had
to contain the placeholder in order to search for it, so `grep -r` always matched
its own source and the guard could never pass.

Exits non-zero on failure so it gates the workflow. Pure stdlib -- no pip step.
"""
from __future__ import annotations

import re
import sys

# GitHub usernames: alphanumerics and single inner hyphens, 1-39 chars.
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
FIELDS = ("creator", "maintainer")


def frontmatter(path="SKILL.md"):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        sys.exit("::error::SKILL.md has no YAML frontmatter block")
    return match.group(1)


def main():
    block = frontmatter()
    errors = []

    for field in FIELDS:
        found = re.findall(r"^\s*%s:\s*(\S+)\s*$" % field, block, re.M)
        if not found:
            errors.append("metadata.%s is missing from SKILL.md" % field)
            continue
        for value in found:
            label = "metadata.%s = %r" % (field, value)
            if "TODO" in value.upper() or value.startswith("<"):
                errors.append(
                    "%s is still a placeholder -- replace it with the real "
                    "GitHub username before publishing" % label
                )
            elif "@" in value:
                errors.append(
                    "%s looks like an email address. Use the GitHub *username* "
                    "so creator_url resolves, and so a personal address is not "
                    "published" % label
                )
            elif not USERNAME_RE.match(value):
                errors.append("%s is not a valid GitHub username" % label)

    # The *_url fields must point at the same account.
    for field in FIELDS:
        names = re.findall(r"^\s*%s:\s*(\S+)\s*$" % field, block, re.M)
        urls = re.findall(r"^\s*%s_url:\s*(\S+)\s*$" % field, block, re.M)
        if names and urls:
            expected = "https://github.com/%s" % names[0]
            if urls[0] != expected:
                errors.append(
                    "metadata.%s_url is %r but should be %r"
                    % (field, urls[0], expected)
                )

    if errors:
        for error in errors:
            print("::error::%s" % error)
        return 1
    print("author attribution OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
