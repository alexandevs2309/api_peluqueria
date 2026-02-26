# apps/auth_api/role_hierarchy.py
"""
Jerarquía de roles y validaciones de seguridad
"""

# Jerarquía estricta de roles
ROLE_HIERARCHY = {
    'SuperAdmin': {
        'can_create': ['SuperAdmin', 'Client-Admin', 'Client-Staff', 'Estilista', 'Cajera', 'Manager'],
        'level': 0,
        'scope': 'GLOBAL'
    },
    'Client-Admin': {
        'can_create': ['Client-Staff', 'Estilista', 'Cajera', 'Manager'],
        'level': 1,
        'scope': 'TENANT'
    },
    'Client-Staff': {
        'can_create': [],
        'level': 2,
        'scope': 'TENANT'
    },
    'Estilista': {
        'can_create': [],
        'level': 2,
        'scope': 'TENANT'
    },
    'Cajera': {
        'can_create': [],
        'level': 2,
        'scope': 'TENANT'
    },
    'Manager': {
        'can_create': [],
        'level': 2,
        'scope': 'TENANT'
    }
}


def validate_role_assignment(creator_role, target_role, creator_is_superuser=False):
    """
    Valida si un usuario puede asignar un rol específico
    
    Args:
        creator_role: Rol del usuario que crea/modifica
        target_role: Rol que se intenta asignar
        creator_is_superuser: Si el creador es superusuario
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # SuperAdmin puede asignar cualquier rol
    if creator_is_superuser:
        return True, None
    
    # Validar que el rol del creador existe
    if creator_role not in ROLE_HIERARCHY:
        return False, f'Rol de creador inválido: {creator_role}'
    
    # Validar que el rol objetivo existe
    if target_role not in ROLE_HIERARCHY:
        return False, f'Rol objetivo inválido: {target_role}'
    
    # Validar jerarquía
    allowed_roles = ROLE_HIERARCHY[creator_role]['can_create']
    if target_role not in allowed_roles:
        return False, f'{creator_role} no puede asignar rol {target_role}. Roles permitidos: {", ".join(allowed_roles)}'
    
    return True, None


def get_allowed_roles(creator_role, creator_is_superuser=False):
    """
    Obtiene lista de roles que un usuario puede asignar
    
    Args:
        creator_role: Rol del usuario
        creator_is_superuser: Si es superusuario
    
    Returns:
        list: Lista de roles permitidos
    """
    if creator_is_superuser:
        return list(ROLE_HIERARCHY.keys())
    
    if creator_role not in ROLE_HIERARCHY:
        return []
    
    return ROLE_HIERARCHY[creator_role]['can_create']


def can_modify_user(modifier_role, target_user_role, modifier_is_superuser=False):
    """
    Valida si un usuario puede modificar a otro usuario
    
    Args:
        modifier_role: Rol del usuario que modifica
        target_user_role: Rol del usuario objetivo
        modifier_is_superuser: Si el modificador es superusuario
    
    Returns:
        tuple: (can_modify, error_message)
    """
    # SuperAdmin puede modificar a cualquiera
    if modifier_is_superuser:
        return True, None
    
    # No se puede modificar a usuarios de nivel superior o igual
    if modifier_role not in ROLE_HIERARCHY or target_user_role not in ROLE_HIERARCHY:
        return False, 'Rol inválido'
    
    modifier_level = ROLE_HIERARCHY[modifier_role]['level']
    target_level = ROLE_HIERARCHY[target_user_role]['level']
    
    if target_level <= modifier_level:
        return False, f'{modifier_role} no puede modificar usuarios con rol {target_user_role}'
    
    return True, None
