export class UIHelpers {
  static getActionSeverity(action: string): 'success' | 'info' | 'danger' | 'secondary' {
    switch (action) {
      case 'CREATE': return 'success';
      case 'UPDATE': return 'info';
      case 'DELETE': return 'danger';
      default: return 'secondary';
    }
  }

  static getRoleSeverity(role: string): 'danger' | 'warn' | 'info' | 'success' | 'secondary' {
    switch (role) {
      case 'SUPER_ADMIN':
      case 'SuperAdmin': return 'danger';
      case 'CLIENT_ADMIN':
      case 'Client-Admin': return 'warn';
      case 'CLIENT_STAFF':
      case 'Client-Staff': return 'info';
      case 'Estilista': return 'info';
      case 'Cajera': return 'success';
      case 'Manager': return 'warn';
      case 'Utility': return 'secondary';
      default: return 'secondary';
    }
  }

  static getStatusSeverity(isActive: boolean): 'success' | 'danger' {
    return isActive ? 'success' : 'danger';
  }
}
