# Database Migrations

This directory contains database migration scripts using Flask-Migrate (Alembic).

## Setup

Install Flask-Migrate:
```bash
pip install Flask-Migrate
```

## Migration Commands

### Initialize migrations (first time only)
```bash
flask db init
```

### Create a new migration
```bash
flask db migrate -m "Description of changes"
```

### Apply migrations
```bash
flask db upgrade
```

### Rollback migration
```bash
flask db downgrade
```

### View migration history
```bash
flask db history
```

### View current migration
```bash
flask db current
```

## Migration Scripts

Manual migration scripts are located in `versions/manual/` directory.

### Performance Optimization Migrations

1. **001_add_performance_indexes.sql** - Adds optimized indexes for frequently queried columns
2. **002_optimize_settings_tables.sql** - Optimizes settings tables structure
3. **003_add_cache_table.sql** - Adds optional cache table for non-Redis deployments

## Best Practices

1. Always review auto-generated migrations before applying
2. Test migrations on a backup database first
3. Include both upgrade and downgrade paths
4. Document breaking changes in migration messages
5. Keep migrations small and focused
6. Back up database before running migrations in production

## Rollback Strategy

All migrations include rollback scripts. To rollback:
```bash
flask db downgrade -1  # Rollback one migration
flask db downgrade <revision>  # Rollback to specific revision
```
