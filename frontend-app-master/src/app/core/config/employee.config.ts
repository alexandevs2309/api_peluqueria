export const EMPLOYEE_CONFIG = {
  // Configuración de formularios
  FORM: {
    MIN_NAME_LENGTH: 2,
    MIN_PASSWORD_LENGTH: 8,
    DEFAULT_PASSWORD: 'Temporal123!',
    MAX_PROFESSION_LENGTH: 100,
    MAX_PHONE_LENGTH: 20
  },

  // Mensajes de validación
  VALIDATION_MESSAGES: {
    REQUIRED_NAME: 'El nombre completo es requerido',
    MIN_NAME_LENGTH: 'El nombre debe tener al menos 2 caracteres',
    REQUIRED_EMAIL: 'El email es requerido',
    INVALID_EMAIL: 'El email debe ser válido',
    EMAIL_TAKEN: 'Este email ya está en uso',
    REQUIRED_PASSWORD: 'La contraseña es requerida',
    MIN_PASSWORD_LENGTH: 'La contraseña debe tener al menos 8 caracteres',
    INVALID_PHONE: 'El formato del teléfono es inválido'
  },

  // Mensajes de éxito
  SUCCESS_MESSAGES: {
    EMPLOYEE_CREATED: 'Empleado creado correctamente',
    EMPLOYEE_UPDATED: 'Empleado actualizado correctamente',
    EMPLOYEE_DELETED: 'Empleado eliminado correctamente',
    EMPLOYEES_LOADED: 'empleado(s) cargado(s) correctamente'
  },

  // Mensajes de error
  ERROR_MESSAGES: {
    LOAD_EMPLOYEES: 'No se pudieron cargar los empleados',
    CREATE_EMPLOYEE: 'No se pudo crear el empleado',
    UPDATE_EMPLOYEE: 'No se pudo actualizar el empleado',
    DELETE_EMPLOYEE: 'No se pudo eliminar el empleado',
    INVALID_DATA: 'Datos inválidos. Verifique la información ingresada',
    NO_PERMISSIONS: 'Sin permisos para realizar esta acción',
    CONNECTION_ERROR: 'Error de conexión con el servidor',
    EMPLOYEE_LIMIT: 'Límite de empleados alcanzado para su plan',
    USER_CREATION_FAILED: 'Error al crear el usuario',
    EMPLOYEE_CREATION_FAILED: 'Error al crear el empleado',
    ROLLBACK_FAILED: 'Se creó el usuario pero no se pudo eliminar tras el error. Contacte al administrador.'
  },

  // Estados de empleado
  EMPLOYEE_STATUS: {
    ACTIVE: { label: 'Activo', value: true, severity: 'success' },
    INACTIVE: { label: 'Inactivo', value: false, severity: 'danger' }
  },

  // Configuración de tabla
  TABLE: {
    ROWS_PER_PAGE: 10,
    GLOBAL_FILTER_FIELDS: ['nombre', 'email', 'profession'],
    EMPTY_MESSAGE: 'No hay empleados registrados'
  },

  // Configuración de diálogo
  DIALOG: {
    WIDTH: '600px',
    CREATE_HEADER: 'Nuevo Empleado',
    EDIT_HEADER: 'Editar Empleado'
  },

  // Roles permitidos para empleados
  ALLOWED_ROLES: ['ClientStaff', 'ClientAdmin'],

  // Profesiones predefinidas (ADR-001: profession = cargo del empleado)
  PROFESSIONS: [
    { value: 'barber', label: 'Barbero (Corte caballero)' },
    { value: 'stylist', label: 'Estilista (Corte dama)' },
    { value: 'manicurist', label: 'Manicurista' },
    { value: 'pedicurist', label: 'Pedicurista' },
    { value: 'colorist', label: 'Colorista' },
    { value: 'braider', label: 'Trencista' },
    { value: 'eyebrow', label: 'Cejas / Pestañas' },
    { value: 'makeup', label: 'Maquilladora' },
    { value: 'massage', label: 'Masajista' },
    { value: 'barber_stylist', label: 'Barbero / Estilista' },
    { value: 'receptionist', label: 'Recepcionista' },
    { value: 'cashier', label: 'Cajero / Cajera' },
    { value: 'manager', label: 'Administrador / Gerente' },
    { value: 'general', label: 'General / Multipropósito' },
    { value: 'other', label: 'Otro' },
  ],

  // Patrones de validación
  PATTERNS: {
    PHONE: /^[\+]?[1-9][\d]{0,15}$/,
    EMAIL: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  },

  // Configuración de paginación
  PAGINATION: {
    DEFAULT_PAGE_SIZE: 10,
    PAGE_SIZE_OPTIONS: [5, 10, 20, 50]
  }
};

export const EMPLOYEE_PERMISSIONS = {
  CREATE: 'employees.create',
  READ: 'employees.read',
  UPDATE: 'employees.update',
  DELETE: 'employees.delete',
  MANAGE_ALL: 'employees.manage_all'
};

export const USER_PERMISSIONS = {
  CREATE: 'users.create',
  READ: 'users.read',
  UPDATE: 'users.update',
  DELETE: 'users.delete'
};
