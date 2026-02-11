import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface Artifact {
  id: number;
  artifact_id: string;
  type: 'image' | 'video' | 'presentation' | 'code' | 'document' | 'html' | 'audio' | 'file';
  title?: string;
  description?: string;
  file_name: string;
  file_path: string;
  mime_type?: string;
  file_size?: number;
  conversation_id?: string;
  agent_id?: string;
  source: string;
  tool_id?: string;
  metadata: Record<string, any>;
  version: number;
  is_latest: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  accessed_at: string;
}

export interface ArtifactListResponse {
  artifacts: Artifact[];
  total: number;
  page: number;
  page_size: number;
}

export interface ArtifactCreateRequest {
  type: Artifact['type'];
  title?: string;
  description?: string;
  file_path: string;
  file_name: string;
  mime_type?: string;
  file_size?: number;
  conversation_id?: string;
  agent_id?: string;
  source?: string;
  tool_id?: string;
  metadata?: Record<string, any>;
  parent_artifact_id?: number;
}

@Injectable({
  providedIn: 'root'
})
export class ArtifactService {
  private apiUrl = `${environment.apiUrl}/artifacts`;
  
  // BehaviorSubject para mantener lista actualizada
  private artifactsSubject = new BehaviorSubject<Artifact[]>([]);
  public artifacts$ = this.artifactsSubject.asObservable();
  
  constructor(private http: HttpClient) {}

  /**
   * Lista artefactos con filtros opcionales
   */
  listArtifacts(
    conversationId?: string,
    type?: Artifact['type'],
    agentId?: string,
    limit: number = 50,
    offset: number = 0
  ): Observable<ArtifactListResponse> {
    let url = `${this.apiUrl}?limit=${limit}&offset=${offset}`;
    if (conversationId) url += `&conversation_id=${conversationId}`;
    if (type) url += `&type=${type}`;
    if (agentId) url += `&agent_id=${agentId}`;
    
    return this.http.get<ArtifactListResponse>(url).pipe(
      tap(response => {
        this.artifactsSubject.next(response.artifacts);
      })
    );
  }

  /**
   * Obtiene artefactos recientes (para sidebar)
   */
  getRecentArtifacts(limit: number = 20): Observable<ArtifactListResponse> {
    return this.http.get<ArtifactListResponse>(`${this.apiUrl}/recent?limit=${limit}`).pipe(
      tap(response => {
        this.artifactsSubject.next(response.artifacts);
      })
    );
  }

  /**
   * Obtiene artefactos de una conversación
   */
  getConversationArtifacts(
    conversationId: string,
    type?: Artifact['type'],
    limit: number = 50
  ): Observable<ArtifactListResponse> {
    let url = `${this.apiUrl}/conversation/${conversationId}?limit=${limit}`;
    if (type) url += `&type=${type}`;
    return this.http.get<ArtifactListResponse>(url);
  }

  /**
   * Obtiene metadata de un artefacto
   */
  getArtifact(artifactId: string): Observable<Artifact> {
    return this.http.get<Artifact>(`${this.apiUrl}/${artifactId}`);
  }

  /**
   * Crea un nuevo artefacto
   */
  createArtifact(artifact: ArtifactCreateRequest): Observable<Artifact> {
    return this.http.post<Artifact>(this.apiUrl, artifact);
  }

  /**
   * Actualiza un artefacto
   */
  updateArtifact(
    artifactId: string,
    updates: Partial<Pick<Artifact, 'title' | 'description' | 'status' | 'metadata'>>
  ): Observable<Artifact> {
    return this.http.put<Artifact>(`${this.apiUrl}/${artifactId}`, updates);
  }

  /**
   * Elimina un artefacto
   */
  deleteArtifact(artifactId: string, soft: boolean = true): Observable<any> {
    return this.http.delete(`${this.apiUrl}/${artifactId}?soft=${soft}`);
  }

  /**
   * Obtiene la URL del contenido del artefacto
   */
  getContentUrl(artifactId: string): string {
    return `${this.apiUrl}/${artifactId}/content`;
  }

  /**
   * Obtiene la URL del viewer sandboxed
   */
  getViewerUrl(artifactId: string): string {
    return `${this.apiUrl}/${artifactId}/view`;
  }

  /**
   * Obtiene info de visualización del artefacto
   */
  getArtifactInfo(artifactId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/${artifactId}/info`);
  }

  /**
   * Descarga el archivo del artefacto
   */
  downloadArtifact(artifactId: string): Observable<Blob> {
    return this.http.get(
      `${this.apiUrl}/${artifactId}/content`,
      { responseType: 'blob' }
    );
  }

  /**
   * Filtra artefactos por tipo
   */
  filterByType(artifacts: Artifact[], type: Artifact['type'] | 'all'): Artifact[] {
    if (type === 'all') return artifacts;
    return artifacts.filter(a => a.type === type);
  }

  /**
   * Obtiene icono según tipo de artefacto
   */
  getIconForType(type: Artifact['type']): string {
    const icons: Record<string, string> = {
      'image': 'image',
      'video': 'videocam',
      'presentation': 'slideshow',
      'code': 'code',
      'document': 'description',
      'html': 'html',
      'audio': 'audiotrack',
      'file': 'insert_drive_file'
    };
    return icons[type] || 'insert_drive_file';
  }

  /**
   * Formatea tamaño de archivo
   */
  formatFileSize(bytes?: number): string {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  }

  /**
   * Formatea fecha
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Justo ahora';
    if (minutes < 60) return `Hace ${minutes} min`;
    if (hours < 24) return `Hace ${hours} h`;
    if (days === 1) return 'Ayer';
    if (days < 7) return `Hace ${days} días`;
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
  }
}
