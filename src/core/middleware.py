import logging

logger = logging.getLogger(__name__)

class HeaderDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/login') and request.method == 'POST':
            print(f"--- Headers for {request.path} ---")
            for k, v in request.META.items():
                if k.startswith('HTTP_') or k in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
                    print(f"{k}: {v}")
            print(f"Is secure: {request.is_secure()}")
            print(f"Scheme: {request.scheme}")
            print("----------------------------------")
        
        response = self.get_response(request)
        return response

class AllowNullOriginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.META.get('HTTP_ORIGIN') == 'null':
            # SECURITY: Only trust 'null' origin if the browser confirms it is a same-origin request.
            # This prevents attacks from sandboxed iframes (which send Origin: null but Sec-Fetch-Site: cross-site).
            if request.META.get('HTTP_SEC_FETCH_SITE') == 'same-origin':
                request.META['HTTP_ORIGIN'] = f"{request.scheme}://{request.get_host()}"
        
        return self.get_response(request)
