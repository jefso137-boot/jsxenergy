from django.db import migrations


def criar_checklist_manutencao(apps, schema_editor):
    ChecklistTemplate = apps.get_model("checklists", "ChecklistTemplate")
    ChecklistTemplate.objects.get_or_create(
        tipo="MANUTENCAO",
        defaults={"nome": "Manutenção"},
    )


def remover_checklist_manutencao(apps, schema_editor):
    ChecklistTemplate = apps.get_model("checklists", "ChecklistTemplate")
    ChecklistTemplate.objects.filter(tipo="MANUTENCAO").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("checklists", "0007_alter_checklisttemplate_tipo"),
    ]

    operations = [
        migrations.RunPython(criar_checklist_manutencao, remover_checklist_manutencao),
    ]
