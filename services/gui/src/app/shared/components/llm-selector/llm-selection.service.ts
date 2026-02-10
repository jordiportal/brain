import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, tap, map, catchError } from 'rxjs';
import { LlmProvider } from '../../../core/models';
import { environment } from '../../../../environments/environment';

/**
 * Servicio unificado para gestión de selección LLM
 * 
 * Features:
 * - Carga centralizada de proveedores LLM
 * - Caché de modelos por proveedor (evita llamadas repetidas)
 * - Persistencia de selecciones en localStorage
 * - Un solo lugar para toda la lógica de LLM selection
 * 
 * Usado por:
 * - LlmSelectorComponent
 * - TestingComponent (legacy)
 * - ChainsComponent (legacy)
 * - SubagentsComponent (legacy)
 */
@Injectable({
  providedIn: 'root'
})
export class LlmSelectionService {
  // Signals públicas
  providers = signal<LlmProvider[]>([]);
  loadingProviders = signal(false);
  
  // Caché de modelos por proveedor: Map<providerId, models[]>
  private modelsCache = new Map<string | number, string[]>();
  loadingModels = signal(false);
  
  // Clave para localStorage
  private readonly STORAGE_KEY = 'llm_last_selection';

  constructor(private http: HttpClient) {}

  /**
   * Carga todos los proveedores LLM activos
   */
  loadProviders(): Observable<LlmProvider[]> {
    if (this.providers().length > 0) {
      return of(this.providers());
    }

    this.loadingProviders.set(true);
    
    return this.http.get<LlmProvider[]>(
      `${environment.apiUrl}/config/llm-providers?active_only=true`
    ).pipe(
      tap(providers => {
        this.providers.set(providers);
        this.loadingProviders.set(false);
      }),
      catchError(error => {
        console.error('Error loading LLM providers:', error);
        this.loadingProviders.set(false);
        return of([]);
      })
    );
  }

  /**
   * Carga modelos disponibles para un proveedor (con caché)
   */
  loadModels(provider: LlmProvider): Observable<string[]> {
    const cacheKey = provider.id;
    
    // Verificar caché
    if (this.modelsCache.has(cacheKey)) {
      return of(this.modelsCache.get(cacheKey)!);
    }

    this.loadingModels.set(true);

    const params: any = {
      provider_url: provider.baseUrl,
      provider_type: provider.type || 'ollama'
    };
    
    if (provider.apiKey) {
      params.api_key = provider.apiKey;
    }

    return this.http.get<{ models: { name: string }[] }>(
      `${environment.apiUrl}/llm/models`,
      { params }
    ).pipe(
      map(response => {
        const models = response.models.map(m => m.name);
        // Guardar en caché
        this.modelsCache.set(cacheKey, models);
        return models;
      }),
      catchError(error => {
        console.error('Error loading models:', error);
        // Fallback: usar default model del provider
        if (provider.defaultModel) {
          return of([provider.defaultModel]);
        }
        return of([]);
      }),
      tap(() => this.loadingModels.set(false))
    );
  }

  /**
   * Obtiene un proveedor por ID
   */
  getProviderById(providerId: string | number | null | undefined): LlmProvider | undefined {
    if (!providerId) return undefined;
    return this.providers().find(p => 
      p.id.toString() === providerId?.toString()
    );
  }

  /**
   * Limpia la caché de modelos (útil para forzar recarga)
   */
  clearModelsCache(): void {
    this.modelsCache.clear();
  }

  /**
   * Guarda la última selección en localStorage
   */
  saveLastSelection(context: string, providerId: string | number, model: string): void {
    try {
      const storage = JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '{}');
      storage[context] = { providerId, model, timestamp: Date.now() };
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(storage));
    } catch (e) {
      console.warn('Failed to save selection to localStorage:', e);
    }
  }

  /**
   * Recupera la última selección desde localStorage
   */
  getLastSelection(context: string): { providerId: string | number; model: string } | null {
    try {
      const storage = JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '{}');
      const saved = storage[context];
      if (saved) {
        return { providerId: saved.providerId, model: saved.model };
      }
    } catch (e) {
      console.warn('Failed to read selection from localStorage:', e);
    }
    return null;
  }

  /**
   * Construye la configuración para una ejecución
   */
  buildExecutionConfig(providerId: string | number | null | undefined, model: string | null | undefined) {
    const provider = this.getProviderById(providerId);
    if (!provider) return null;

    return {
      provider_url: provider.baseUrl,
      provider_type: provider.type || 'ollama',
      api_key: provider.apiKey,
      model: model || provider.defaultModel || ''
    };
  }
}
