# Sistema de Facturación Multi-Empresa

Sistema web multiempresa de facturación y gestión empresarial construido con Django, Django REST Framework y PostgreSQL.

## Características Principales

- **Multi-tenant**: Aislamiento de datos por empresa con `tenant_id` en todos los modelos
- **Autenticación JWT**: Registro, login, refresh tokens, cambio de contraseña
- **Roles**: Administrador, Vendedor, Contador con permisos diferenciados por empresa
- **Módulos**: Empresas, Clientes, Productos, Inventario, Cotizaciones, Ventas, Pagos, Contratos, Órdenes de Servicio
- **Cuentas por Cobrar**: Tracking automático de saldos, aging report, alertas de vencimiento
- **Importación masiva desde Excel**: Validación previa, procesamiento en background (Celery), reportes de errores
- **Auditoría**: Registro automático de todas las operaciones CRUD por usuario
- **Reportes y Dashboard**: KPIs, ventas por período, cuentas por cobrar, exportación a Excel
- **API REST documentada**: OpenAPI/Swagger en `/api/docs/`
- **Docker**: Configuración completa para desarrollo y producción
- **Monedas**: Soporte PYG y USD

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Django 4.2 + DRF 3.15 |
| Frontend | Streamlit 1.56+ |
| Base de datos | PostgreSQL 15 |
| Cola de tareas | Celery + Redis |
| Auth | JWT (SimpleJWT) |
| Docs API | drf-spectacular (Swagger/ReDoc) |
| Excel | pandas + openpyxl |
| Charts | Plotly 6.6+ |
| Deploy | Docker + docker-compose |

## Estructura del Proyecto

```
facturacion/
├── config/                  # Configuración Django
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── core/               # Modelos base, permisos, mixins
│   ├── empresas/            # Gestión de empresas (tenants)
│   ├── usuarios/            # Auth, memberships, roles
│   ├── clientes/            # Clientes, direcciones, contactos
│   ├── productos/           # Productos, categorías, variantes, precios
│   ├── inventario/          # Almacenes, stock, movimientos
│   ├── ventas/              # Cotizaciones, ventas, líneas, CxC
│   ├── pagos/               # Registro y confirmación de pagos
│   ├── contratos/           # Contratos de mantenimiento, órdenes de servicio
│   ├── reportes/            # Dashboard, reportes, exportación Excel
│   ├── importacion/         # Import jobs, validadores, tareas Celery
│   └── auditoria/           # Audit trail, middleware
├── frontend/                # Streamlit UI
│   ├── pages/               # 11 páginas funcionales
│   ├── api_client.py        # Cliente API (41 funciones)
│   ├── helpers.py           # Utilidades de formateo
│   ├── app.py               # Router principal
│   └── requirements.txt     # Deps frontend
├── scripts/                 # Scripts de importación standalone
├── tests/                   # Tests automatizados
├── examples/                # Archivos Excel de ejemplo (generados)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── ESTADO_ACTUAL.md         # Estado actual del proyecto
└── README.md
```

## Instalación Rápida

### Opción 1: Docker (recomendado)

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd facturacion

# 2. Levantar servicios
docker-compose up -d

# 3. Crear migraciones y aplicarlas
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# 4. Crear superusuario
docker-compose exec web python manage.py createsuperuser

# 5. Acceder
# API:     http://localhost:8000/api/v1/
# Swagger: http://localhost:8000/api/docs/
# ReDoc:   http://localhost:8000/api/redoc/
# Admin:   http://localhost:8000/admin/
```

### Opción 2: Instalación Local

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
# Crear archivo .env en la raíz (ya incluido como ejemplo)
# Ajustar DB_HOST=localhost si no usa Docker para la BD

# 4. Asegurar que PostgreSQL está corriendo y crear la BD
# psql -U postgres -c "CREATE DATABASE facturacion;"

# 5. Crear directorio de logs
mkdir logs

# 6. Crear migraciones y aplicarlas
python manage.py makemigrations
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Iniciar servidor
python manage.py runserver

# 9. (En otra terminal) Iniciar Celery worker
celery -A config worker -l info
```

## Endpoints de la API

### Autenticación
| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/v1/auth/registro/` | Registrar nuevo usuario |
| POST | `/api/v1/auth/login/` | Login (obtener tokens JWT) |
| POST | `/api/v1/auth/token/refresh/` | Refrescar access token |
| GET/PUT | `/api/v1/auth/perfil/` | Ver/editar perfil |
| POST | `/api/v1/auth/cambiar-password/` | Cambiar contraseña |

### Empresas
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/v1/empresas/` | Listar/crear empresas |
| GET/PUT/DELETE | `/api/v1/empresas/{id}/` | Detalle/editar/eliminar empresa |

### Clientes (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/v1/clientes/` | Listar/crear clientes |
| GET/PUT/DELETE | `/api/v1/clientes/{id}/` | Detalle/editar/eliminar |
| GET/POST | `/api/v1/clientes/{id}/direcciones/` | Direcciones del cliente |
| GET/POST | `/api/v1/clientes/{id}/contactos/` | Contactos del cliente |

