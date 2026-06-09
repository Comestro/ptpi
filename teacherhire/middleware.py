import traceback
from .models import SystemErrorLog

class GlobalExceptionLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Extract full traceback call-stack
        stack_trace = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
        # Safely extract payload body if it exists
        payload = ""
        try:
            if request.body:
                payload = request.body.decode('utf-8')
        except Exception:
            pass

        # Record system exception into the log database table
        try:
            user = getattr(request, 'user', None)
            if user and not user.is_authenticated:
                user = None

            SystemErrorLog.objects.create(
                user=user,
                source="Backend",
                request_path=request.path,
                request_method=request.method,
                exception_type=exception.__class__.__name__,
                exception_message=str(exception),
                stack_trace=stack_trace,
                payload=payload
            )
        except Exception as e:
            # Safeguard so middleware logger errors never crash the request flow
            print("Logger Middleware Error:", e)

        # Return None so standard Django 500 handling is preserved (custom handlers, debug views)
        return None
