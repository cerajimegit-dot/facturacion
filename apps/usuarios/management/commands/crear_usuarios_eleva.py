"""Create vendedor and contador users for Eleva Supply."""
from django.core.management.base import BaseCommand
from apps.usuarios.models import Usuario, Membership
from apps.empresas.models import Empresa


class Command(BaseCommand):
    help = 'Crear usuarios vendedor y contador para Eleva Supply'

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(nombre__icontains='Eleva Supply')
        except Empresa.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                'No se encontró la empresa "Eleva Supply". Créala primero.'
            ))
            return
        except Empresa.MultipleObjectsReturned:
            empresa = Empresa.objects.filter(nombre__icontains='Eleva Supply').first()

        self.stdout.write(f'Empresa: {empresa.nombre} (ID: {empresa.id})')

        # ── Vendedor ──────────────────────────────────────────────────────
        vendedor_email = 'vendedor@elevasupply.com'
        vendedor, created = Usuario.objects.get_or_create(
            email=vendedor_email,
            defaults={
                'username': 'vendedor_eleva',
                'first_name': 'Vendedor',
                'last_name': 'Eleva',
                'rol': 'vendedor',
                'empresa': empresa,
                'is_active': True,
            },
        )
        if created:
            vendedor.set_password('Vendedor2026!')
            vendedor.save()
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Vendedor creado: {vendedor_email} / Vendedor2026!'
            ))
        else:
            self.stdout.write(f'  → Vendedor ya existe: {vendedor_email}')

        # Membership vendedor
        mem_v, mem_created = Membership.objects.get_or_create(
            usuario=vendedor,
            empresa=empresa,
            defaults={'rol': 'vendedor', 'activo': True},
        )
        if mem_created:
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Membership vendedor creada'
            ))

        # ── Contador ──────────────────────────────────────────────────────
        contador_email = 'contador@elevasupply.com'
        contador, created = Usuario.objects.get_or_create(
            email=contador_email,
            defaults={
                'username': 'contador_eleva',
                'first_name': 'Contador',
                'last_name': 'Eleva',
                'rol': 'contador',
                'empresa': empresa,
                'is_active': True,
            },
        )
        if created:
            contador.set_password('Contador2026!')
            contador.save()
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Contador creado: {contador_email} / Contador2026!'
            ))
        else:
            self.stdout.write(f'  → Contador ya existe: {contador_email}')

        # Membership contador
        mem_c, mem_created = Membership.objects.get_or_create(
            usuario=contador,
            empresa=empresa,
            defaults={'rol': 'contador', 'activo': True},
        )
        if mem_created:
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Membership contador creada'
            ))

        # ── Resumen de módulos habilitados ────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Módulos por rol:'))
        self.stdout.write(self.style.SUCCESS(
            '  Vendedor: dashboard, clientes, productos, ventas, cobros, presupuestos, reportes'
        ))
        self.stdout.write(self.style.SUCCESS(
            '  Contador: dashboard, compras, gastos_dashboard, pagos, contabilidad, reportes, productos, inventario'
        ))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('¡Usuarios creados exitosamente!'))
