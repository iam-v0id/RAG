# Minimal test function for Vercel
def handler(request):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": '{"message": "Hello from Vercel Python!"}',
    }
