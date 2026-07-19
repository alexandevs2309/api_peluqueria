export interface ServiceCategoryDto {
  id: number;
  name: string;
}

export interface ServiceDto {
  id: number;
  name: string;
  description?: string;
  image?: string;
  categories: number[];
  category_names?: string[];
  price: number;
  duration: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateServiceDto {
  name: string;
  description?: string;
  image?: string;
  categories: number[];
  price: number;
  duration: number;
  is_active: boolean;
}

export interface UpdateServiceDto {
  name?: string;
  description?: string;
  image?: string;
  categories?: number[];
  price?: number;
  duration?: number;
  is_active?: boolean;
}
