from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


@login_required
def painel_redirect(request):
    if request.user.is_tecnico:
        return redirect("tecnico_minhas_os")
    if request.user.is_lider:
        return redirect("lider_minhas_os")
    return redirect("admin:index")


def csrf_failure(request, reason=""):
    """Em vez da página de erro padrão do Django, manda o usuário de volta
    para a mesma tela com uma mensagem clara — cobre o caso comum de a
    página ter ficado aberta por muito tempo e a sessão expirar."""
    messages.error(request, "Sua sessão expirou. Tente novamente.")
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(referer)
    return redirect("painel_redirect")
