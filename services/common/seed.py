"""Seed data shared by the services, so that services which share it always agree."""

CATALOG = {
    "SKU-001": {"name": "Mechanical Keyboard", "price": 89.00, "stock": 12},
    "SKU-002": {"name": "Wireless Mouse", "price": 19.99, "stock": 42},
    "SKU-003": {"name": "USB-C Hub", "price": 34.50, "stock": 7},
    "SKU-004": {"name": "27-inch Monitor", "price": 229.00, "stock": 0},
    "SKU-005": {"name": "Laptop Stand", "price": 24.90, "stock": 130},
}
SKUS = list(CATALOG)
CURRENCY = "EUR"

POSTS = [
    {
        "id": 1,
        "title": "Why we put a gateway in front of everything",
        "author": "Ada Lovelace",
        "published_at": "2026-01-05T09:00:00Z",
        "summary": "One front door beats many side doors.",
        "body": "A gateway gives every request the same front door, so authentication, "
        "rate limiting and routing live in one place instead of in every service.",
    },
    {
        "id": 2,
        "title": "Routing by path, rewriting on the way",
        "author": "Grace Hopper",
        "published_at": "2026-01-12T09:00:00Z",
        "summary": "Public paths do not have to match service paths.",
        "body": "The public path /blog/posts reaches the blog service as /posts. "
        "The prefix is a public concern and the service never needs to know it.",
    },
    {
        "id": 3,
        "title": "Tokens, claims and trust",
        "author": "Alan Turing",
        "published_at": "2026-01-19T09:00:00Z",
        "summary": "Verify once at the edge, pass on only what is needed.",
        "body": "The gateway verifies the JWT and forwards only the user id and email. "
        "Services trust those two headers because nothing else can reach them.",
    },
    {
        "id": 4,
        "title": "Rate limits that protect the login form",
        "author": "Edsger Dijkstra",
        "published_at": "2026-01-26T09:00:00Z",
        "summary": "Brute force is cheap unless you make it expensive.",
        "body": "A tight limit on the login endpoint turns password guessing from a "
        "minute of work into a month of work.",
    },
    {
        "id": 5,
        "title": "Canary releases with weighted routes",
        "author": "Barbara Liskov",
        "published_at": "2026-02-02T09:00:00Z",
        "summary": "Send ten percent of traffic to the new version first.",
        "body": "Two versions of one service run side by side. The gateway sends a small "
        "share of requests to the new one and the response headers show which answered.",
    },
]
