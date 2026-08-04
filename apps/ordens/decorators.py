from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def tecnico_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_tecnico:
            raise PermissionDenied("Esta área é exclusiva para técnicos de campo.")
        return view_func(request, *args, **kwargs)

    return wrapper
