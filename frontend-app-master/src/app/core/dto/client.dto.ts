export interface ClientDto {
  id: number;
  full_name: string;
  email: string;
  phone?: string;
  address?: string;
  birthday?: string;
  gender?: 'M' | 'F' | 'O';
  notes?: string;
  is_active: boolean;
  branch?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface CreateClientDto {
  full_name: string;
  email: string;
  phone?: string;
  address?: string;
  birthday?: string;
  gender?: 'M' | 'F' | 'O';
  notes?: string;
  is_active: boolean;
  branch?: number | null;
}

export interface UpdateClientDto {
  full_name?: string;
  email?: string;
  phone?: string;
  address?: string;
  birthday?: string;
  gender?: 'M' | 'F' | 'O';
  notes?: string;
  is_active?: boolean;
  branch?: number | null;
}
