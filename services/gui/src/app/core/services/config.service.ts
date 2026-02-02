import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
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

/**
 * ConfigService - Servicio de configuración que accede a la API Python
 * (anteriormente StrapiService - mantiene alias para compatibilidad)
 */
@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private readonly API_URL = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ===========================================
  // LLM Providers - Ahora desde API Python
  // ===========================================

  getLlmProviders(): Observable<LlmProvider[]> {
    return this.http.get<any[]>(`${this.API_URL}/config/llm-providers`)
      .pipe(
        map(providers => providers.map(p => this.mapProviderResponse(p))),
        catchError(err => {
          console.error('Error loading LLM providers:', err);
          return of([]);
        })
      );
  }

  getLlmProvider(documentId: string): Observable<LlmProvider> {
    // Intentar buscar por ID numérico
    const id = parseInt(documentId, 10);
    if (!isNaN(id)) {
      return this.http.get<any>(`${this.API_URL}/config/llm-providers/${id}`)
        .pipe(map(p => this.mapProviderResponse(p)));
    }
    // Fallback: buscar en la lista
    return this.getLlmProviders().pipe(
      map(providers => {
        const provider = providers.find(p => p.documentId === documentId || p.id.toString() === documentId);
        if (!provider) throw new Error('Provider not found');
        return provider;
      })
    );
  }

  createLlmProvider(data: Partial<LlmProvider>): Observable<LlmProvider> {
    // Por ahora, los creates no están implementados en la API
    console.warn('createLlmProvider not implemented - use database directly');
    return of(data as LlmProvider);
  }

  updateLlmProvider(documentId: string, data: Partial<LlmProvider>): Observable<LlmProvider> {
    console.warn('updateLlmProvider not implemented - use database directly');
    return of(data as LlmProvider);
  }

  deleteLlmProvider(documentId: string): Observable<void> {
    console.warn('deleteLlmProvider not implemented - use database directly');
    return of(undefined);
  }

  private mapProviderResponse(p: any): LlmProvider {
    return {
      id: p.id,
      documentId: p.documentId || p.id?.toString(),
      name: p.name,
      type: p.type || 'ollama',
      baseUrl: p.baseUrl,
      apiKey: p.apiKey,
      defaultModel: p.defaultModel,
      embeddingModel: p.embeddingModel,
      isActive: p.isActive ?? true,
      config: p.config || {},
      description: p.description,
      createdAt: p.createdAt || new Date().toISOString(),
      updatedAt: p.updatedAt || new Date().toISOString()
    };
  }

  // ===========================================
  // MCP Connections - Ahora desde API Python
  // ===========================================

  getMcpConnections(): Observable<McpConnection[]> {
    return this.http.get<any[]>(`${this.API_URL}/config/mcp-connections`)
      .pipe(
        map(connections => connections.map(c => this.mapMcpResponse(c))),
        catchError(err => {
          console.error('Error loading MCP connections:', err);
          return of([]);
        })
      );
  }

  getMcpConnection(documentId: string): Observable<McpConnection> {
    return this.getMcpConnections().pipe(
      map(connections => {
        const conn = connections.find(c => c.documentId === documentId || c.id.toString() === documentId);
        if (!conn) throw new Error('Connection not found');
        return conn;
      })
    );
  }

  createMcpConnection(data: Partial<McpConnection>): Observable<McpConnection> {
    console.warn('createMcpConnection not implemented - use database directly');
    return of(data as McpConnection);
  }

  updateMcpConnection(documentId: string, data: Partial<McpConnection>): Observable<McpConnection> {
    console.warn('updateMcpConnection not implemented - use database directly');
    return of(data as McpConnection);
  }

  deleteMcpConnection(documentId: string): Observable<void> {
    console.warn('deleteMcpConnection not implemented - use database directly');
    return of(undefined);
  }

  private mapMcpResponse(c: any): McpConnection {
    return {
      id: c.id,
      documentId: c.documentId || c.id?.toString(),
      name: c.name,
      type: c.type || 'stdio',
      serverUrl: c.serverUrl,
      command: c.command,
      args: c.args,
      isActive: c.isActive ?? true,
      description: c.description,
      config: c.config || {},
      createdAt: c.createdAt || new Date().toISOString(),
      updatedAt: c.updatedAt || new Date().toISOString()
    };
  }

  // ===========================================
  // Brain Chains - Ahora desde API Python
  // ===========================================

  getBrainChains(params?: { populate?: string }): Observable<BrainChain[]> {
    return this.http.get<any[]>(`${this.API_URL}/config/brain-chains`)
      .pipe(
        map(chains => chains.map(c => this.mapChainResponse(c))),
        catchError(err => {
          console.error('Error loading brain chains:', err);
          return of([]);
        })
      );
  }

  getBrainChain(documentId: string): Observable<BrainChain> {
    return this.getBrainChains().pipe(
      map(chains => {
        const chain = chains.find(c => c.documentId === documentId || c.id.toString() === documentId);
        if (!chain) throw new Error('Chain not found');
        return chain;
      })
    );
  }

  createBrainChain(data: Partial<BrainChain>): Observable<BrainChain> {
    console.warn('createBrainChain not implemented - use database directly');
    return of(data as BrainChain);
  }

  updateBrainChain(documentId: string, data: Partial<BrainChain>): Observable<BrainChain> {
    console.warn('updateBrainChain not implemented - use database directly');
    return of(data as BrainChain);
  }

  deleteBrainChain(documentId: string): Observable<void> {
    console.warn('deleteBrainChain not implemented - use database directly');
    return of(undefined);
  }

  private mapChainResponse(c: any): BrainChain {
    return {
      id: c.id,
      documentId: c.documentId || c.id?.toString(),
      name: c.name,
      slug: c.slug || c.name?.toLowerCase().replace(/\s+/g, '-'),
      type: c.type || 'chain',
      description: c.description,
      version: c.version || '1.0.0',
      isActive: c.isActive ?? true,
      definition: c.definition || {},
      nodes: c.nodes,
      edges: c.edges,
      config: c.config,
      tags: c.tags,
      llmProvider: c.llmProvider,
      createdAt: c.createdAt || new Date().toISOString(),
      updatedAt: c.updatedAt || new Date().toISOString()
    };
  }

  // ===========================================
  // Execution Logs - Devuelve vacío por ahora
  // ===========================================

  getExecutionLogs(params?: { page?: number; pageSize?: number; filters?: any }): Observable<StrapiResponse<ExecutionLog>> {
    // Execution logs no están implementados en la nueva API
    return of({
      data: [],
      meta: {
        pagination: {
          page: 1,
          pageSize: 25,
          pageCount: 0,
          total: 0
        }
      }
    });
  }

  getExecutionLog(documentId: string): Observable<ExecutionLog> {
    return of({} as ExecutionLog);
  }

  // ===========================================
  // System Settings - Devuelve vacío por ahora
  // ===========================================

  getSystemSettings(category?: string): Observable<SystemSetting[]> {
    return of([]);
  }

  getSystemSetting(key: string): Observable<SystemSetting | undefined> {
    return of(undefined);
  }

  updateSystemSetting(documentId: string, value: any): Observable<SystemSetting> {
    console.warn('updateSystemSetting not implemented');
    return of({} as SystemSetting);
  }

  createSystemSetting(data: Partial<SystemSetting>): Observable<SystemSetting> {
    console.warn('createSystemSetting not implemented');
    return of(data as SystemSetting);
  }

  // ===========================================
  // System Stats - Nuevo endpoint
  // ===========================================

  getSystemStats(): Observable<{ chains: number; llmProviders: number; mcpConnections: number; executions: number }> {
    return this.http.get<any>(`${this.API_URL}/config/stats`)
      .pipe(
        map(stats => ({
          chains: stats.chains || 0,
          llmProviders: stats.llmProviders || 0,
          mcpConnections: stats.mcpConnections || 0,
          executions: 0 // No tenemos este dato aún
        })),
        catchError(err => {
          console.error('Error loading system stats:', err);
          return of({ chains: 0, llmProviders: 0, mcpConnections: 0, executions: 0 });
        })
      );
  }
}

// Alias para compatibilidad con código existente
export { ConfigService as StrapiService };
