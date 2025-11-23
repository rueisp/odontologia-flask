# 🧪 Guía de Pruebas Automatizadas

Esta carpeta contiene las pruebas automatizadas para el proyecto de la clínica odontológica.

## 📁 Estructura de Archivos

```
tests/
├── __init__.py              # Hace que tests sea un paquete Python
├── conftest.py              # Configuración de fixtures para pytest
├── test_auth.py             # Pruebas de autenticación (login, logout, registro)
├── test_pacientes.py        # Pruebas del módulo de pacientes
├── test_citas.py            # Pruebas del módulo de citas
├── test_models.py           # Pruebas de los modelos de base de datos
└── README.md                # Este archivo
```

## 🚀 Instalación de Dependencias

Antes de ejecutar las pruebas, instala pytest:

```bash
pip install pytest pytest-cov
```

O si tienes un archivo `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
```

## ▶️ Cómo Ejecutar las Pruebas

### Ejecutar todas las pruebas:
```bash
pytest
```

### Ejecutar pruebas con más detalles:
```bash
pytest -v
```

### Ejecutar un archivo específico:
```bash
pytest tests/test_auth.py
```

### Ejecutar una prueba específica:
```bash
pytest tests/test_auth.py::TestAuthentication::test_login_with_valid_credentials
```

### Ejecutar pruebas con cobertura de código:
```bash
pytest --cov=clinica --cov-report=html
```

Esto generará un reporte HTML en `htmlcov/index.html` que puedes abrir en tu navegador.

### Ejecutar solo pruebas marcadas:
```bash
pytest -m auth          # Solo pruebas de autenticación
pytest -m pacientes     # Solo pruebas de pacientes
pytest -m citas         # Solo pruebas de citas
```

## 📊 Interpretar los Resultados

### ✅ Prueba exitosa:
```
tests/test_auth.py::TestAuthentication::test_login_page_loads PASSED
```

### ❌ Prueba fallida:
```
tests/test_auth.py::TestAuthentication::test_login_with_valid_credentials FAILED
```

### ⚠️ Prueba omitida:
```
tests/test_auth.py::TestAuthentication::test_some_feature SKIPPED
```

## 🔧 Fixtures Disponibles

Los fixtures están definidos en `conftest.py`:

- **`app`**: Instancia de la aplicación Flask configurada para pruebas
- **`client`**: Cliente de prueba para hacer peticiones HTTP
- **`init_database`**: Base de datos inicializada con datos de prueba
- **`authenticated_client`**: Cliente ya autenticado como usuario normal
- **`admin_client`**: Cliente autenticado como administrador

## 📝 Ejemplo de Uso de Fixtures

```python
def test_mi_prueba(authenticated_client, init_database):
    """Esta prueba usa un cliente autenticado y una BD inicializada"""
    response = authenticated_client.get('/pacientes')
    assert response.status_code == 200
```

## 🎯 Buenas Prácticas

1. **Nombra las pruebas descriptivamente**: `test_login_with_invalid_password` es mejor que `test_1`
2. **Una prueba, una verificación**: Cada prueba debe verificar una sola cosa
3. **Usa fixtures**: Reutiliza código común en fixtures
4. **Limpia después de cada prueba**: Los fixtures con `scope='function'` se limpian automáticamente
5. **Documenta tus pruebas**: Usa docstrings para explicar qué verifica cada prueba

## 🐛 Debugging de Pruebas

Si una prueba falla, puedes usar:

```bash
pytest -v --tb=long  # Muestra más detalles del error
pytest -s            # Muestra prints en la consola
pytest --pdb         # Abre el debugger de Python cuando falla una prueba
```

## 📈 Cobertura de Código

Para ver qué porcentaje de tu código está cubierto por pruebas:

```bash
pytest --cov=clinica --cov-report=term-missing
```

Esto mostrará qué líneas de código NO están cubiertas por pruebas.

## 🔄 Integración Continua (CI)

Estas pruebas pueden ejecutarse automáticamente en GitHub Actions, GitLab CI, o cualquier otra plataforma de CI/CD.

Ejemplo de configuración para GitHub Actions (`.github/workflows/tests.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=clinica
```

## 📚 Recursos Adicionales

- [Documentación de pytest](https://docs.pytest.org/)
- [Documentación de Flask Testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

## ❓ Preguntas Frecuentes

**P: ¿Por qué usar una base de datos en memoria?**  
R: Para que las pruebas sean rápidas y no afecten tu base de datos real.

**P: ¿Necesito ejecutar las pruebas antes de cada commit?**  
R: Es una buena práctica. Puedes configurar un pre-commit hook para hacerlo automáticamente.

**P: ¿Cómo agrego nuevas pruebas?**  
R: Crea un nuevo archivo `test_*.py` o agrega funciones `test_*` a los archivos existentes.

---

¡Feliz testing! 🎉
