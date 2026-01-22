import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import {
  StrapiResponse,
  StrapiSingleResponse,
  LlmProvider,
  McpConnection,
  BrainChain,
  ExecutionLog,
  SystemSetting
} from '../models';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class StrapiService {
  private readonly STRAPI_URL = environment.strapiApiUrl;

  constructor(private http: HttpClient) {}

  // ===========================================
  // LLM Providers
  // ===========================================

  getLlmProviders(): Observable<LlmProvider[]> {
    return this.http.get<StrapiResponse<LlmProvider>>(`${this.STRAPI_URL}/llm-providers`)
      .pipe(map(res => res.data));
  }

  getLlmProvider(documentId: string): Observable<LlmProvider> {
    return this.http.get<StrapiSingleResponse<LlmProvider>>(`${this.STRAPI_URL}/llm-providers/${documentId}`)
      .pipe(map(res => res.data));
  }

  createLlmProvider(data: Partial<LlmProvider>): Observable<LlmProvider> {
    return this.http.post<StrapiSingleResponse<LlmProvider>>(`${this.STRAPI_URL}/llm-providers`, { data })
      .pipe(map(res => res.data));
  }

  updateLlmProvider(documentId: string, data: Partial<LlmProvider>): Observable<LlmProvider> {
    return this.http.put<StrapiSingleResponse<LlmProvider>>(`${this.STRAPI_URL}/llm-providers/${documentId}`, { data })
      .pipe(map(res => res.data));
  }

  deleteLlmProvider(documentId: string): Observable<void> {
    return this.http.delete<void>(`${this.STRAPI_URL}/llm-providers/${documentId}`);
  }

  // ===========================================
  // MCP Connections
  // ===========================================

  getMcpConnections(): Observable<McpConnection[]> {
    return this.http.get<StrapiResponse<McpConnection>>(`${this.STRAPI_URL}/mcp-connections`)
      .pipe(map(res => res.data));
  }

  getMcpConnection(documentId: string): Observable<McpConnection> {
    return this.http.get<StrapiSingleResponse<McpConnection>>(`${this.STRAPI_URL}/mcp-connections/${documentId}`)
      .pipe(map(res => res.data));
  }

  createMcpConnection(data: Partial<McpConnection>): Observable<McpConnection> {
    return this.http.post<StrapiSingleResponse<McpConnection>>(`${this.STRAPI_URL}/mcp-connections`, { data })
      .pipe(map(res => res.data));
  }

  updateMcpConnection(documentId: string, data: Partial<McpConnection>): Observable<McpConnection> {
    return this.http.put<StrapiSingleResponse<McpConnection>>(`${this.STRAPI_URL}/mcp-connections/${documentId}`, { data })
      .pipe(map(res => res.data));
  }

  deleteMcpConnection(documentId: string): Observable<void> {
    return this.http.delete<void>(`${this.STRAPI_URL}/mcp-connections/${documentId}`);
  }

  // ===========================================
  // Brain Chains
  // ===========================================

  getBrainChains(params?: { populate?: string }): Observable<BrainChain[]> {
    let httpParams = new HttpParams();
    if (params?.populate) {
      httpParams = httpParams.set('populate', params.populate);
    }
    return this.http.get<StrapiResponse<BrainChain>>(`${this.STRAPI_URL}/brain-chains`, { params: httpParams })
      .pipe(map(res => res.data));
  }

  getBrainChain(documentId: string): Observable<BrainChain> {
    return this.http.get<StrapiSingleResponse<BrainChain>>(`${this.STRAPI_URL}/brain-chains/${documentId}?populate=*`)
      .pipe(map(res => res.data));
  }

  createBrainChain(data: Partial<BrainChain>): Observable<BrainChain> {
    return this.http.post<StrapiSingleResponse<BrainChain>>(`${this.STRAPI_URL}/brain-chains`, { data })
      .pipe(map(res => res.data));
  }

  updateBrainChain(documentId: string, data: Partial<BrainChain>): Observable<BrainChain> {
    return this.http.put<StrapiSingleResponse<BrainChain>>(`${this.STRAPI_URL}/brain-chains/${documentId}`, { data })
      .pipe(map(res => res.data));
  }

  deleteBrainChain(documentId: string): Observable<void> {
    return this.http.delete<void>(`${this.STRAPI_URL}/brain-chains/${documentId}`);
  }

  // ===========================================
  // Execution Logs
  // ===========================================

  getExecutionLogs(params?: { page?: number; pageSize?: number; filters?: any }): Observable<StrapiResponse<ExecutionLog>> {
    let httpParams = new HttpParams()
      .set('populate', '*')
      .set('sort', 'createdAt:desc');
    
    if (params?.page) {
      httpParams = httpParams.set('pagination[page]', params.page.toString());
    }
    if (params?.pageSize) {
      httpParams = httpParams.set('pagination[pageSize]', params.pageSize.toString());
    }
    
    return this.http.get<StrapiResponse<ExecutionLog>>(`${this.STRAPI_URL}/execution-logs`, { params: httpParams });
  }

  getExecutionLog(documentId: string): Observable<ExecutionLog> {
    return this.http.get<StrapiSingleResponse<ExecutionLog>>(`${this.STRAPI_URL}/execution-logs/${documentId}?populate=*`)
      .pipe(map(res => res.data));
  }

  // ===========================================
  // System Settings
  // ===========================================

  getSystemSettings(category?: string): Observable<SystemSetting[]> {
    let httpParams = new HttpParams();
    if (category) {
      httpParams = httpParams.set('filters[category][$eq]', category);
    }
    return this.http.get<StrapiResponse<SystemSetting>>(`${this.STRAPI_URL}/system-settings`, { params: httpParams })
      .pipe(map(res => res.data));
  }

  getSystemSetting(key: string): Observable<SystemSetting | undefined> {
    const params = new HttpParams().set('filters[key][$eq]', key);
    return this.http.get<StrapiResponse<SystemSetting>>(`${this.STRAPI_URL}/system-settings`, { params })
      .pipe(map(res => res.data[0]));
  }

  updateSystemSetting(documentId: string, value: any): Observable<SystemSetting> {
    return this.http.put<StrapiSingleResponse<SystemSetting>>(
      `${this.STRAPI_URL}/system-settings/${documentId}`,
      { data: { value } }
    ).pipe(map(res => res.data));
  }

  createSystemSetting(data: Partial<SystemSetting>): Observable<SystemSetting> {
    return this.http.post<StrapiSingleResponse<SystemSetting>>(`${this.STRAPI_URL}/system-settings`, { data })
      .pipe(map(res => res.data));
  }
}
