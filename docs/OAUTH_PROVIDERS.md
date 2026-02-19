OAuth providers and free-token usage
=================================

This project includes a minimal OAuth helper to allow using OAuth-based provider tokens
for free or low-cost provider tiers (refresh-token and client_credentials flows).

Supported environment variables (Google example):

- `GOOGLE_CLIENT_ID` - OAuth client id
- `GOOGLE_CLIENT_SECRET` - OAuth client secret
- `GOOGLE_REFRESH_TOKEN` - Refresh token (if using refresh flow)
- `GOOGLE_TOKEN_URL` - Token endpoint (defaults to https://oauth2.googleapis.com/token)
- `GOOGLE_API_BASE` - API base URL (defaults to https://gemini.googleapis.com/v1)
- `GOOGLE_OAUTH_CACHE` - Path to cache file for tokens (defaults to `.cache/google_oauth.json`)

Notes:

- The helper uses `aiohttp` for token HTTP calls. Install dependencies with:

```bash
pip install aiohttp
```

- The included `OAuthTokenManager` will attempt to load a cached token, refresh using a
  `refresh_token` if provided, or fall back to `client_credentials` if available.

- The `GoogleProvider` in `core/supreme/llm_providers.py` demonstrates how to integrate
  the OAuth manager. Provider initialization will skip providers that cannot obtain tokens.

Security:

- Store client secrets and refresh tokens securely (not in public repos). Use environment
  variables or a secrets manager in production.
