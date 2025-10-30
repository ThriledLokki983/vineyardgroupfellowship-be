# Settings Configuration

This directory contains the Django settings configuration for the Vineyard Group Fellowship
project.

## File Structure

```
Vineyard Group Fellowship/
├── settings.py           # Entry point - imports from settings/ directory
└── settings/             # Environment-based settings package
    ├── __init__.py       # Auto-selects environment based on DJANGO_ENVIRONMENT
    ├── base.py           # Common settings shared across all environments
    ├── development.py    # Development-specific settings
    ├── production.py     # Production-specific settings
    └── testing.py        # Test-specific settings
```

## Environment Selection

The settings are automatically selected based on the `DJANGO_ENVIRONMENT`
environment variable:

- `development` (default): Uses `settings/development.py`
- `production`: Uses `settings/production.py`
- `testing`: Uses `settings/testing.py`

## Usage

### Docker Development

```yaml
environment:
  DJANGO_SETTINGS_MODULE: Vineyard Group Fellowship.settings.development
  DJANGO_ENVIRONMENT: development
```

### Local Development

```bash
export DJANGO_SETTINGS_MODULE=Vineyard Group Fellowship.settings
export DJANGO_ENVIRONMENT=development
python manage.py runserver
```

### Testing

```bash
export DJANGO_SETTINGS_MODULE=Vineyard Group Fellowship.settings
export DJANGO_ENVIRONMENT=testing
python manage.py test
```

### Production

```bash
export DJANGO_SETTINGS_MODULE=Vineyard Group Fellowship.settings.production
export DJANGO_ENVIRONMENT=production
```

## Cleanup History

**Removed obsolete files (2025-10-20):**

- `settings_backup.py` - 864 lines of old monolithic configuration
- `settings_old.py` - 856 lines of legacy settings
- `test_settings.py` - superseded by `settings/testing.py`

**Current structure benefits:**

- ✅ Environment-based configuration
- ✅ Shared base settings with environment overrides
- ✅ Clear separation of concerns
- ✅ Production-ready security configurations
- ✅ Optimized testing settings
