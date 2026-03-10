import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { EngineTask, EngineTaskState, TaskEvent } from '../models';

export interface TaskListParams {
  context_id?: string;
  agent_id?: string;
  chain_id?: string;
  state?: EngineTaskState;
  created_by?: string;
  parent_task_id?: string;
  limit?: number;
  offset?: number;
  order_by?: string;
  order_dir?: string;
}

export interface TaskListResponse {
  tasks: EngineTask[];
  total: number;
  limit: number;
  offset: number;
}

export interface TaskEventListResponse {
  events: TaskEvent[];
}

@Injectable({ providedIn: 'root' })
export class TaskService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/engine/tasks`;

  listTasks(params: TaskListParams = {}): Observable<TaskListResponse> {
    let httpParams = new HttpParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        httpParams = httpParams.set(key, String(value));
      }
    }
    return this.http.get<TaskListResponse>(this.baseUrl, { params: httpParams });
  }

  getTask(taskId: string): Observable<EngineTask> {
    return this.http.get<EngineTask>(`${this.baseUrl}/${taskId}`);
  }

  cancelTask(taskId: string, reason?: string): Observable<EngineTask> {
    let params = new HttpParams();
    if (reason) params = params.set('reason', reason);
    return this.http.post<EngineTask>(`${this.baseUrl}/${taskId}/cancel`, null, { params });
  }

  resumeTask(taskId: string, message: string): Observable<EngineTask> {
    return this.http.post<EngineTask>(`${this.baseUrl}/${taskId}/resume`, { message });
  }

  getTaskEvents(taskId: string): Observable<TaskEventListResponse> {
    return this.http.get<TaskEventListResponse>(`${this.baseUrl}/${taskId}/events`);
  }

  getChildTasks(taskId: string): Observable<EngineTask[]> {
    return this.http.get<EngineTask[]>(`${this.baseUrl}/${taskId}/children`);
  }
}
