# raphael-analytics

Usage, business, and organizational intelligence

## API

- Prefix: `/v1/analytics`
- Port: `8105`
- Health: `GET /health`

## Events

_Published and consumed events documented in `openapi.yaml` and raphael-contracts._

## Development

```bash
uv sync
uv run uvicorn raphael_analytics.app:app --reload --port 8105
```

Part of the [Raphael Platform](https://github.com/hummingbird-labs) by HummingBird Labs.
