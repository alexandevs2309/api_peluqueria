export interface AppointmentDto {
  id: number;
  client: number; // ✅ Backend field (ID relacional)
  stylist: number; // ✅ Backend field (ID relacional)
  service?: number; // ✅ Backend field (ID relacional)
  date_time: string;
  description?: string;
  status: 'scheduled' | 'completed' | 'cancelled';
  created_at?: string;
  updated_at?: string;
}

export interface AppointmentWithDetailsDto extends AppointmentDto {
  // Campos enriquecidos para UI (calculados por adaptador)
  client_name?: string;
  stylist_name?: string;
  service_name?: string;
  service_price?: number;
  service_duration?: number;
}

export interface CreateAppointmentDto {
  client: number; // ✅ Backend field name
  stylist: number; // ✅ Backend field name
  service?: number; // ✅ Backend field name
  date_time: string;
  description?: string;
  status: 'scheduled' | 'completed' | 'cancelled';
}

export interface UpdateAppointmentDto {
  client?: number;
  stylist?: number;
  service?: number;
  date_time?: string;
  description?: string;
  status?: 'scheduled' | 'completed' | 'cancelled';
}
