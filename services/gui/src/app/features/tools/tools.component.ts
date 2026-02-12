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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatChipListboxChange } from '@angular/material/chips';
import { environment } from '../../../environments/environment';

interface OpenAPIConnection {
  id: string;
  name: string;
  slug: string;
  description?: string;
  specUrl: string;
  baseUrl: string;
  authType: string;
  hasAuth: boolean;
  authToken?: string;
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

// Interfaces para herramientas configurables (del backend)
interface VisibilityCondition {
  field: string;
  value?: string;
  values?: string[];
  not_value?: string;
  not_values?: string[];
}

interface ValidationRule {
  min?: number;
  max?: number;
  min_length?: number;
  max_length?: number;
  pattern?: string;
  pattern_message?: string;
}

interface ConfigField {
  key: string;
  label: string;
  type: 'text' | 'select' | 'multiselect' | 'number' | 'boolean' | 'password' | 'text_array';
  options?: { value: string; label: string }[];
  options_depend_on?: string;
  dynamic_options?: Record<string, { value: string; label: string }[]>;
  default?: any;
  hint?: string;
  placeholder?: string;
  required?: boolean;
  visible_when?: VisibilityCondition;
  validation?: ValidationRule;
  group?: string;
  admin_only?: boolean;
  order?: number;
}

interface ConfigurableTool {
  id: string;
  display_name: string;
  description: string;
  icon: string;
  category: string;
  config_schema: ConfigField[];
  default_config: Record<string, any>;
  config: Record<string, any>;
  requires_api_key?: boolean;
  supported_providers?: string[];
  admin_only?: boolean;
  enabled_by_default?: boolean;
}

// Alias para compatibilidad
interface CoreToolConfig {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  config: Record<string, any>;
  configSchema: ConfigField[];
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
    MatBadgeModule,
    MatSlideToggleModule
  ],
  template: `
    <div class="tools-page">
      <div class="page-header">
        <div>
          <h1>Herramientas</h1>
          <p class="subtitle">Conexiones OpenAPI y herramientas para agentes</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="accent" (click)="openNewConnectionDialog()">
            <mat-icon>add</mat-icon>
            Nueva Conexión
          </button>
          <button mat-raised-button color="primary" (click)="refreshConnections()" [disabled]="refreshingConnections()">
            @if (refreshingConnections()) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              <mat-icon>refresh</mat-icon>
            }
            Refrescar
          </button>
        </div>
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
                    <div class="connection-icon" mat-card-avatar>
                      <mat-icon>api</mat-icon>
                    </div>
                    <mat-card-title>{{ conn.name }}</mat-card-title>
                    <mat-card-subtitle>{{ conn.baseUrl }}</mat-card-subtitle>
                  </mat-card-header>
                  
                  <mat-card-content>
                    <div class="connection-details">
                      <p class="description">{{ conn.description || 'Conexión OpenAPI configurada' }}</p>
                      <div class="detail-row">
                        <span class="label">Spec:</span>
                        <span class="value truncate">{{ conn.specUrl }}</span>
                      </div>
                      <div class="detail-row">
                        <span class="label">Auth:</span>
                        <mat-chip [class]="conn.authType" class="auth-chip">
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
                    <button mat-button (click)="openEditConnectionDialog(conn)">
                      <mat-icon>edit</mat-icon>
                      Editar
                    </button>
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
            <span class="badge" *ngIf="coreToolConfigs().length">{{ coreToolConfigs().length }}</span>
          </ng-template>

          <div class="core-tools-config">
            <div class="config-header">
              <h2>Configuración de Herramientas</h2>
              <p>Configura los proveedores y parámetros por defecto de las herramientas del sistema</p>
              
              <!-- Filtro por categoría -->
              @if (toolCategories().length > 1) {
                <div class="category-filter">
                  <mat-chip-listbox [(ngModel)]="selectedCategory" (change)="selectedCategory.set($event.value)">
                    <mat-chip-option [value]="null">Todas</mat-chip-option>
                    @for (cat of toolCategories(); track cat) {
                      <mat-chip-option [value]="cat">{{ cat | titlecase }}</mat-chip-option>
                    }
                  </mat-chip-listbox>
                </div>
              }
            </div>

            @if (loadingCoreConfig()) {
              <div class="loading-container">
                <mat-spinner diameter="48"></mat-spinner>
                <p>Cargando configuración desde el servidor...</p>
              </div>
            } @else if (coreToolConfigs().length === 0) {
              <div class="empty-state">
                <mat-icon>settings_suggest</mat-icon>
                <h3>No hay herramientas configurables</h3>
                <p>Las herramientas configurables se cargan desde el backend.</p>
                <button mat-raised-button color="primary" (click)="loadCoreToolConfigs()">
                  <mat-icon>refresh</mat-icon>
                  Reintentar
                </button>
              </div>
            } @else {
              <div class="core-tools-grid">
                @for (tool of getFilteredTools(); track tool.id) {
                  <mat-card class="core-tool-card" [id]="'tool-config-' + tool.id">
                    <mat-card-header>
                      <div class="tool-icon" [ngClass]="tool.category" mat-card-avatar>
                        <mat-icon>{{ tool.icon }}</mat-icon>
                      </div>
                      <div>
                        <mat-card-title>{{ tool.name }}</mat-card-title>
                        <mat-card-subtitle>{{ tool.description }}</mat-card-subtitle>
                      </div>
                    </mat-card-header>

                    <mat-card-content>
                      <div class="config-fields">
                        @for (field of tool.configSchema; track field.key) {
                          @if (shouldShowField(field, tool.config)) {
                            @switch (field.type) {
                              @case ('select') {
                                <mat-form-field appearance="outline" class="full-width">
                                  <mat-label>{{ field.label }}</mat-label>
                                  <mat-select [(ngModel)]="tool.config[field.key]">
                                    @for (opt of getFieldOptions(field, tool.config); track opt.value) {
                                      <mat-option [value]="opt.value">{{ opt.label }}</mat-option>
                                    }
                                  </mat-select>
                                  @if (field.hint) {
                                    <mat-hint>{{ field.hint }}</mat-hint>
                                  }
                                </mat-form-field>
                              }
                              @case ('text') {
                                <mat-form-field appearance="outline" class="full-width">
                                  <mat-label>{{ field.label }}</mat-label>
                                  <input matInput [(ngModel)]="tool.config[field.key]" 
                                         [placeholder]="field.placeholder || ''">
                                  @if (field.hint) {
                                    <mat-hint>{{ field.hint }}</mat-hint>
                                  }
                                </mat-form-field>
                              }
                              @case ('password') {
                                <mat-form-field appearance="outline" class="full-width">
                                  <mat-label>{{ field.label }}</mat-label>
                                  <input matInput type="password" [(ngModel)]="tool.config[field.key]" 
                                         [placeholder]="field.placeholder || ''">
                                  @if (field.hint) {
                                    <mat-hint>{{ field.hint }}</mat-hint>
                                  }
                                </mat-form-field>
                              }
                              @case ('number') {
                                <mat-form-field appearance="outline" class="full-width">
                                  <mat-label>{{ field.label }}</mat-label>
                                  <input matInput type="number" [(ngModel)]="tool.config[field.key]" 
                                         [placeholder]="field.placeholder || ''"
                                         [attr.min]="field.validation?.min ?? null"
                                         [attr.max]="field.validation?.max ?? null">
                                  @if (field.hint) {
                                    <mat-hint>{{ field.hint }}</mat-hint>
                                  }
                                </mat-form-field>
                              }
                              @case ('boolean') {
                                <div class="boolean-field">
                                  <mat-slide-toggle [(ngModel)]="tool.config[field.key]">
                                    {{ field.label }}
                                  </mat-slide-toggle>
                                  @if (field.hint) {
                                    <p class="field-hint">{{ field.hint }}</p>
                                  }
                                </div>
                              }
                            }
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

      <!-- Diálogo para nueva/editar conexión OpenAPI -->
      @if (showNewConnectionDialog()) {
        <div class="dialog-overlay" (click)="closeNewConnectionDialog()">
          <div class="dialog-content" (click)="$event.stopPropagation()">
            <div class="dialog-header">
              <h2>
                @if (isEditing()) {
                  <mat-icon>edit</mat-icon>
                  Editar Conexión OpenAPI
                } @else {
                  <mat-icon>add_circle</mat-icon>
                  Nueva Conexión OpenAPI
                }
              </h2>
              <button mat-icon-button (click)="closeNewConnectionDialog()" class="close-btn">
                <mat-icon>close</mat-icon>
              </button>
            </div>

            <div class="dialog-body">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Nombre</mat-label>
                <input matInput [(ngModel)]="newConnection.name" (blur)="updateSlug()" placeholder="Mi API">
                <mat-hint>Nombre descriptivo de la conexión</mat-hint>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Slug</mat-label>
                <input matInput [(ngModel)]="newConnection.slug" [disabled]="isEditing()" placeholder="mi-api">
                @if (isEditing()) {
                  <mat-hint>El slug no se puede editar</mat-hint>
                } @else {
                  <mat-hint>Identificador único (se genera automáticamente del nombre)</mat-hint>
                }
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Descripción</mat-label>
                <textarea matInput [(ngModel)]="newConnection.description" rows="2" placeholder="Descripción opcional..."></textarea>
              </mat-form-field>

              <div class="form-row">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Spec URL</mat-label>
                  <input matInput [(ngModel)]="newConnection.spec_url" placeholder="https://api.example.com/openapi.json">
                  <mat-hint>URL de la especificación OpenAPI/Swagger</mat-hint>
                </mat-form-field>
              </div>

              <div class="form-row">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Base URL</mat-label>
                  <input matInput [(ngModel)]="newConnection.base_url" placeholder="https://api.example.com/v1">
                  <mat-hint>URL base para las llamadas a la API</mat-hint>
                </mat-form-field>
              </div>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Tipo de Autenticación</mat-label>
                <mat-select [(ngModel)]="newConnection.auth_type">
                  <mat-option value="none">Sin autenticación</mat-option>
                  <mat-option value="bearer">Bearer Token</mat-option>
                  <mat-option value="api_key">API Key</mat-option>
                  <mat-option value="basic">Basic Auth</mat-option>
                </mat-select>
              </mat-form-field>

              @if (newConnection.auth_type !== 'none') {
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Token / API Key</mat-label>
                  <input matInput [(ngModel)]="newConnection.auth_token" 
                         [type]="showAuthToken() ? 'text' : 'password'" 
                         placeholder="sk-...">
                  <button mat-icon-button matSuffix (click)="toggleAuthTokenVisibility()" type="button">
                    <mat-icon>{{ showAuthToken() ? 'visibility_off' : 'visibility' }}</mat-icon>
                  </button>
                  <mat-hint>Se almacenará de forma segura</mat-hint>
                </mat-form-field>

                <div class="form-row two-col">
                  <mat-form-field appearance="outline">
                    <mat-label>Header</mat-label>
                    <input matInput [(ngModel)]="newConnection.auth_header" placeholder="Authorization">
                  </mat-form-field>

                  <mat-form-field appearance="outline">
                    <mat-label>Prefix</mat-label>
                    <input matInput [(ngModel)]="newConnection.auth_prefix" placeholder="Bearer">
                  </mat-form-field>
                </div>
              }

              <div class="form-row two-col">
                <mat-form-field appearance="outline">
                  <mat-label>Timeout (segundos)</mat-label>
                  <input matInput type="number" [(ngModel)]="newConnection.timeout" min="5" max="300">
                </mat-form-field>

                <div class="toggle-field">
                  <mat-slide-toggle [(ngModel)]="newConnection.is_active" color="primary">
                    Conexión activa
                  </mat-slide-toggle>
                </div>
              </div>
            </div>

            <div class="dialog-actions">
              <button mat-button (click)="closeNewConnectionDialog()">
                Cancelar
              </button>
              @if (isEditing()) {
                <button mat-raised-button color="primary" (click)="updateConnection()" [disabled]="savingConnection()">
                  @if (savingConnection()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    <mat-icon>save</mat-icon>
                  }
                  Guardar Cambios
                </button>
              } @else {
                <button mat-raised-button color="primary" (click)="createConnection()" [disabled]="creatingConnection()">
                  @if (creatingConnection()) {
                    <mat-spinner diameter="20"></mat-spinner>
                  } @else {
                    <mat-icon>save</mat-icon>
                  }
                  Crear Conexión
                </button>
              }
            </div>
          </div>
        </div>
      }
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

    /* Connections Grid - Same as chains/subagents */
    .connections-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }

    .connection-card {
      border-radius: 12px;
      transition: transform 0.2s, box-shadow 0.2s;
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .connection-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .connection-card mat-card-content {
      flex: 1 1 auto;
    }

    .connection-card mat-card-actions {
      margin-top: auto;
      padding-top: 16px;
      border-top: 1px solid #f0f0f0;
    }

    .connection-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .connection-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .connection-details {
      margin-top: 12px;
    }

    .connection-details .description {
      color: #666;
      font-size: 14px;
      margin-bottom: 12px;
    }

    .detail-row {
      display: flex;
      align-items: center;
      margin-bottom: 6px;
      font-size: 13px;
    }

    .detail-row .label {
      width: 60px;
      color: #888;
      font-size: 12px;
      font-weight: 500;
    }

    .detail-row .value {
      flex: 1;
      color: #333;
    }

    .truncate {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 250px;
    }

    .auth-chip {
      font-size: 11px !important;
      min-height: 22px !important;
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
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .core-tool-card mat-card-header {
      display: flex;
      align-items: flex-start;
      padding: 16px 16px 0;
    }

    .core-tool-card mat-card-title {
      font-size: 16px;
      font-weight: 600;
      line-height: 1.3;
      margin-bottom: 4px;
    }

    .core-tool-card mat-card-subtitle {
      font-size: 13px;
      line-height: 1.4;
    }

    .core-tool-card mat-card-content {
      flex: 1 1 auto;
      padding: 16px;
    }

    .core-tool-card mat-card-actions {
      margin-top: auto;
      padding: 16px;
      border-top: 1px solid #f0f0f0;
    }

    .tool-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
      flex-shrink: 0;
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

    /* Category filter */
    .category-filter {
      margin-top: 16px;
    }

    .category-filter mat-chip-option {
      text-transform: capitalize;
    }

    /* Boolean field styling */
    .boolean-field {
      display: flex;
      flex-direction: column;
      padding: 12px 0;
      border-bottom: 1px solid rgba(0,0,0,0.08);
    }

    .boolean-field mat-slide-toggle {
      font-size: 14px;
    }

    .field-hint {
      margin: 4px 0 0 0;
      font-size: 12px;
      color: #666;
    }

    /* Execution category styling */
    .tool-icon.execution { 
      background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
    }

    /* Dialog Styles */
    .dialog-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: 24px;
    }

    .dialog-content {
      background: white;
      border-radius: 16px;
      width: 100%;
      max-width: 600px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }

    .dialog-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px 24px 0;
      border-bottom: 1px solid #e0e0e0;
    }

    .dialog-header h2 {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }

    .dialog-header h2 mat-icon {
      color: #667eea;
    }

    .dialog-body {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding: 0 24px 24px;
      border-top: 1px solid #e0e0e0;
      padding-top: 16px;
    }

    .full-width {
      width: 100%;
    }

    .form-row {
      display: flex;
      gap: 16px;
    }

    .form-row.two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .toggle-field {
      display: flex;
      align-items: center;
      padding: 12px 0;
    }

    .close-btn {
      color: #666;
    }

    /* Header actions layout */
    .header-actions {
      display: flex;
      gap: 12px;
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
  
  // Core tools config (ahora dinámico desde backend)
  coreToolConfigs = signal<CoreToolConfig[]>([]);
  configurableTools = signal<ConfigurableTool[]>([]);
  loadingCoreConfig = signal(false);
  savingToolConfig = signal<string | null>(null);
  toolCategories = signal<string[]>([]);
  selectedCategory = signal<string | null>(null);

  generatingConnectionId = '';
  searchTerm = '';
  filterType = '';
  selectedTool: Tool | null = null;
  testParams = '{}';
  
  // Nueva conexión OpenAPI
  showNewConnectionDialog = signal(false);
  creatingConnection = signal(false);
  editingConnection = signal<OpenAPIConnection | null>(null);
  savingConnection = signal(false);
  showAuthToken = signal(false);
  newConnection = {
    name: '',
    slug: '',
    description: '',
    spec_url: '',
    base_url: '',
    auth_type: 'none' as 'none' | 'bearer' | 'api_key' | 'basic',
    auth_token: '',
    auth_header: 'Authorization',
    auth_prefix: 'Bearer',
    timeout: 30,
    is_active: true
  };

  ngOnInit(): void {
    this.loadConnections();
    this.loadTools();
    this.loadCoreToolConfigs();
  }
  
  loadCoreToolConfigs(): void {
    this.loadingCoreConfig.set(true);
    
    // Cargar herramientas configurables dinámicamente desde el backend
    this.http.get<any>(`${environment.apiUrl}/tools/configurable?include_admin=false`)
      .subscribe({
        next: (response) => {
          const tools = response.tools || [];
          this.configurableTools.set(tools);
          this.toolCategories.set(response.categories || []);
          
          // Convertir al formato CoreToolConfig para compatibilidad con el template actual
          const coreConfigs: CoreToolConfig[] = tools.map((tool: ConfigurableTool) => ({
            id: tool.id,
            name: tool.display_name,
            description: tool.description,
            icon: tool.icon,
            category: tool.category,
            config: tool.config,
            configSchema: tool.config_schema
          }));
          
          this.coreToolConfigs.set(coreConfigs);
          this.loadingCoreConfig.set(false);
        },
        error: (err) => {
          console.error('Error loading configurable tools:', err);
          // Si falla, mostrar array vacío
          this.coreToolConfigs.set([]);
          this.loadingCoreConfig.set(false);
        }
      });
  }
  
  /**
   * Determina si un campo debe mostrarse basándose en visible_when
   */
  shouldShowField(field: ConfigField, config: Record<string, any>): boolean {
    if (!field.visible_when) {
      return true;
    }
    
    const condition = field.visible_when;
    const currentValue = config[condition.field];
    
    // Condición: valor específico
    if (condition.value !== undefined) {
      return currentValue === condition.value;
    }
    
    // Condición: lista de valores
    if (condition.values !== undefined) {
      return condition.values.includes(currentValue);
    }
    
    // Condición: NOT valor específico
    if (condition.not_value !== undefined) {
      return currentValue !== condition.not_value;
    }
    
    // Condición: NOT lista de valores
    if (condition.not_values !== undefined) {
      return !condition.not_values.includes(currentValue);
    }
    
    return true;
  }
  
  /**
   * Obtiene las opciones para un campo, considerando dynamic_options
   */
  getFieldOptions(field: ConfigField, config: Record<string, any>): { value: string; label: string }[] {
    // Si tiene opciones dinámicas, usarlas basándose en el campo padre
    if (field.options_depend_on && field.dynamic_options) {
      const parentValue = config[field.options_depend_on] || '';
      const dynamicOpts = field.dynamic_options[parentValue];
      if (dynamicOpts) {
        return dynamicOpts;
      }
      // Fallback a opciones estáticas si no hay match
    }
    
    // Opciones estáticas
    return field.options || [];
  }
  
  /**
   * Agrupa campos por su propiedad group
   */
  getFieldGroups(fields: ConfigField[]): Map<string, ConfigField[]> {
    const groups = new Map<string, ConfigField[]>();
    
    // Ordenar por order primero
    const sorted = [...fields].sort((a, b) => (a.order || 0) - (b.order || 0));
    
    for (const field of sorted) {
      const groupName = field.group || 'General';
      if (!groups.has(groupName)) {
        groups.set(groupName, []);
      }
      groups.get(groupName)!.push(field);
    }
    
    return groups;
  }
  
  /**
   * Filtra herramientas por categoría
   */
  getFilteredTools(): CoreToolConfig[] {
    const tools = this.coreToolConfigs();
    const category = this.selectedCategory();
    
    if (!category) {
      return tools;
    }
    
    return tools.filter(t => t.category === category);
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
          this.snackBar.open(`${response.count} conexiones recargadas desde base de datos`, 'Cerrar', { duration: 3000 });
          this.refreshingConnections.set(false);
          this.loadConnections();
        },
        error: (err) => {
          this.snackBar.open('Error refrescando conexiones', 'Cerrar', { duration: 3000 });
          this.refreshingConnections.set(false);
        }
      });
  }

  openNewConnectionDialog(): void {
    this.showNewConnectionDialog.set(true);
    // Reset form
    this.newConnection = {
      name: '',
      slug: '',
      description: '',
      spec_url: '',
      base_url: '',
      auth_type: 'none',
      auth_token: '',
      auth_header: 'Authorization',
      auth_prefix: 'Bearer',
      timeout: 30,
      is_active: true
    };
  }

  closeNewConnectionDialog(): void {
    this.showNewConnectionDialog.set(false);
    this.editingConnection.set(null);
  }

  generateSlugFromName(name: string): string {
    return name.toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }

  updateSlug(): void {
    if (this.newConnection.name && !this.newConnection.slug) {
      this.newConnection.slug = this.generateSlugFromName(this.newConnection.name);
    }
  }

  createConnection(): void {
    if (!this.newConnection.name || !this.newConnection.spec_url || !this.newConnection.base_url) {
      this.snackBar.open('Nombre, Spec URL y Base URL son obligatorios', 'Cerrar', { duration: 3000 });
      return;
    }

    this.creatingConnection.set(true);

    this.http.post<any>(`${environment.apiUrl}/tools/openapi/connections`, this.newConnection)
      .subscribe({
        next: (response) => {
          this.snackBar.open('Conexión creada exitosamente', 'Cerrar', { duration: 3000 });
          this.creatingConnection.set(false);
          this.closeNewConnectionDialog();
          this.loadConnections();
        },
        error: (err) => {
          const errorMsg = err.error?.detail || 'Error creando conexión';
          this.snackBar.open(errorMsg, 'Cerrar', { duration: 5000 });
          this.creatingConnection.set(false);
        }
      });
  }

  openEditConnectionDialog(connection: OpenAPIConnection): void {
    this.editingConnection.set(connection);
    this.showNewConnectionDialog.set(true);
    // Populate form with connection data
    this.newConnection = {
      name: connection.name,
      slug: connection.slug,
      description: connection.description || '',
      spec_url: connection.specUrl,
      base_url: connection.baseUrl,
      auth_type: connection.authType as 'none' | 'bearer' | 'api_key' | 'basic',
      auth_token: connection.authToken || '', // Populate token so it can be edited
      auth_header: 'Authorization',
      auth_prefix: 'Bearer',
      timeout: connection.timeout,
      is_active: true
    };
  }

  updateConnection(): void {
    const connection = this.editingConnection();
    if (!connection) return;

    if (!this.newConnection.name || !this.newConnection.spec_url || !this.newConnection.base_url) {
      this.snackBar.open('Nombre, Spec URL y Base URL son obligatorios', 'Cerrar', { duration: 3000 });
      return;
    }

    this.savingConnection.set(true);

    this.http.put<any>(`${environment.apiUrl}/tools/openapi/connections/${connection.id}`, this.newConnection)
      .subscribe({
        next: (response) => {
          this.snackBar.open('Conexión actualizada exitosamente', 'Cerrar', { duration: 3000 });
          this.savingConnection.set(false);
          this.editingConnection.set(null);
          this.closeNewConnectionDialog();
          this.loadConnections();
        },
        error: (err) => {
          const errorMsg = err.error?.detail || 'Error actualizando conexión';
          this.snackBar.open(errorMsg, 'Cerrar', { duration: 5000 });
          this.savingConnection.set(false);
        }
      });
  }

  isEditing(): boolean {
    return this.editingConnection() !== null;
  }

  toggleAuthTokenVisibility(): void {
    this.showAuthToken.update(value => !value);
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
