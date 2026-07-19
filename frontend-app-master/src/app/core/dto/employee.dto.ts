export interface EmployeeDto {
  id: number;
  user_id: number;
  branch?: number | null;
  profession?: string;
  profession_display?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
  service_ids?: number[];
  services_count?: number;
  created_at: string;
}

export interface EmployeeWithUserDto {
  id: number;
  user_id: number;
  branch?: number | null;
  user: {
    id: number;
    email: string;
    full_name: string;
    role: string;
    business_role?: string;
    business_role_display?: string;
    is_active: boolean;
    tenant: number;
    created_at: string;
    updated_at: string;
  };
  profession?: string;
  profession_display?: string;
  phone?: string;
  hire_date?: string;
  is_active: boolean;
  service_ids?: number[];
  services_count?: number;
  created_at: string;
  display_name?: string;
}

export interface CreateEmployeeDto {
  user_id: number;
  branch?: number | null;
  profession?: string;
  phone?: string;
  hire_date?: string;
  is_active?: boolean;
}

export interface UpdateEmployeeDto {
  branch?: number | null;
  profession?: string;
  phone?: string;
  hire_date?: string;
  is_active?: boolean;
}
