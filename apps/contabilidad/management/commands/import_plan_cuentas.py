"""Management command para importar plan de cuentas desde Excel.

Soporta el formato ANEXO 1 (Balance General SET/DNIT) donde:
- Columna 0: código de cuenta (1, 1.01, 1.01.01, etc.)
- Columna 1: descripción de la cuenta
- Filas con 'xx' son placeholders y se ignoran
- Los datos empiezan aprox. en la fila 13
"""
import re
from django.core.management.base import BaseCommand
import pandas as pd
from apps.contabilidad.models import PlanCuentas
from apps.empresas.models import Empresa


class Command(BaseCommand):
    help = 'Importa plan de cuentas desde archivo Excel formato ANEXO 1'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Ruta del archivo Excel')
        parser.add_argument(
            '--empresa', type=str, default='',
            help='Nombre de la empresa (parcial). Si no se indica, usa la primera.'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Solo muestra qué se importaría sin crear nada'
        )

    def _parse_excel(self, excel_file):
        """Parsea el Excel formato ANEXO 1 y retorna lista de (codigo, descripcion)."""
        df = pd.read_excel(excel_file, header=None)
        self.stdout.write(f"Leyendo {len(df)} filas del Excel")

        accounts = []
        code_pattern = re.compile(r'^\d[\d.]*$')

        for idx, row in df.iterrows():
            raw_code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            raw_desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''

            if not raw_code or not raw_desc:
                continue
            if not code_pattern.match(raw_code):
                continue
            if 'xx' in raw_code:
                continue

            accounts.append((raw_code, raw_desc))

        return accounts

    def _determine_condicion(self, codigo):
        """Determina naturaleza de la cuenta por su prefijo."""
        if codigo.startswith('1'):
            return 'deudora'
        elif codigo.startswith('2'):
            return 'acreedora'
        elif codigo.startswith('3'):
            return 'acreedora'
        return 'deudora'

    def _determine_clase(self, codigo):
        """Determina si la cuenta es sintética (agrupadora) o analítica (detalle).
        
        Convención: cuentas con menos de 3 niveles son sintéticas.
        Ej: 1, 1.01, 1.01.01 = sintéticas; 1.01.01.01 = analítica
        """
        parts = codigo.split('.')
        if len(parts) <= 3:
            return 'sintetica'
        return 'analitica'

    def _find_parent_code(self, codigo):
        """Determina el código padre. Ej: 1.01.01.01 -> 1.01.01"""
        parts = codigo.split('.')
        if len(parts) <= 1:
            return None
        return '.'.join(parts[:-1])

    def handle(self, *args, **options):
        excel_file = options['excel_file']
        empresa_name = options['empresa']
        dry_run = options['dry_run']

        # Obtener empresa
        if empresa_name:
            empresa = Empresa.objects.filter(nombre__icontains=empresa_name).first()
        else:
            empresa = Empresa.objects.first()

        if not empresa:
            self.stdout.write(self.style.ERROR("No se encontró la empresa"))
            return

        self.stdout.write(f"Empresa: {empresa.nombre} ({empresa.id})")

        try:
            accounts = self._parse_excel(excel_file)
            self.stdout.write(f"Cuentas válidas encontradas: {len(accounts)}")

            if dry_run:
                for cod, desc in accounts:
                    cond = self._determine_condicion(cod)
                    cls = self._determine_clase(cod)
                    exists = PlanCuentas.objects.filter(
                        empresa=empresa, codigo_cuenta=cod
                    ).exists()
                    status = "EXISTE" if exists else "NUEVA"
                    self.stdout.write(f"  [{status}] {cod} - {desc} ({cond}/{cls})")
                return

            created = 0
            updated = 0
            skipped = 0

            # Primera pasada: crear/actualizar cuentas
            for cod, desc in accounts:
                condicion = self._determine_condicion(cod)
                clase = self._determine_clase(cod)

                obj, was_created = PlanCuentas.objects.update_or_create(
                    empresa=empresa,
                    codigo_cuenta=cod,
                    defaults={
                        'descripcion': desc,
                        'condicion': condicion,
                        'clase': clase,
                        'activa': True,
                    }
                )
                if was_created:
                    created += 1
                    self.stdout.write(f"  + {cod} - {desc}")
                else:
                    updated += 1

            # Segunda pasada: asignar parentesco
            parents_set = 0
            for cod, _ in accounts:
                parent_code = self._find_parent_code(cod)
                if not parent_code:
                    continue
                parent = PlanCuentas.objects.filter(
                    empresa=empresa, codigo_cuenta=parent_code
                ).first()
                if parent:
                    PlanCuentas.objects.filter(
                        empresa=empresa, codigo_cuenta=cod
                    ).update(parent=parent)
                    parents_set += 1

            total = PlanCuentas.objects.filter(empresa=empresa).count()
            self.stdout.write(self.style.SUCCESS(
                f"\nResumen:\n"
                f"  Creadas: {created}\n"
                f"  Actualizadas: {updated}\n"
                f"  Parentescos: {parents_set}\n"
                f"  Total en BD: {total}"
            ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {excel_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
