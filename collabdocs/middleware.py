import time


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        print(
            f"{request.method} {request.path} "
            f"{response.status_code} {elapsed_ms:.2f}ms"
        )
        return response
