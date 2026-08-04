import base64
import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

LOGO_PATH = settings.BASE_DIR / "static" / "images" / "jsx_energy_logo.jpeg"


def _foto_para_data_uri(campo_arquivo):
    campo_arquivo.open("rb")
    try:
        conteudo = campo_arquivo.read()
    finally:
        campo_arquivo.close()
    mime, _ = mimetypes.guess_type(campo_arquivo.name)
    mime = mime or "image/jpeg"
    b64 = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _logo_data_uri():
    if not LOGO_PATH.exists():
        return None
    conteudo = LOGO_PATH.read_bytes()
    mime, _ = mimetypes.guess_type(str(LOGO_PATH))
    mime = mime or "image/jpeg"
    b64 = base64.b64encode(conteudo).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _montar_paragrafos(texto):
    if not texto:
        return []
    blocos = [b.strip() for b in texto.split("\n\n")]
    return [b for b in blocos if b]


def _montar_bullets(texto):
    if not texto:
        return []
    linhas = [linha.strip() for linha in texto.splitlines()]
    return [linha for linha in linhas if linha]


def montar_contexto(ordem_servico):
    fotos = [
        {
            "titulo_secao": foto.titulo_secao,
            "legenda": foto.legenda,
            "data_uri": _foto_para_data_uri(foto.imagem),
        }
        for foto in ordem_servico.fotos.all()
    ]

    data_relatorio = ordem_servico.data_conclusao or timezone.now()

    return {
        "titulo_pdf": ordem_servico.titulo_pdf,
        "status_page_titulo_pdf": ordem_servico.status_page_titulo_pdf,
        "photo_header_line1_pdf": ordem_servico.photo_header_line1_pdf,
        "cliente_nome": ordem_servico.cliente.nome,
        "report_date": timezone.localtime(data_relatorio).strftime("%d/%m/%Y"),
        "status_pill_text": ordem_servico.status_pill_text,
        "cover_footnote": ordem_servico.cover_footnote,
        "narrativa_paragrafos": _montar_paragrafos(ordem_servico.narrativa_paragrafos),
        "resumo_bullets": _montar_bullets(ordem_servico.resumo_tecnico_bullets),
        "fotos": fotos,
        "logo_data_uri": _logo_data_uri(),
    }


def gerar_pdf_os(ordem_servico):
    """Gera o PDF do relatório da OS (WeasyPrint) e salva em ordem_servico.pdf_file."""
    contexto = montar_contexto(ordem_servico)
    html_string = render_to_string("relatorios/relatorio_os.html", contexto)
    pdf_bytes = HTML(string=html_string).write_pdf()

    nome_arquivo = f"OS-{ordem_servico.pk}-{ordem_servico.cliente.nome}".replace(" ", "_")
    ordem_servico.pdf_file.save(f"{nome_arquivo}.pdf", ContentFile(pdf_bytes), save=True)
    return ordem_servico.pdf_file
