import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly API_URL = 'http://localhost:8000/api/v1';

  constructor(private http: HttpClient) {}

  // ===========================================
  // Health Check
  // ===========================================

  getHealth(): Observable<{ status: string; version: string }> {
    return this.http.get<{ status: string; version: string }>('http://localhost:8000/health');
  }

  // ===========================================
  // Graphs
  // ===========================================

  getGraphs(): Observable<any> {
    return this.http.get(`${this.API_URL}/graphs`);
  }

  getGraph(graphId: string): Observable<any> {
    return this.http.get(`${this.API_URL}/graphs/${graphId}`);
  }

  getGraphExecutions(graphId: string, limit: number = 10): Observable<any> {
    return this.http.get(`${this.API_URL}/graphs/${graphId}/executions?limit=${limit}`);
  }

  // ===========================================
  // Executions
  // ===========================================

  getExecution(executionId: string): Observable<any> {
    return this.http.get(`${this.API_URL}/executions/${executionId}`);
  }

  getExecutionTrace(executionId: string): Observable<any> {
    return this.http.get(`${this.API_URL}/executions/${executionId}/trace`);
  }

  // ===========================================
  // RAG
  // ===========================================

  getRagCollections(): Observable<any> {
    return this.http.get(`${this.API_URL}/rag/collections`);
  }

  ragSearch(query: string, collection?: string, topK: number = 5): Observable<any> {
    return this.http.post(`${this.API_URL}/rag/search`, null, {
      params: { query, ...(collection && { collection }), top_k: topK.toString() }
    });
  }

  // ===========================================
  // Chains
  // ===========================================

  getChains(): Observable<any> {
    return this.http.get(`${this.API_URL}/chains`);
  }

  invokeChain(chainId: string, input: any): Observable<any> {
    return this.http.post(`${this.API_URL}/chains/${chainId}/invoke`, input);
  }

  // ===========================================
  // Test LLM Connection
  // ===========================================

  testLlmConnection(provider: { type: string; baseUrl: string; apiKey?: string; model?: string }): Observable<any> {
    return this.http.post(`${this.API_URL}/llm/test`, provider);
  }
}