### Productos (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| GET/POST | `/api/v1/productos/` | Listar/crear productos |
| GET/PUT/DELETE | `/api/v1/productos/{id}/` | Detalle/editar/eliminar |
| GET/POST | `/api/v1/productos/categorias/` | Gestión de categorías |
| GET/POST | `/api/v1/productos/precios/` | Listas de precios |

### Inventario (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| CRUD | `/api/v1/inventario/almacenes/` | Almacenes |
| CRUD | `/api/v1/inventario/` | Stock |
| GET | `/api/v1/inventario/bajo_minimo/` | Productos bajo stock mínimo |
| GET/POST | `/api/v1/inventario/movimientos/` | Movimientos de stock |

### Ventas (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| CRUD | `/api/v1/ventas/` | Ventas/Facturas |
| POST | `/api/v1/ventas/{id}/agregar_linea/` | Agregar línea a venta |
| POST | `/api/v1/ventas/{id}/confirmar/` | Confirmar venta → genera CxC |
| POST | `/api/v1/ventas/{id}/anular/` | Anular venta |
| CRUD | `/api/v1/ventas/cotizaciones/` | Cotizaciones |
| POST | `/api/v1/ventas/cotizaciones/{id}/convertir_a_venta/` | Convertir cotización en venta |
| CRUD | `/api/v1/ventas/cuentas-por-cobrar/` | Cuentas por cobrar |
| GET | `/api/v1/ventas/cuentas-por-cobrar/vencidas/` | CxC vencidas |
| GET | `/api/v1/ventas/cuentas-por-cobrar/resumen/` | Resumen de CxC |

### Pagos (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| CRUD | `/api/v1/pagos/` | Pagos |
| POST | `/api/v1/pagos/{id}/confirmar/` | Confirmar pago → actualiza saldos |
| POST | `/api/v1/pagos/{id}/anular/` | Anular pago → revierte saldos |

### Contratos (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| CRUD | `/api/v1/contratos/` | Contratos de mantenimiento |
| CRUD | `/api/v1/contratos/ordenes-servicio/` | Órdenes de servicio |

### Reportes (requiere `?empresa={id}`)
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/v1/reportes/dashboard/` | Dashboard con KPIs |
| GET | `/api/v1/reportes/ventas/` | Reporte de ventas (JSON o Excel) |
| GET | `/api/v1/reportes/cuentas-por-cobrar/` | Aging report de CxC |

### Importación Masiva
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/v1/importacion/` | Listar trabajos de importación |
| POST | `/api/v1/importacion/upload/` | Subir archivo Excel |
| POST | `/api/v1/importacion/{id}/validar/` | Iniciar validación async |
| GET | `/api/v1/importacion/{id}/reporte/` | Ver reporte de validación |
| POST | `/api/v1/importacion/{id}/confirmar/` | Ejecutar importación |
| POST | `/api/v1/importacion/{id}/cancelar/` | Cancelar trabajo |

### Auditoría
| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/v1/auditoria/` | Listar registros de auditoría |

## Flujo de Importación desde Excel

### 1. Generar archivos de ejemplo
```bash
python scripts/generate_example_excel.py
# Genera archivos en examples/
```

### 2. Importación vía API
```bash
# Subir archivo
curl -X POST http://localhost:8000/api/v1/importacion/upload/ \
  -H "Authorization: Bearer <token>" \
  -F "archivo=@examples/importacion_completa.xlsx" \
  -F "tipo=mixto" \
  -F "empresa=<empresa_uuid>"

# Validar (async)
curl -X POST http://localhost:8000/api/v1/importacion/<job_id>/validar/ \
  -H "Authorization: Bearer <token>"

# Ver reporte de validación
curl http://localhost:8000/api/v1/importacion/<job_id>/reporte/ \
  -H "Authorization: Bearer <token>"

# Confirmar importación (async)
curl -X POST http://localhost:8000/api/v1/importacion/<job_id>/confirmar/ \
  -H "Authorization: Bearer <token>"
```

### 3. Importación vía script (CLI)
```bash
# Solo validar
python scripts/import_excel.py --empresa EMP001 --file examples/clientes.xlsx --tipo clientes --validar-solo

