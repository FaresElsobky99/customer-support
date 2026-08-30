export type UserRole = 'admin' | 'customer';

export interface LoginResponse {
  token: string;
  customer_id: number;
  role: UserRole;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
  status: string;
  role?: UserRole;
}

export interface CustomerListResponse {
  customers: Customer[];
}
