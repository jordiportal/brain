import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BrainUser, RolePermission } from '../models';

export interface UsersListResponse {
  users: BrainUser[];
  stats: Record<string, number>;
  total: number;
}

export interface RolesListResponse {
  roles: {
    name: string;
    user_count: number;
    permissions: RolePermission[];
  }[];
}

export interface CreateUserPayload {
  email: string;
  password: string;
  firstname?: string;
  lastname?: string;
  role: string;
  is_active: boolean;
}

export interface UpdateUserPayload {
  email?: string;
  firstname?: string;
  lastname?: string;
  role?: string;
  is_active?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private readonly API = `${environment.apiUrl}/users`;

  constructor(private http: HttpClient) {}

  listUsers(includeInactive = false): Observable<UsersListResponse> {
    return this.http.get<UsersListResponse>(this.API, {
      params: includeInactive ? { include_inactive: 'true' } : {}
    });
  }

  getUser(id: number): Observable<BrainUser> {
    return this.http.get<BrainUser>(`${this.API}/${id}`);
  }

  createUser(payload: CreateUserPayload): Observable<BrainUser> {
    return this.http.post<BrainUser>(this.API, payload);
  }

  updateUser(id: number, payload: UpdateUserPayload): Observable<BrainUser> {
    return this.http.put<BrainUser>(`${this.API}/${id}`, payload);
  }

  deleteUser(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.API}/${id}`);
  }

  changeUserPassword(id: number, newPassword: string): Observable<{ message: string }> {
    return this.http.put<{ message: string }>(`${this.API}/${id}/password`, {
      new_password: newPassword
    });
  }

  listRoles(): Observable<RolesListResponse> {
    return this.http.get<RolesListResponse>(`${this.API}/roles/list`);
  }

  updateRolePermission(role: string, resource: string, actions: string[]): Observable<RolePermission> {
    return this.http.put<RolePermission>(`${this.API}/roles/${role}/permissions`, {
      resource, actions
    });
  }

  deleteRolePermission(role: string, permissionId: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.API}/roles/${role}/permissions/${permissionId}`);
  }
}
