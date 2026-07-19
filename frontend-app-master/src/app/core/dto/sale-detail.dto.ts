export interface SaleDetailDto {
  id?: number;
  content_type: string;
  object_id: number;
  name: string;
  quantity: number;
  price: number;
  subtotal?: number;
}

export interface CartItemDto {
  id: string;
  type: 'service' | 'product';
  item: any;
  quantity: number;
  price: number;
  subtotal: number;
}
