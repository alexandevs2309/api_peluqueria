export function extractErrorDetail(error: any): string | null {
  const body = error?.error;
  if (!body) return null;

  if (typeof body === 'string') return body;

  if (body?.detail) {
    return Array.isArray(body.detail) ? body.detail[0] : body.detail;
  }

  if (body?.message) {
    return Array.isArray(body.message) ? body.message[0] : body.message;
  }

  if (body?.error) {
    return Array.isArray(body.error) ? body.error[0] : body.error;
  }

  if (Array.isArray(body) && body.length > 0) {
    return String(body[0]);
  }

  if (typeof body === 'object') {
    const firstField = Object.keys(body).find(k => k !== 'code' && k !== 'reason');
    if (firstField) {
      const val = body[firstField];
      return Array.isArray(val) ? val[0] : String(val);
    }
  }

  return null;
}

export function getHttpErrorMessage(error: any, fallbackMessage: string): string {
    const status = error?.status;
    const backendCode = error?.error?.code;
    const backendReason = error?.error?.reason;
    const backendDetail =
        error?.error?.detail ||
        error?.error?.message ||
        error?.error?.error ||
        extractErrorDetail(error);

    if (status === 0) {
        return 'No hay conexion con el servidor. Verifica tu internet o que el API este en linea.';
    }

    if (status >= 500) {
        return 'El servidor no esta disponible en este momento. Intenta nuevamente en unos minutos.';
    }

    if (status === 429) {
        return 'Demasiados intentos. Espera un momento e intenta otra vez.';
    }

    if (status === 401) {
        return backendDetail || 'Credenciales invalidas.';
    }

    if (status === 403) {
        if (backendCode === 'TENANT_INACTIVE') {
            if (backendReason === 'trial_expired') {
                return 'El periodo de prueba de tu empresa ha expirado. Contacta al soporte o al administrador del SaaS.';
            }

            if (backendReason === 'paid_access_expired') {
                return 'El acceso de pago de tu empresa ha expirado. Contacta al soporte o al administrador del SaaS.';
            }

            if (backendReason === 'tenant_suspended') {
                return 'La cuenta de tu empresa esta suspendida. Contacta al soporte o al administrador del SaaS.';
            }

            if (backendReason === 'tenant_deleted') {
                return 'La cuenta de tu empresa fue desactivada. Contacta al soporte o al administrador del SaaS.';
            }

            return 'La cuenta de tu empresa esta inactiva. Contacta al soporte o al administrador del SaaS.';
        }

        return backendDetail || 'No tienes permisos para realizar esta accion.';
    }

    if (status === 404) {
        return backendDetail || 'No se encontro el recurso solicitado.';
    }

    if (status === 402) {
        return backendDetail || 'Se requiere una suscripcion activa para continuar.';
    }

    return backendDetail || fallbackMessage;
}
