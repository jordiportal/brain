import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface UserProfile {
  user_id: string;
  display_name?: string;
  personal_prompt?: string;
  m365_user_id?: string;
  timezone: string;
  preferences: UserPreferences;
  created_at?: string;
  updated_at?: string;
}

export interface UserPreferences {
  importantSenders?: string[];
  projectKeywords?: string[];
  mailSignature?: string;
  digestFormat?: string;
}

export interface UserTask {
  id: number;
  user_id: string;
  type: string;
  name: string;
  cron_expression: string;
  is_active: boolean;
  config?: Record<string, unknown>;
  last_run_at?: string;
  last_status?: string;
  created_at?: string;
}

export interface TaskResult {
  id: number;
  task_id: number;
  user_id: string;
  result_type: string;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
  expires_at: string;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly API = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getProfile(userId: string): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.API}/profile/${encodeURIComponent(userId)}`);
  }

  updateProfile(userId: string, data: Partial<UserProfile>): Observable<UserProfile> {
    return this.http.put<UserProfile>(`${this.API}/profile/${encodeURIComponent(userId)}`, data);
  }

  getTasks(userId: string): Observable<{ items: UserTask[] }> {
    return this.http.get<{ items: UserTask[] }>(`${this.API}/tasks`, { params: { user_id: userId } });
  }

  createTask(data: Partial<UserTask>): Observable<UserTask> {
    return this.http.post<UserTask>(`${this.API}/tasks`, data);
  }

  updateTask(id: number, data: Partial<UserTask>): Observable<UserTask> {
    return this.http.put<UserTask>(`${this.API}/tasks/${id}`, data);
  }

  deleteTask(id: number): Observable<{ deleted: boolean }> {
    return this.http.delete<{ deleted: boolean }>(`${this.API}/tasks/${id}`);
  }

  runTaskNow(id: number): Observable<{ accepted: boolean }> {
    return this.http.post<{ accepted: boolean }>(`${this.API}/tasks/${id}/run-now`, {});
  }

  getTaskResults(taskId: number, limit = 20): Observable<{ items: TaskResult[] }> {
    return this.http.get<{ items: TaskResult[] }>(`${this.API}/tasks/${taskId}/results`, { params: { limit: String(limit) } });
  }
}
