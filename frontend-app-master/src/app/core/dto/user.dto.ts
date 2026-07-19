export interface UserDto {
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
}

export interface CreateUserDto {
  email: string;
  full_name: string;
  password: string;
  role?: string;
  business_role?: string;
  tenant: number;
}

export interface UpdateUserDto {
  email?: string;
  full_name?: string;
  role?: string;
  business_role?: string;
  is_active?: boolean;
}
