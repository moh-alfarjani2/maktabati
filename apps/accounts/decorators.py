from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(allowed_roles=[]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if request.user.is_superuser or (getattr(request.user, 'role', None) and request.user.role.name in allowed_roles):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, "ليس لديك صلاحية للوصول إلى هذه الصفحة.")
            return redirect('dashboard')
        return _wrapped_view
    return decorator