# Validar e importar
python scripts/import_excel.py --empresa EMP001 --file examples/importacion_completa.xlsx --tipo mixto
```

### Formato del Excel

**Hoja `clientes`:**
| Columna | Requerida | Descripción |
|---|---|---|
| nombre | Sí | Nombre del cliente |
| ruc | Sí | RUC / Identificación fiscal |
| telefono | No | Teléfono |
| email | No | Email (se valida formato) |
| direccion_facturacion | No | Dirección de facturación |
| direccion_entrega | No | Dirección de entrega |
| tipo_cliente | No | `persona` o `empresa` |
| sector | No | Sector económico |
| zona | No | Zona geográfica |
| observaciones | No | Notas |

**Hoja `productos`:**
| Columna | Requerida | Descripción |
|---|---|---|
| sku | Sí | Código único del producto |
| nombre | Sí | Nombre del producto |
| precio_unitario | Sí | Precio de venta |
| descripcion | No | Descripción |
| categoria | No | Categoría (se crea si no existe) |
| costo | No | Costo de adquisición |
| imagen_url | No | URL de imagen |

**Hoja `stock`:**
| Columna | Requerida | Descripción |
|---|---|---|
| sku | Sí | SKU del producto (debe existir) |
| almacen_codigo | Sí | Código del almacén (se crea si no existe) |
| cantidad | Sí | Cantidad en stock (>= 0) |
| ubicacion | No | Ubicación dentro del almacén |

**Hoja `ventas`:**
| Columna | Requerida | Descripción |
|---|---|---|
| numero | Sí | Número de factura |
| fecha | Sí | Fecha (YYYY-MM-DD o DD/MM/YYYY) |
| cliente_ruc | Sí | RUC del cliente (debe existir) |
| sku | Sí | SKU del producto (debe existir) |
| cantidad | Sí | Cantidad (> 0) |
| precio_unitario | Sí | Precio unitario |
| impuestos | No | % de impuesto (default: 10) |
| estado | No | Estado (default: confirmada) |
| metodo_pago | No | Método de pago |

## Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=apps --cov-report=html

# Tests específicos
pytest tests/test_auth.py
pytest tests/test_clientes.py
pytest tests/test_ventas.py
pytest tests/test_importacion.py

# Solo tests de importación
pytest tests/test_importacion.py -v
```

## Flujo de Trabajo Típico

```
1. POST /api/v1/auth/registro/          → Crear cuenta
2. POST /api/v1/auth/login/             → Obtener token JWT
3. POST /api/v1/empresas/               → Crear empresa (auto-admin)
4. POST /api/v1/importacion/upload/     → Subir clientes + productos desde Excel
5. POST /api/v1/importacion/{id}/validar/ → Validar datos
6. POST /api/v1/importacion/{id}/confirmar/ → Importar datos
7. POST /api/v1/ventas/?empresa={id}    → Crear ventas
8. POST /api/v1/ventas/{id}/confirmar/  → Confirmar → genera CxC
9. POST /api/v1/pagos/?empresa={id}     → Registrar pago
10. POST /api/v1/pagos/{id}/confirmar/  → Confirmar → actualiza saldos
11. GET /api/v1/reportes/dashboard/     → Ver KPIs
```

## Configuración PostgreSQL local

1. Asegúrate que PostgreSQL está instalado y corriendo en localhost:5432.
2. Verifica que exista la base de datos y el usuario:

```bash
psql -U postgres -h localhost -p 5432 -c "SELECT datname FROM pg_database;"
```

3. Si no existe, crea la base de datos `facturacion` (o según tu .env):

```bash
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE facturacion;"
```

4. Puedes usar el script de soporte:

```bash
python scripts/create_postgres_db.py
```

## Variables de Entorno

| Variable | Default | Descripción |
|---|---|---|
| `SECRET_KEY` | (insecure) | Django secret key |
| `DEBUG` | `True` | Modo debug |
| `ALLOWED_HOSTS` | `*` | Hosts permitidos |
| `DB_NAME` | `facturacion` | Nombre de la BD |
| `DB_USER` | `postgres` | Usuario PostgreSQL |
| `DB_PASSWORD` | `postgres` | Contraseña PostgreSQL |
| `DB_HOST` | `localhost` | Host PostgreSQL |
| `DB_PORT` | `5432` | Puerto PostgreSQL |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | URL del broker Redis |
| `CORS_ALLOW_ALL` | `True` | Permitir CORS abierto |

## Despliegue en Producción

1. **Cambiar** `SECRET_KEY` por un valor seguro
2. **Establecer** `DEBUG=False`
3. **Configurar** `ALLOWED_HOSTS` con el dominio
4. **Configurar** `CORS_ALLOW_ALL=False` y agregar orígenes permitidos
5. **Usar** HTTPS con certificado SSL
6. **Configurar** backups automáticos de PostgreSQL
7. Ejecutar `python manage.py collectstatic`

## Checklist de Verificación

- [ ] `docker-compose up -d` levanta todos los servicios
- [ ] `python manage.py makemigrations && python manage.py migrate` sin errores
- [ ] `python manage.py createsuperuser` funciona
- [ ] POST `/api/v1/auth/registro/` crea usuario
- [ ] POST `/api/v1/auth/login/` retorna tokens JWT
- [ ] POST `/api/v1/empresas/` crea empresa con membership admin
- [ ] CRUD de clientes funciona aislado por empresa
- [ ] Importación Excel de 1.000 clientes funciona con reporte
- [ ] Flujo venta → confirmar → pago → confirmar actualiza saldos
- [ ] Dashboard muestra KPIs correctos
- [ ] Auditoría registra operaciones con timestamp y usuario
- [ ] `pytest` pasa todos los tests
- [ ] Swagger en `/api/docs/` muestra todos los endpoints

## Licencia

Proyecto privado. Todos los derechos reservados.
