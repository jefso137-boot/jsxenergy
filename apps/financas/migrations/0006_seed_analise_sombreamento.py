from django.db import migrations


def criar_analise_sombreamento(apps, schema_editor):
    CustoExtraCatalogo = apps.get_model("financas", "CustoExtraCatalogo")
    CustoExtraCatalogo.objects.get_or_create(
        nome="Análise de sombreamento",
        defaults={
            "valor": 100,
            "tipo_campo": "ARQUIVO_PDF",
            "aplicavel_em": "VISTORIA",
            "ativo": True,
        },
    )


def remover_analise_sombreamento(apps, schema_editor):
    CustoExtraCatalogo = apps.get_model("financas", "CustoExtraCatalogo")
    CustoExtraCatalogo.objects.filter(nome="Análise de sombreamento").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("financas", "0005_custoextracatalogo_aplicavel_em_and_more"),
    ]

    operations = [
        migrations.RunPython(criar_analise_sombreamento, remover_analise_sombreamento),
    ]
