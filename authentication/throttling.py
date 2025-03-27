from rest_framework.throttling import SimpleRateThrottle

class AuthenticationThrottle(SimpleRateThrottle):
    rate = '5/minute'
    scope = 'auth_login'

    def get_cache_key(self, request, view):
        if not request.data.get('email'):
            return None
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.data.get('email')
        }
