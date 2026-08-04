import os

from django.core.management.base import BaseCommand

from apps.contas.models import Usuario


class Command(BaseCommand):
    help = (
        "Cria o usuario administrativo inicial a partir das variaveis de ambiente "
        "DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD. "
        "Nao faz nada se as variaveis nao estiverem definidas ou se o usuario ja existir."
    )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD nao definidos, pulando.")
            return

        if Usuario.objects.filter(username=username).exists():
            self.stdout.write(f"Usuario '{username}' ja existe, pulando.")
            return

        Usuario.objects.create_superuser(username, email, password, role="admin")
        self.stdout.write(self.style.SUCCESS(f"Usuario admin '{username}' criado com sucesso."))
