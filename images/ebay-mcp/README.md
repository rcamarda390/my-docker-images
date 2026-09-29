# eBay MCP image

Builds the unofficial [YosefHayim/ebay-mcp](https://github.com/YosefHayim/ebay-mcp)
HTTP server from a pinned release tag and commit. The image contains all Node.js
dependencies and does not download packages at runtime. It still requires network
access to the configured eBay APIs.

## Runtime

The container listens on port `3000` and exposes:

- MCP: `http://HOST:3000/`
- Health: `http://HOST:3000/health`

Credentials must be supplied at runtime. Do not bake them into the image.

```sh
docker run --rm \
  --name ebay-mcp \
  -p 127.0.0.1:3000:3000 \
  -e EBAY_CLIENT_ID \
  -e EBAY_CLIENT_SECRET \
  -e EBAY_REDIRECT_URI \
  -e EBAY_USER_REFRESH_TOKEN \
  -e EBAY_ENVIRONMENT=sandbox \
  -e EBAY_MCP_TOOLS=browse,inventory,analytics,communication,fulfillment,developer \
  -e EBAY_READ_ONLY=true \
  -e MCP_AUTH_TOKEN \
  ghcr.io/rcamarda390/ebay-mcp:1.16.0-v1
```

Start in eBay sandbox with `EBAY_READ_ONLY=true`. Remove read-only mode only
after validating the account, marketplace, exposed tool families, and approval
process for mutations. Use `MCP_AUTH_TOKEN` whenever the HTTP endpoint is
reachable by anything other than a trusted loopback client.

The application can also read and update `/app/.env`. If file-based token
persistence is required, bind-mount a pre-created, owner-writable file there;
runtime environment variables are preferred for container deployments.

Local media access is disabled unless `EBAY_MCP_MEDIA_DIRS` or
`EBAY_MCP_MEDIA_ROOT` names a mounted directory.
