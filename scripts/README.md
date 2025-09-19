# 💾 Scripts de Backup y Restore

## 📋 Archivos Incluidos

- `backup.sh` - Script de backup automático
- `restore.sh` - Script de restore de base de datos  
- `setup-cron.sh` - Configuración de cron job automático

## 🚀 Uso

### Backup Manual
```bash
# Backup básico
./scripts/backup.sh

# Con configuración personalizada
BACKUP_DIR=/path/to/backups RETENTION_DAYS=30 ./scripts/backup.sh
```

### Restore
```bash
# Restore desde backup
./scripts/restore.sh ./backups/backup_20241201_120000.sql.gz
```

### Configurar Backups Automáticos
```bash
# Configurar cron job (backup diario 2:00 AM)
./scripts/setup-cron.sh
```

## ⚙️ Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `DATABASE_URL` | - | URL de conexión a PostgreSQL |
| `BACKUP_DIR` | `./backups` | Directorio de backups |
| `RETENTION_DAYS` | `7` | Días de retención de backups |

## 📁 Estructura de Backups

```
backups/
├── backup_20241201_120000.sql.gz
├── backup_20241202_120000.sql.gz
└── backup_20241203_120000.sql.gz
```

## 🔧 Troubleshooting

### Error: "pg_dump: command not found"
```bash
# Instalar PostgreSQL client
apt-get install postgresql-client
```

### Error: "Permission denied"
```bash
# Dar permisos de ejecución
chmod +x scripts/*.sh
```

### Verificar Cron Job
```bash
# Ver cron jobs activos
crontab -l

# Ver logs de backup
tail -f /var/log/backup.log
```