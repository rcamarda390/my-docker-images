"""Hide search_docs' query_embedding parameter from the MCP tool schema.

gnosis-mcp 0.17.5 exposes `query_embedding: list[float] | None` on the
search_docs tool. LLM clients (Cline) read it as "supply an embedding vector"
and stall, emit number soup or fail the call. The server embeds the query
itself (GNOSIS_MCP_EMBED_PROVIDER=local), so no client should send one.
The parameter becomes a local that stays None; the search code path is unchanged.

Usage: hide-query-embedding.py [path/to/gnosis_mcp/server.py]
"""
import ast
import importlib.util
import sys

path = sys.argv[1] if len(sys.argv) > 1 else (
    importlib.util.find_spec("gnosis_mcp").submodule_search_locations[0] + "/server.py"
)
src = open(path).read()


def sub(old, new):
    global src
    assert src.count(old) == 1, f"patch anchor not found exactly once (upstream changed?): {old!r}"
    src = src.replace(old, new)


sub(
    "    limit: int = 5,\n    query_embedding: list[float] | None = None,\n    rerank: bool | None = None,\n) -> str:",
    "    limit: int = 5,\n    rerank: bool | None = None,\n) -> str:",
)
sub(
    "        query_embedding: Optional pre-computed embedding vector for hybrid search.\n"
    "            When provided, combines keyword (tsvector) and semantic (cosine) scoring.\n",
    "",
)
sub(
    '`GNOSIS_MCP_RERANK_ENABLED`. Requires the [reranking] extra.\n    """\n    ctx = await _get_ctx()\n',
    '`GNOSIS_MCP_RERANK_ENABLED`. Requires the [reranking] extra.\n    """\n'
    "    query_embedding: list[float] | None = None  # hidden from the tool schema; server embeds locally\n"
    "    ctx = await _get_ctx()\n",
)

fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.AsyncFunctionDef) and n.name == "search_docs")
assert "query_embedding" not in [a.arg for a in fn.args.args], "query_embedding still in search_docs signature"
open(path, "w").write(src)
print("patched", path)
