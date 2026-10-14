# patch-litellm-jwt-email.py
"""CVE-2026-93355 carry. Identical in both image contexts; no extra dependency."""
import argparse
import ast
import asyncio
import copy
import __future__
from pathlib import Path
from types import SimpleNamespace


MARKER = "# ponytail: CVE-2026-93355; retire when upstream verifies JWT email."


def method(source, class_name, name):
    tree = ast.parse(source)
    owner, = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name]
    node, = [node for node in owner.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    return node


def verify(source, auth_source):
    # Execute the installed methods' actual code; isolate provider/database imports.
    email = copy.deepcopy(method(source, "JWTHandler", "get_user_email"))
    info = copy.deepcopy(method(source, "JWTAuthManager", "get_user_info"))
    email.decorator_list = []
    info.decorator_list = []

    def nested(data, key_path, default):
        for part in key_path.split("."):
            if not isinstance(data, dict) or part not in data:
                return default
            data = data[part]
        return data

    fuzzy, = [node for node in ast.parse(auth_source).body
              if isinstance(node, ast.AsyncFunctionDef) and node.name == "_get_fuzzy_user_object"]
    fuzzy.decorator_list = []

    class Users:
        def __init__(self):
            self.email_lookups = 0
            self.bindings = []

        async def find_unique(self, **kwargs):
            return None

        async def find_first(self, **kwargs):
            self.email_lookups += 1
            return SimpleNamespace(user_id="victim")

        async def update(self, **kwargs):
            self.bindings.append(kwargs)

    users = Users()
    namespace = {"get_nested_value": nested, "asyncio": asyncio,
                 "_user_table": lambda repo: users, "UserRepository": lambda client: SimpleNamespace(table=users)}
    module = ast.Module(body=[email, info, fuzzy], type_ignores=[])
    exec(compile(module, "<installed JWT email methods>", "exec",
                 flags=__future__.annotations.compiler_flag), namespace)

    class Handler:
        LITELLM_USER_EMAIL_CLAIM = "_litellm_user_email"
        litellm_jwtauth = SimpleNamespace(user_email_jwt_field="email")
        get_user_email = namespace["get_user_email"]

        def _has_trusted_issuer_normalized_claim(self, token, claim):
            return token.get("trusted") is True and claim in token

        def is_enforced_email_domain(self):
            return False

        def get_user_id(self, token, default_value):
            return token.get("sub", default_value)

    async def check():
        handler = Handler()
        for value in (None, False, "true", "false", 0, 1, {}, []):
            token = {"email": "victim@example.org"}
            if value is not None:
                token["email_verified"] = value
            assert handler.get_user_email(token, "unsafe-default") is None
            assert await namespace["get_user_info"](handler, token) == (None, None, None)
            token["sub"] = "attacker-subject"
            assert await namespace["get_user_info"](handler, token) == ("attacker-subject", None, None)
            user_id, user_email, _ = await namespace["get_user_info"](handler, token)
            assert await namespace["_get_fuzzy_user_object"](None, sso_user_id=user_id, user_email=user_email) is None
            await asyncio.sleep(0)
            assert users.email_lookups == 0 and users.bindings == []
            token.update(trusted=True, _litellm_user_email="victim@example.org")
            assert handler.get_user_email(token, None) is None

        verified = {"email": "valid@example.org", "email_verified": True}
        assert await namespace["get_user_info"](handler, verified) == ("valid@example.org", "valid@example.org", None)
        verified["sub"] = "valid-subject"
        user_id, user_email, _ = await namespace["get_user_info"](handler, verified)
        linked = await namespace["_get_fuzzy_user_object"](None, sso_user_id=user_id, user_email=user_email)
        await asyncio.sleep(0)
        assert linked.user_id == "victim" and users.email_lookups == 1
        assert users.bindings[0]["data"] == {"sso_user_id": "valid-subject"}
        assert await namespace["get_user_info"](handler, verified) == ("valid-subject", "valid@example.org", None)
        assert await namespace["get_user_info"](handler, {"sub": "subject-only"}) == ("subject-only", None, None)
        handler.litellm_jwtauth = SimpleNamespace(user_email_jwt_field="profile.email")
        assert handler.get_user_email({"profile": {"email": "nested@example.org"}, "email_verified": True}, None) == "nested@example.org"
        assert handler.get_user_email({"profile": {"email": "nested@example.org"}}, None) is None

    asyncio.run(check())
    print("CVE-2026-93355: unverified email fallback blocked; verified email and subject identity preserved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    source = args.source.read_text()
    auth_source = args.source.with_name("auth_checks.py").read_text()
    if not args.verify:
        assert MARKER not in source, "Already patched"
        node = method(source, "JWTHandler", "get_user_email")
        # Both pinned releases must retain the reviewed normalized/email field paths.
        body = ast.get_source_segment(source, node)
        assert "LITELLM_USER_EMAIL_CLAIM" in body and "user_email_jwt_field" in body
        lines = source.splitlines(keepends=True)
        lines.insert(node.body[0].lineno - 1,
                     "        " + MARKER + "\n"
                     "        if token.get(\"email_verified\") is not True:\n"
                     "            return None\n")
        source = "".join(lines)
        compile(source, str(args.source), "exec")
        verify(source, auth_source)
        args.source.write_text(source)
    else:
        assert MARKER in source, "Missing JWT email verification patch"
        verify(source, auth_source)


if __name__ == "__main__":
    main()
