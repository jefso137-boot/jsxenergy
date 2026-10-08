from django.db import migrations


def criar_manutencao(apps, schema_editor):
    CustoExtraCatalogo = apps.get_model("financas", "CustoExtraCatalogo")
    CustoExtraCatalogo.objects.get_or_create(
        nome="Manutenção",
        defaults={
            "valor": 0,
            "tipo_campo": "FOTO_TEXTO",
            "aplicavel_em": "MANUTENCAO",
            "valor_definido_pelo_tecnico": True,
            "ativo": True,
        },
    )


def remover_manutencao(apps, schema_editor):
    CustoExtraCatalogo = apps.get_model("financas", "CustoExtraCatalogo")
    CustoExtraCatalogo.objects.filter(nome="Manutenção").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("financas", "0009_alter_custoextracatalogo_aplicavel_em"),
    ]

    operations = [
        migrations.RunPython(criar_manutencao, remover_manutencao),
    ]
