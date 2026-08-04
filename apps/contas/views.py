from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def painel_redirect(request):
    if request.user.is_tecnico:
        return redirect("tecnico_minhas_os")
    return redirect("admin:index")
