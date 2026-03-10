import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  ConversationListItem,
  ConversationDetail,
  ConversationMessage,
  MemoryFact,
  MemoryEpisode,
} from '../models';

export interface ConversationListResponse {
  conversations: ConversationListItem[];
  total: number;
}

export interface MemoryContextResponse {
  facts: MemoryFact[];
  episodes: MemoryEpisode[];
  facts_count: number;
  episodes_count: number;
}

@Injectable({ providedIn: 'root' })
export class ConversationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/conversations`;
  private readonly memoryUrl = `${environment.apiUrl}/memory`;

  listConversations(limit = 50, offset = 0): Observable<ConversationListResponse> {
    const params = new HttpParams()
      .set('limit', limit)
      .set('offset', offset);
    return this.http.get<ConversationListResponse>(this.baseUrl, { params });
  }

  getConversation(id: string): Observable<ConversationDetail> {
    return this.http.get<ConversationDetail>(`${this.baseUrl}/${id}`);
  }

  getMessages(id: string, limit = 100, before?: string): Observable<ConversationMessage[]> {
    let params = new HttpParams().set('limit', limit);
    if (before) {
      params = params.set('before', before);
    }
    return this.http.get<ConversationMessage[]>(`${this.baseUrl}/${id}/messages`, { params });
  }

  deleteConversation(id: string): Observable<{ status: string; id: string }> {
    return this.http.delete<{ status: string; id: string }>(`${this.baseUrl}/${id}`);
  }

  updateConversation(id: string, patch: { title?: string }): Observable<any> {
    return this.http.patch(`${this.baseUrl}/${id}`, patch);
  }

  getMemoryContext(userId?: string, agentId?: string): Observable<MemoryContextResponse> {
    let params = new HttpParams();
    if (userId) params = params.set('user_id', userId);
    if (agentId) params = params.set('agent_id', agentId);
    return this.http.get<MemoryContextResponse>(`${this.memoryUrl}/context`, { params });
  }
}
