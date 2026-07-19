# Sistema de Traducciones Multi-idioma

## ✅ Textos que SÍ se traducen automáticamente

### 1. **Menús estáticos del TopBar**
- Profile / Perfil / Profil / Perfil / Profil
- Settings / Configuración / Paramètres / Configurações / Einstellungen
- Logout / Cerrar sesión / Déconnexion / Sair / Abmelden

### 2. **Selector de idiomas**
- Español / English / Français / Português / Deutsch

### 3. **Mensajes del sistema**
- "Idioma cambiado" / "Language changed" / "Langue modifiée"
- "Éxito" / "Success" / "Succès"
- Mensajes de logout

### 4. **Menús de notificaciones vacíos**
- "No hay notificaciones de citas" → "No appointment notifications" → "Aucune notification de rendez-vous"
- "No hay notificaciones de ventas" → "No sale notifications" → "Aucune notification de vente"

### 5. **Botones de acción**
- "Ver todas las citas" → "View all appointments" → "Voir tous les rendez-vous"
- "Marcar todas como leídas" → "Mark all as read" → "Tout marquer comme lu"

### 6. **Textos comunes**
- Guardar / Save / Enregistrer / Salvar / Speichern
- Cancelar / Cancel / Annuler / Cancelar / Abbrechen
- Eliminar / Delete / Supprimer / Excluir / Löschen
- Buscar / Search / Rechercher / Pesquisar / Suchen

---

## ❌ Textos que NO se traducen (y por qué)

### 1. **Títulos de notificaciones dinámicas**
**Ejemplo**: "Nueva cita con Juan Pérez"

**Por qué**: Estos textos vienen del **backend** en tiempo real. Para traducirlos necesitarías:
- Que el backend envíe traducciones en todos los idiomas
- O que el backend detecte el idioma del usuario y envíe el texto traducido

**Solución**: El backend debería usar Django i18n y enviar notificaciones según el idioma del usuario.

### 2. **Contenido de la base de datos**
**Ejemplo**: Nombres de servicios, productos, clientes

**Por qué**: Son datos específicos del negocio, no textos de interfaz.

**Solución**: Si necesitas traducir contenido de BD, implementa campos multiidioma:
```python
class Service(models.Model):
    name_es = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    name_fr = models.CharField(max_length=100)
```

### 3. **Mensajes de validación del backend**
**Ejemplo**: "El cliente ya existe en este tenant"

**Por qué**: Ya están traducidos por Django usando `gettext_lazy()` y el header `Accept-Language`.

**Estado**: ✅ Ya implementado en tu backend.

---

## 🔧 Cómo agregar nuevas traducciones

### Paso 1: Agregar clave en `translations.ts`
```typescript
export const TRANSLATIONS = {
  es: {
    'dashboard.title': 'Panel de Control',
  },
  en: {
    'dashboard.title': 'Dashboard',
  },
  fr: {
    'dashboard.title': 'Tableau de bord',
  }
}
```

### Paso 2: Usar en componente
```typescript
// En TypeScript
this.localeService.t('dashboard.title')

// En template
{{ localeService.t('dashboard.title') }}
```

---

## 📊 Cobertura actual

| Área | Cobertura | Estado |
|------|-----------|--------|
| TopBar menús | 100% | ✅ |
| Selector idiomas | 100% | ✅ |
| Mensajes sistema | 100% | ✅ |
| Notificaciones estáticas | 100% | ✅ |
| Notificaciones dinámicas | 0% | ⚠️ Backend |
| Validaciones backend | 100% | ✅ Django i18n |
| Contenido BD | 0% | ⚠️ Requiere campos multi-idioma |

---

## 🎯 Recomendaciones

### Para traducir notificaciones dinámicas:

**Backend (Django)**:
```python
from django.utils.translation import gettext as _

# En signals o tasks
Notification.objects.create(
    title=_('Nueva cita con %(client)s') % {'client': client.name},
    # Django traducirá según Accept-Language del usuario
)
```

**Frontend**: Ya envía `Accept-Language` automáticamente vía interceptor.

### Para traducir contenido de BD:

Usa librerías como `django-modeltranslation` o implementa campos separados por idioma.

---

## ✅ Resultado actual

Al cambiar de idioma:
1. ✅ Menús se actualizan instantáneamente
2. ✅ Botones cambian de texto
3. ✅ Mensajes toast se traducen
4. ✅ Validaciones backend ya traducidas
5. ⚠️ Notificaciones dinámicas permanecen en idioma original (requiere backend)

**Sistema funcional y listo para producción con traducciones estáticas completas.**
