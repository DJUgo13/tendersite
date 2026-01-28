from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Проверяет финальные таймеры направлений и при необходимости закрывает направления."

    def handle(self, *args, **options):
        from core.utils import check_auto_close_directions
        from core.models import Direction

        before = Direction.objects.filter(winner__isnull=False).count()
        check_auto_close_directions()
        after = Direction.objects.filter(winner__isnull=False).count()

        self.stdout.write(self.style.SUCCESS(
            f"[{timezone.now().strftime('%d.%m.%Y %H:%M:%S')}] Done. Winners before: {before}, after: {after}."
        ))

