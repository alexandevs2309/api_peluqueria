# DECISIÓN ARQUITECTÓNICA: Sistema Fiscal Multi-País

## PROBLEMA
¿Usar modelo configurable vs calculadoras hardcodeadas?

## DECISIÓN: HÍBRIDO

### FASE 1 (ACTUAL): Calculadoras por País
```python
# Cada país = una clase especializada
class DominicanTaxCalculator:
    # Lógica específica RD
    
class USATaxCalculator:
    # Lógica específica USA
    
class MexicoTaxCalculator:
    # Lógica específica México
```

**VENTAJAS:**
- ✅ Lógica fiscal correcta por país
- ✅ Validada por expertos legales
- ✅ Sin errores de configuración
- ✅ Fácil testing y auditoría

### FASE 2 (FUTURO): Modelo para Ajustes Menores
```python
class TaxAdjustment(models.Model):
    country = models.CharField(max_length=2)
    tax_type = models.CharField()
    rate_adjustment = models.DecimalField()  # Solo ajustes, no lógica completa
    effective_date = models.DateField()
    is_active = models.BooleanField()
```

**USO:** Solo para cambios de tasas, no lógica completa.

## IMPLEMENTACIÓN RECOMENDADA

### 1. Agregar Calculadoras por País (Mínimo)
- USA: Sin descuentos federales obligatorios
- México: IMSS, INFONAVIT, ISR básico
- Colombia: Salud, Pensión, ARL

### 2. Modelo Simple de Configuración
- Solo tasas básicas
- No lógica de cálculo
- Validaciones estrictas

## RAZONES DE LA DECISIÓN

1. **Cumplimiento Legal**: Calculadoras validadas > Configuración errónea
2. **Mantenibilidad**: Código específico > Lógica genérica compleja
3. **Escalabilidad**: Agregar países = agregar clases (simple)
4. **Riesgo**: Bajo riesgo legal con lógica hardcodeada

## CONCLUSIÓN
Empezar con calculadoras específicas, evolucionar a híbrido cuando sea necesario.