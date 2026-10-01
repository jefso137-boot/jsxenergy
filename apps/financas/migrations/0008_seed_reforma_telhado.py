from django.db import migrations


def criar_reforma_telhado(apps, schema_editor):
    CustoExtraCatalogo = apps.get_model("financas", "CustoExtraCatalogo")
    CustoExtraCatalogo.objects.get_or_create(
        nome="Reforma de telhado",
        defaults={
            "valor": 0,
            "tipo_campo": "FOTO_TEXTO",
            "aplicavel_em": "INSTALACAO",
            "valor_definido_pelo_tecnico": True,
            "ativo": True,
        },
    )


def remover_reforma_telhado(apps, schema_editor):
    CustoExtraCatalogo = apps.get_model("financas", "CustoExtraCatalogo")
    CustoExtraCatalogo.objects.filter(nome="Reforma de telhado").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("financas", "0007_custoextracatalogo_valor_definido_pelo_tecnico_and_more"),
    ]

    operations = [
        migrations.RunPython(criar_reforma_telhado, remover_reforma_telhado),
    ]
