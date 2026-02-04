import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { MatBadgeModule } from '@angular/material/badge';
import { environment } from '../../../environments/environment';

interface OpenAPIConnection {
  id: string;
  name: string;
  slug: string;
  specUrl: string;
  baseUrl: string;
  authType: string;
  hasAuth: boolean;
  timeout: number;
}

interface Tool {
  id: string;
  name: string;
  description: string;
  type: string;
  connection_id?: string;
  method?: string;
  path?: string;
}

interface CoreToolConfig {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  config: Record<string, any>;
  configSchema: ConfigField[];
}

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'select' | 'number' | 'boolean';
  options?: { value: string; label: string }[];
  placeholder?: string;
  hint?: string;
}

@Component({
  selector: 'app-tools',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatTooltipModule,
    MatTabsModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatExpansionModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTableModule,
    MatBadgeModule
  ],
  template: `
    <div class="tools-page">
      <div class="page-header">
        <div>
          <h1>Herramientas</h1>
          <p class="subtitle">Conexiones OpenAPI y herramientas para agentes</p>
        </div>
        <button mat-raised-button color="primary" (click)="refreshConnections()" [disabled]="refreshingConnections()">
          @if (refreshingConnections()) {
            <mat-spinner diameter="20"></mat-spinner>
          } @else {
            <mat-icon>refresh</mat-icon>
          }
          Refrescar desde Strapi
        </button>
      </div>

      <mat-tab-group>
        <!-- Tab de Conexiones -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>cloud</mat-icon>
            <span class="tab-label">Conexiones</span>
            <span class="badge" *ngIf="connections().length">{{ connections().length }}</span>
          </ng-template>

          <!-- Lista de conexiones -->
          @if (loadingConnections()) {
            <div class="loading-container">
              <mat-spinner diameter="48"></mat-spinner>
              <p>Cargando conexiones...</p>
            </div>
          } @else {
            <div class="connections-grid">
              @for (conn of connections(); track conn.id) {
                <mat-card class="connection-card">
                  <mat-card-header>
                    <div class="connection-icon">
                      <mat-icon>api</mat-icon>
                    </div>
                    <mat-card-title>{{ conn.name }}</mat-card-title>
                    <mat-card-subtitle>{{ conn.baseUrl }}</mat-card-subtitle>
                  </mat-card-header>
                  
                  <mat-card-content>
                    <div class="connection-details">
                      <div class="detail-row">
                        <span class="label">Spec URL:</span>
                        <span class="value truncate">{{ conn.specUrl }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="label">Auth:</span>
                        <mat-chip [class]="conn.authType">
                          {{ conn.authType | uppercase }}
                          @if (conn.hasAuth) {
                            <mat-icon>check</mat-icon>
                          }
                        </mat-chip>
                      </div>
                      <div class="detail-row">
                        <span class="label">Tools:</span>
                        <span class="value">{{ getToolCount(conn.id) }} herramientas</span>
                      </div>
                    </div>
                  </mat-card-content>

                  <mat-card-actions align="end">
                    <button mat-button color="primary" (click)="generateTools(conn.id)" [disabled]="generatingTools()">
                      @if (generatingTools() && generatingConnectionId === conn.id) {
                        <mat-spinner diameter="20"></mat-spinner>
                      } @else {
                        <mat-icon>build</mat-icon>
                      }
                      Generar Tools
                    </button>
                    <button mat-button (click)="testConnection(conn.id)">
                      <mat-icon>play_arrow</mat-icon>
                      Probar
                    </button>
                  </mat-card-actions>
                </mat-card>
              } @empty {
                <div class="empty-state">
                  <mat-icon>cloud_off</mat-icon>
                  <h3>No hay conexiones configuradas</h3>
                  <p>Las conexiones OpenAPI se configuran desde la API.</p>
                  <button mat-raised-button color="primary" (click)="refreshConnections()">
                    <mat-icon>refresh</mat-icon>
                    Refrescar
                  </button>
                </div>
              }
            </div>
          }
        </mat-tab>

        <!-- Tab de Herramientas -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>build</mat-icon>
            <span class="tab-label">Herramientas</span>
            <span class="badge" *ngIf="tools().length">{{ tools().length }}</span>
          </ng-template>

          <div class="tools-header">
            <mat-form-field appearance="outline" class="search-field">
              <mat-label>Buscar herramienta</mat-label>
              <input matInput [(ngModel)]="searchTerm" placeholder="sales, products...">
              <mat-icon matSuffix>search</mat-icon>
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Filtrar por tipo</mat-label>
              <mat-select [(ngModel)]="filterType" (ngModelChange)="loadTools()">
                <mat-option value="">Todos</mat-option>
                <mat-option value="openapi">OpenAPI</mat-option>
                <mat-option value="builtin">Builtin</mat-option>
              </mat-select>
            </mat-form-field>

            <button mat-raised-button (click)="loadTools()">
              <mat-icon>refresh</mat-icon>
              Recargar
            </button>
          </div>

          @if (loadingTools()) {
            <div class="loading-container">
              <mat-spinner diameter="48"></mat-spinner>
              <p>Cargando herramientas...</p>
            </div>
          } @else {
            <div class="tools-list">
              @for (tool of filteredTools(); track tool.id) {
                <mat-expansion-panel>
                  <mat-expansion-panel-header>
                    <mat-panel-title>
                      <mat-chip [class]="tool.type" class="type-chip">{{ tool.type }}</mat-chip>
                      @if (tool.method) {
                        <mat-chip [class]="tool.method.toLowerCase()" class="method-chip">{{ tool.method }}</mat-chip>
                      }
                      <span class="tool-name">{{ tool.name }}</span>
                    </mat-panel-title>
                    <mat-panel-description>
                      {{ tool.description | slice:0:60 }}{{ tool.description.length > 60 ? '...' : '' }}
                    </mat-panel-description>
                  </mat-expansion-panel-header>

                  <div class="tool-details">
                    <p class="description">{{ tool.description }}</p>
                    
                    @if (tool.path) {
                      <div class="detail-item">
                        <strong>Path:</strong> <code>{{ tool.path }}</code>
                      </div>
                    }
                    
                    @if (tool.connection_id) {
                      <div class="detail-item">
                        <strong>Conexión:</strong> {{ tool.connection_id }}
                      </div>
                    }

                    <div class="tool-actions">
                      <button mat-raised-button color="primary" (click)="openTestTool(tool)">
                        <mat-icon>play_arrow</mat-icon>
                        Probar Herramienta
                      </button>
                      <button mat-button (click)="copyToolId(tool.id)">
                        <mat-icon>content_copy</mat-icon>
                        Copiar ID
                      </button>
                    </div>
                  </div>
                </mat-expansion-panel>
              } @empty {
                <div class="empty-state">
                  <mat-icon>build_circle</mat-icon>
                  <h3>No hay herramientas</h3>
                  <p>Genera herramientas desde una conexión OpenAPI</p>
                </div>
              }
            </div>
          }
        </mat-tab>

        <!-- Tab de Pruebas -->
        <mat-tab label="Probar Herramienta" [disabled]="!selectedTool">
          @if (selectedTool) {
            <div class="test-panel">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>{{ selectedTool.name }}</mat-card-title>
                  <mat-card-subtitle>{{ selectedTool.description }}</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Parámetros (JSON)</mat-label>
                    <textarea matInput [(ngModel)]="testParams" rows="5" 
                              placeholder='{"limit": 5}'></textarea>
                  </mat-form-field>
                </mat-card-content>
                <mat-card-actions>
                  <button mat-raised-button color="primary" 
                          [disabled]="executingTool()"
                          (click)="executeTool()">
                    @if (executingTool()) {
                      <mat-spinner diameter="20"></mat-spinner>
                    } @else {
                      <mat-icon>play_arrow</mat-icon>
                    }
                    Ejecutar
                  </button>
                </mat-card-actions>
              </mat-card>

              @if (toolResult()) {
                <mat-card class="result-card">
                  <mat-card-header>
                    <mat-card-title>Resultado</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <pre class="result-json">{{ toolResult() | json }}</pre>
                  </mat-card-content>
                </mat-card>
              }
            </div>
          }
        </mat-tab>

        <!-- Tab de Configuración de Herramientas Core -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>settings</mat-icon>
            <span class="tab-label">Configuración</span>
          </ng-template>

          <div class="core-tools-config">
            <div class="config-header">
              <h2>Configuración de Herramientas</h2>
              <p>Configura los proveedores y parámetros por defecto de las herramientas del sistema</p>
            </div>

            @if (loadingCoreConfig()) {
              <div class="loading-container">
                <mat-spinner diameter="48"></mat-spinner>
                <p>Cargando configuración...</p>
              </div>
            } @else {
              <div class="core-tools-grid">
                @for (tool of coreToolConfigs(); track tool.id) {
                  <mat-card class="core-tool-card" [id]="'tool-config-' + tool.id">
                    <mat-card-header>
                      <div class="tool-icon" [ngClass]="tool.category">
                        <mat-icon>{{ tool.icon }}</mat-icon>
                      </div>
                      <mat-card-title>{{ tool.name }}</mat-card-title>
                      <mat-card-subtitle>{{ tool.description }}</mat-card-subtitle>
                    </mat-card-header>

                    <mat-card-content>
                      <div class="config-fields">
                        @for (field of tool.configSchema; track field.key) {
                          @if (field.type === 'select') {
                            <mat-form-field appearance="outline" class="full-width">
                              <mat-label>{{ field.label }}</mat-label>
                              <mat-select [(ngModel)]="tool.config[field.key]">
                                @for (opt of field.options; track opt.value) {
                                  <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                                }
                              </mat-select>
                              @if (field.hint) {
                                <mat-hint>{{ field.hint }}</mat-hint>
                              }
                            </mat-form-field>
                          } @else if (field.type === 'text') {
                            <mat-form-field appearance="outline" class="full-width">
                              <mat-label>{{ field.label }}</mat-label>
                              <input matInput [(ngModel)]="tool.config[field.key]" 
                                     [placeholder]="field.placeholder || ''">
                              @if (field.hint) {
                                <mat-hint>{{ field.hint }}</mat-hint>
                              }
                            </mat-form-field>
                          } @else if (field.type === 'number') {
                            <mat-form-field appearance="outline" class="full-width">
                              <mat-label>{{ field.label }}</mat-label>
                              <input matInput type="number" [(ngModel)]="tool.config[field.key]" 
                                     [placeholder]="field.placeholder || ''">
                              @if (field.hint) {
                                <mat-hint>{{ field.hint }}</mat-hint>
                              }
                            </mat-form-field>
                          }
                        }
                      </div>
                    </mat-card-content>

                    <mat-card-actions align="end">
                      <button mat-button color="primary" (click)="saveCoreToolConfig(tool)" 
                              [disabled]="savingToolConfig() === tool.id">
                        @if (savingToolConfig() === tool.id) {
                          <mat-spinner diameter="20"></mat-spinner>
                        } @else {
                          <mat-icon>save</mat-icon>
                        }
                        Guardar
                      </button>
                    </mat-card-actions>
                  </mat-card>
                }
              </div>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .tools-page {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
    }

    .subtitle {
      color: #666;
      margin: 4px 0 0;
    }

    .tab-label {
      margin-left: 8px;
    }

    .badge {
      margin-left: 8px;
      background: #667eea;
      color: white;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px;
      color: #666;
    }

    /* Connection Form */
    .connection-form {
      margin: 24px 0;
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }

    .full-width {
      grid-column: 1 / -1;
    }

    /* Connections Grid */
    .connections-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 20px;
      padding: 24px 0;
    }

    .connection-card {
      border-radius: 12px;
    }

    .connection-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .connection-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .connection-details {
      margin-top: 16px;
    }

    .detail-row {
      display: flex;
      align-items: center;
      margin-bottom: 8px;
    }

    .detail-row .label {
      width: 80px;
      color: #888;
      font-size: 13px;
    }

    .detail-row .value {
      flex: 1;
      font-size: 13px;
    }

    .truncate {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 250px;
    }

    /* Tools Header */
    .tools-header {
      display: flex;
      gap: 16px;
      padding: 24px 0;
      align-items: flex-start;
    }

    .search-field {
      flex: 1;
    }

    /* Tools List */
    .tools-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .type-chip {
      font-size: 10px !important;
      min-height: 20px !important;
      padding: 0 8px !important;
    }

    .type-chip.openapi { background: #e3f2fd !important; color: #1976d2 !important; }
    .type-chip.builtin { background: #f3e5f5 !important; color: #7b1fa2 !important; }

    .method-chip {
      font-size: 10px !important;
      min-height: 20px !important;
      padding: 0 8px !important;
      margin-left: 8px !important;
    }

    .method-chip.get { background: #e8f5e9 !important; color: #388e3c !important; }
    .method-chip.post { background: #fff3e0 !important; color: #f57c00 !important; }
    .method-chip.put { background: #e3f2fd !important; color: #1976d2 !important; }
    .method-chip.patch { background: #fce4ec !important; color: #c2185b !important; }
    .method-chip.delete { background: #ffebee !important; color: #d32f2f !important; }

    .tool-name {
      margin-left: 12px;
      font-weight: 500;
    }

    .tool-details {
      padding: 16px 0;
    }

    .tool-details .description {
      color: #666;
      margin-bottom: 16px;
    }

    .detail-item {
      margin-bottom: 8px;
      font-size: 13px;
    }

    .detail-item code {
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .tool-actions {
      margin-top: 16px;
      display: flex;
      gap: 12px;
    }

    /* Empty State */
    .empty-state {
      text-align: center;
      padding: 64px;
      background: white;
      border-radius: 12px;
      grid-column: 1 / -1;
    }

    .empty-state mat-icon {
      font-size: 72px;
      width: 72px;
      height: 72px;
      color: #ccc;
    }

    /* Test Panel */
    .test-panel {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .result-card {
      background: #1a1a2e;
    }

    .result-card mat-card-header {
      color: white;
    }

    .result-json {
      background: #1a1a2e;
      color: #e0e0e0;
      padding: 16px;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 12px;
      max-height: 400px;
      overflow-y: auto;
    }

    mat-chip.bearer, mat-chip.apikey { background: #e8f5e9 !important; color: #388e3c !important; }
    mat-chip.none { background: #f5f5f5 !important; color: #888 !important; }

    /* Core Tools Config */
    .core-tools-config {
      padding: 24px 0;
    }

    .config-header {
      margin-bottom: 24px;
    }

    .config-header h2 {
      margin: 0 0 8px;
      font-size: 20px;
      font-weight: 500;
    }

    .config-header p {
      color: #666;
      margin: 0;
    }

    .core-tools-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
      gap: 20px;
    }

    .core-tool-card {
      border-radius: 12px;
    }

    .tool-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .tool-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .tool-icon.media { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .tool-icon.web { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .tool-icon.ai { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .tool-icon.filesystem { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }

    .config-fields {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 16px;
    }
  `]
})
export class ToolsComponent implements OnInit {
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);

  connections = signal<OpenAPIConnection[]>([]);
  tools = signal<Tool[]>([]);
  loadingConnections = signal(true);
  loadingTools = signal(false);
  generatingTools = signal(false);
  executingTool = signal(false);
  refreshingConnections = signal(false);
  toolResult = signal<any>(null);
  
  // Core tools config
  coreToolConfigs = signal<CoreToolConfig[]>([]);
  loadingCoreConfig = signal(false);
  savingToolConfig = signal<string | null>(null);

  generatingConnectionId = '';
  searchTerm = '';
  filterType = '';
  selectedTool: Tool | null = null;
  testParams = '{}';

  ngOnInit(): void {
    this.loadConnections();
    this.loadTools();
    this.loadCoreToolConfigs();
  }
  
  loadCoreToolConfigs(): void {
    this.loadingCoreConfig.set(true);
    
    // Por ahora, definir configuración localmente (TODO: cargar desde backend)
    const defaultConfigs: CoreToolConfig[] = [
      {
        id: 'generate_image',
        name: 'Generación de Imágenes',
        description: 'Configura el proveedor para generar imágenes con IA',
        icon: 'image',
        category: 'media',
        config: {
          provider: 'openai',
          model: 'dall-e-3',
          size: '1024x1024',
          quality: 'standard',
          style: 'vivid'
        },
        configSchema: [
          {
            key: 'provider',
            label: 'Proveedor',
            type: 'select',
            options: [
              { value: 'openai', label: 'OpenAI (DALL-E)' },
              { value: 'replicate', label: 'Replicate (Flux/SD)' },
              { value: 'stability', label: 'Stability AI' }
            ],
            hint: 'API para generar imágenes'
          },
          {
            key: 'model',
            label: 'Modelo',
            type: 'select',
            options: [
              { value: 'dall-e-3', label: 'DALL-E 3 (mejor calidad)' },
              { value: 'dall-e-2', label: 'DALL-E 2 (más rápido)' },
              { value: 'flux-schnell', label: 'Flux Schnell' },
              { value: 'sdxl', label: 'Stable Diffusion XL' }
            ]
          },
          {
            key: 'size',
            label: 'Tamaño por defecto',
            type: 'select',
            options: [
              { value: '1024x1024', label: '1024x1024 (Cuadrado)' },
              { value: '1792x1024', label: '1792x1024 (Paisaje)' },
              { value: '1024x1792', label: '1024x1792 (Retrato)' }
            ]
          },
          {
            key: 'quality',
            label: 'Calidad',
            type: 'select',
            options: [
              { value: 'standard', label: 'Estándar' },
              { value: 'hd', label: 'HD (más detalle)' }
            ]
          }
        ]
      },
      {
        id: 'analyze_image',
        name: 'Análisis de Imágenes',
        description: 'Configura el modelo visual para analizar imágenes',
        icon: 'visibility',
        category: 'ai',
        config: {
          provider: 'openai',
          model: 'gpt-4o'
        },
        configSchema: [
          {
            key: 'provider',
            label: 'Proveedor',
            type: 'select',
            options: [
              { value: 'openai', label: 'OpenAI (GPT-4o)' },
              { value: 'ollama', label: 'Ollama (LLaVA)' },
              { value: 'anthropic', label: 'Anthropic (Claude)' }
            ]
          },
          {
            key: 'model',
            label: 'Modelo',
            type: 'text',
            placeholder: 'gpt-4o, llava, claude-3-5-sonnet',
            hint: 'Modelo con capacidad visual'
          }
        ]
      },
      {
        id: 'web_search',
        name: 'Búsqueda Web',
        description: 'Configura el proveedor de búsqueda web',
        icon: 'search',
        category: 'web',
        config: {
          provider: 'tavily',
          max_results: 10
        },
        configSchema: [
          {
            key: 'provider',
            label: 'Proveedor',
            type: 'select',
            options: [
              { value: 'tavily', label: 'Tavily (recomendado)' },
              { value: 'serper', label: 'Serper (Google)' },
              { value: 'duckduckgo', label: 'DuckDuckGo (gratis)' }
            ]
          },
          {
            key: 'max_results',
            label: 'Resultados máximos',
            type: 'number',
            placeholder: '10'
          }
        ]
      }
    ];
    
    // Cargar config guardada desde el backend
    this.http.get<any>(`${environment.apiUrl}/tools/config`)
      .subscribe({
        next: (response) => {
          // Mezclar configuración guardada con defaults
          const savedConfigs = response.configs || {};
          defaultConfigs.forEach(tool => {
            if (savedConfigs[tool.id]) {
              tool.config = { ...tool.config, ...savedConfigs[tool.id] };
            }
          });
          this.coreToolConfigs.set(defaultConfigs);
          this.loadingCoreConfig.set(false);
        },
        error: () => {
          // Si falla, usar defaults
          this.coreToolConfigs.set(defaultConfigs);
          this.loadingCoreConfig.set(false);
        }
      });
  }
  
  saveCoreToolConfig(tool: CoreToolConfig): void {
    this.savingToolConfig.set(tool.id);
    
    this.http.put<any>(`${environment.apiUrl}/tools/config/${tool.id}`, tool.config)
      .subscribe({
        next: () => {
          this.snackBar.open(`Configuración de ${tool.name} guardada`, 'Cerrar', { duration: 3000 });
          this.savingToolConfig.set(null);
        },
        error: (err) => {
          this.snackBar.open('Error guardando configuración', 'Cerrar', { duration: 3000 });
          this.savingToolConfig.set(null);
        }
      });
  }
  
  // Navegar a la configuración de una herramienta específica (para links externos)
  scrollToToolConfig(toolId: string): void {
    const element = document.getElementById(`tool-config-${toolId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      element.classList.add('highlight');
      setTimeout(() => element.classList.remove('highlight'), 2000);
    }
  }

  loadConnections(): void {
    this.loadingConnections.set(true);
    this.http.get<any>(`${environment.apiUrl}/tools/openapi/connections`)
      .subscribe({
        next: (response) => {
          this.connections.set(response.connections || []);
          this.loadingConnections.set(false);
        },
        error: (err) => {
          console.error('Error loading connections:', err);
          this.loadingConnections.set(false);
        }
      });
  }

  loadTools(): void {
    this.loadingTools.set(true);
    let url = `${environment.apiUrl}/tools`;
    if (this.filterType) {
      url += `?type=${this.filterType}`;
    }
    
    this.http.get<any>(url)
      .subscribe({
        next: (response) => {
          this.tools.set(response.tools || []);
          this.loadingTools.set(false);
        },
        error: (err) => {
          console.error('Error loading tools:', err);
          this.loadingTools.set(false);
        }
      });
  }

  filteredTools(): Tool[] {
    if (!this.searchTerm) return this.tools();
    const term = this.searchTerm.toLowerCase();
    return this.tools().filter(t => 
      t.name.toLowerCase().includes(term) || 
      t.description.toLowerCase().includes(term)
    );
  }

  getToolCount(connectionId: string): number {
    return this.tools().filter(t => t.connection_id === connectionId).length;
  }

  refreshConnections(): void {
    this.refreshingConnections.set(true);
    
    this.http.post<any>(`${environment.apiUrl}/tools/openapi/connections/refresh`, {})
      .subscribe({
        next: (response) => {
          this.snackBar.open(`${response.count} conexiones cargadas desde Strapi`, 'Cerrar', { duration: 3000 });
          this.refreshingConnections.set(false);
          this.loadConnections();
        },
        error: (err) => {
          this.snackBar.open('Error refrescando conexiones', 'Cerrar', { duration: 3000 });
          this.refreshingConnections.set(false);
        }
      });
  }

  generateTools(connectionId: string): void {
    this.generatingTools.set(true);
    this.generatingConnectionId = connectionId;
    
    this.http.post<any>(`${environment.apiUrl}/tools/openapi/connections/${connectionId}/generate-tools`, {})
      .subscribe({
        next: (response) => {
          this.snackBar.open(`${response.tools?.length || 0} herramientas generadas`, 'Cerrar', { duration: 3000 });
          this.generatingTools.set(false);
          this.loadTools();
        },
        error: (err) => {
          this.snackBar.open('Error generando herramientas', 'Cerrar', { duration: 3000 });
          this.generatingTools.set(false);
        }
      });
  }

  testConnection(connectionId: string): void {
    // Obtener spec info
    this.http.get<any>(`${environment.apiUrl}/tools/openapi/connections/${connectionId}/spec`)
      .subscribe({
        next: (response) => {
          this.snackBar.open(`Conexión OK - ${response.spec.paths_count} endpoints`, 'Cerrar', { duration: 3000 });
        },
        error: (err) => {
          this.snackBar.open('Error conectando', 'Cerrar', { duration: 3000 });
        }
      });
  }

  openTestTool(tool: Tool): void {
    this.selectedTool = tool;
    this.testParams = '{}';
    this.toolResult.set(null);
  }

  executeTool(): void {
    if (!this.selectedTool) return;

    this.executingTool.set(true);
    this.toolResult.set(null);

    let params = {};
    try {
      params = JSON.parse(this.testParams);
    } catch (e) {
      this.snackBar.open('JSON inválido', 'Cerrar', { duration: 3000 });
      this.executingTool.set(false);
      return;
    }

    this.http.post<any>(`${environment.apiUrl}/tools/${this.selectedTool.id}/execute`, params)
      .subscribe({
        next: (response) => {
          this.toolResult.set(response.result);
          this.executingTool.set(false);
        },
        error: (err) => {
          this.toolResult.set({ error: err.message || 'Error ejecutando herramienta' });
          this.executingTool.set(false);
        }
      });
  }

  copyToolId(toolId: string): void {
    navigator.clipboard.writeText(toolId);
    this.snackBar.open('ID copiado', 'Cerrar', { duration: 2000 });
  }
}
