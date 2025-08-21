import json

from search import handler


def pretty(obj):
    print(json.dumps(obj, indent=2))


def main():
    print("=== GET /api/search ===")
    res_get = handler({"method": "GET", "headers": {}, "query": {}})
    pretty(res_get)

    print("\n=== POST /api/search ===")
    body = {
        "query": "remote work policy",
        "filters": {"department": "HR"},
        "hybridWeight": 0.5,
    }
    res_post = handler(
        {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body).encode("utf-8"),
            "query": {},
        }
    )
    pretty(res_post)


if __name__ == "__main__":
    main()
