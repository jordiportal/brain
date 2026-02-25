import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';
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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { MatListModule } from '@angular/material/list';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { environment } from '../../../environments/environment';

// Chat unificado
import { ChatComponent, ChatMessage, ChatAttachment } from '../../shared/components/chat';
import { AuthService } from '../../core/services/auth.service';
import { LlmSelectorComponent, LlmSelectionService } from '../../shared/components/llm-selector';
import { SseStreamService } from '../../shared/services/sse-stream.service';

interface Skill {
  id: string;
  name: string;
  description: string;
  content?: string;
  loaded?: boolean;
}

interface Subagent {
  id: string;
  name: string;
  description: string;
  version: string;
  domain_tools: string[];
  skills?: Skill[];
  status: string;
  icon: string;
  // From agent_definitions (full definition)
  system_prompt?: string;
  role?: string;
  expertise?: string;
  task_requirements?: string;
  core_tools_enabled?: boolean;
  is_enabled?: boolean;
  icon_name?: string;
  settings?: Record<string, unknown>;
}

interface SubagentTool {
  id: string;
  name: string;
  description: string;
  type: string;
  parameters: any;
}

interface SubagentConfig {
  enabled: boolean;
  system_prompt?: string;
  // LLM para razonamiento del agente - referencia al ID del provider en BD
  llm_provider?: number | string;  // ID del provider en llm_providers
  llm_model?: string;  // Override del modelo (vacío = usar default del provider)
  settings: Record<string, any>;
}

// Proveedor LLM desde la base de datos
interface DBLLMProvider {
  id: number;
  documentId: string;
  name: string;
  type: string;
  baseUrl: string;
  apiKey?: string;
  defaultModel?: string;
  embeddingModel?: string;
  isActive: boolean;
  isDefault: boolean;
}

interface TestResult {
  agent_id: string;
  status: string;
  tools_count: number;
  tools_status: Array<{id: string; name: string; status: string}>;
  checks: Record<string, boolean>;
}

interface ExecuteResult {
  status: string;
  agent_id: string;
  result: {
    success: boolean;
    response: string;
    tools_used: string[];
    images: Array<{url?: string; base64?: string; mime_type?: string}>;
    error?: string;
    execution_time_ms: number;
  };
}

interface SubagentTest {
  id: string;
  name: string;
  description: string;
  input: {
    task: string;
    context?: string;
  };
  expected: {
    type: string;
    criteria: string[];
  };
  lastRun?: {
    status: string;
    timestamp: string;
    notes?: string;
  };
}

interface TestCategory {
  category: string;
  tool_id?: string;
  skill_id?: string;
  file: string;
  tests: SubagentTest[];
}

interface TestRunResult {
  agent_id: string;
  test_id: string;
  test_name: string;
  status: string;
  duration_ms: number;
  result?: any;
  error?: string;
  expected: {
    type: string;
    criteria: string[];
  };
  criteria: string[];
}

@Component({
  selector: 'app-subagents',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
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
    MatSlideToggleModule,
    MatBadgeModule,
    MatListModule,
    MatCheckboxModule,
    ChatComponent,
    LlmSelectorComponent
  ],
  template: `
    <div class="subagents-page">
      <div class="page-header">
        <div>
          <h1>Agentes Especializados</h1>
          <p class="subtitle">Agentes de dominio para tareas específicas</p>
        </div>
        <div class="header-actions">
          <button mat-stroked-button (click)="startNewAgent()">
            <mat-icon>add</mat-icon>
            Nuevo Agente
          </button>
          <button mat-raised-button color="primary" (click)="loadSubagents()" [disabled]="loading()">
            @if (loading()) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              <mat-icon>refresh</mat-icon>
            }
            Actualizar
          </button>
        </div>
      </div>

      <mat-tab-group [(selectedIndex)]="activeTabIndex" animationDuration="300ms">
        <!-- Tab: Lista de Agentes -->
        <mat-tab label="Agentes">
          <div class="tab-content-wrapper">
            <!-- Grid de Agentes -->
            @if (loading()) {
              <div class="loading-container">
                <mat-spinner diameter="48"></mat-spinner>
                <p>Cargando agentes...</p>
              </div>
            } @else {
              <div class="subagents-grid">
                @for (agent of subagents(); track agent.id) {
                  <mat-card class="subagent-card" [class.selected]="selectedAgent?.id === agent.id">
                    <mat-card-header>
                      <div class="agent-icon" [class]="agent.id" mat-card-avatar>
                        <mat-icon>{{ agent.icon }}</mat-icon>
                      </div>
                      <mat-card-title>{{ agent.name }}</mat-card-title>
                      <mat-card-subtitle>v{{ agent.version }}</mat-card-subtitle>
                      <mat-chip class="status-chip" [class]="agent.status">
                        {{ agent.status | uppercase }}
                      </mat-chip>
                    </mat-card-header>
                    
                    <mat-card-content>
                      <p class="description">{{ agent.description }}</p>
                      
                      @if (agent.domain_tools && agent.domain_tools.length > 0) {
                        <div class="tools-section">
                          <span class="tools-label">
                            <mat-icon>build</mat-icon>
                            Herramientas ({{ agent.domain_tools.length }}):
                          </span>
                          <div class="tools-mini-grid">
                            @for (toolId of agent.domain_tools; track toolId) {
                              <div class="tool-mini-item" [matTooltip]="getToolDescription(toolId)">
                                <mat-icon class="tmi-icon">{{ getToolTypeIcon(toolId) }}</mat-icon>
                                <span class="tmi-name">{{ getToolName(toolId) }}</span>
                              </div>
                            }
                          </div>
                        </div>
                      }

                      @if (agent.skills && agent.skills.length > 0) {
                        <div class="skills-section">
                          <span class="skills-label">
                            <mat-icon>school</mat-icon>
                            Skills:
                          </span>
                          <div class="skills-chips">
                            @for (skill of agent.skills; track skill.id) {
                              <mat-chip class="skill-chip" [matTooltip]="skill.description">{{ skill.name }}</mat-chip>
                            }
                          </div>
                        </div>
                      }
                    </mat-card-content>

                    <mat-card-actions align="end">
                      <button mat-button (click)="testAgent(agent.id)" [disabled]="testingAgent() === agent.id">
                        @if (testingAgent() === agent.id) {
                          <mat-spinner diameter="16"></mat-spinner>
                        } @else {
                          <mat-icon>health_and_safety</mat-icon>
                        }
                        Test
                      </button>
                      <button mat-button color="primary" (click)="selectAgent(agent)">
                        <mat-icon>settings</mat-icon>
                        Configurar
                      </button>
                      <button mat-raised-button color="accent" (click)="openExecutePanel(agent)">
                        <mat-icon>play_arrow</mat-icon>
                        Ejecutar
                      </button>
                    </mat-card-actions>
                  </mat-card>
                } @empty {
                  <div class="empty-state">
                    <mat-icon>smart_toy</mat-icon>
                    <h3>No hay agentes registrados</h3>
                    <p>Los agentes se registran automáticamente al iniciar la API</p>
                    <button mat-raised-button color="primary" (click)="loadSubagents()">
                      <mat-icon>refresh</mat-icon>
                      Recargar
                    </button>
                  </div>
                }
              </div>
            }
          </div>

          <!-- Panel de Chat con Agente -->
          @if (executeAgent()) {
            <mat-card class="chat-panel" style="margin-top: 24px;">
              <mat-card-header>
                <mat-card-title>
                  <mat-icon>chat</mat-icon>
                  Chat con {{ executeAgent()?.name }}
                </mat-card-title>
                <div class="chat-header-actions">
                  <button mat-icon-button (click)="clearChat()" matTooltip="Limpiar chat">
                    <mat-icon>delete_sweep</mat-icon>
                  </button>
                  <button mat-icon-button (click)="closeChat()" class="close-btn">
                    <mat-icon>close</mat-icon>
                  </button>
                </div>
              </mat-card-header>
              <mat-card-content class="chat-content">
                <!-- Selector LLM unificado -->
                <div class="chat-config-bar">
                  <app-llm-selector
                    [(providerId)]="executeProviderId"
                    [(model)]="executeModel"
                    mode="compact"
                    (selectionChange)="onExecuteSelectionChange($event)">
                  </app-llm-selector>
                </div>
                
                <!-- Chat -->
                <div class="chat-container-wrapper">
                  <app-chat
                    [messages]="messages"
                    [features]="chatFeatures"
                    [isLoading]="executing"
                    [placeholder]="'Describe la tarea para ' + executeAgent()?.name + '...'"
                    [emptyMessage]="'Envía un mensaje para comenzar la conversación con ' + executeAgent()?.name"
                    (messageSent)="onChatMessageSent($event)"
                    (messageWithAttachments)="onChatMessageWithAttachments($event)">
                  </app-chat>
                </div>
              </mat-card-content>
            </mat-card>
          }
        </mat-tab>

        <!-- Tab: Configuración (habilitada con agente seleccionado o nuevo) -->
        <mat-tab label="Configuración" [disabled]="!selectedAgent">
          @if (selectedAgent) {
            <mat-card class="detail-panel">
              <mat-card-header>
                <mat-card-title>
                <mat-icon>{{ selectedAgent.icon }}</mat-icon>
                {{ isNewAgent() ? 'Nuevo agente' : selectedAgent.name }}
              </mat-card-title>
              <button mat-icon-button (click)="closeConfiguration()" class="close-btn">
                <mat-icon>close</mat-icon>
              </button>
            </mat-card-header>

            <mat-tab-group>
              <!-- Tab de Información (editable) -->
              <mat-tab label="Información">
                <div class="tab-content info-edit-form">
                  <div class="info-grid">
                    <div class="info-column">
                      @if (isNewAgent()) {
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>ID del agente</mat-label>
                          <input matInput [(ngModel)]="selectedAgent.id" placeholder="mi_agente" required>
                          <mat-hint>Identificador único (snake_case). Obligatorio para crear.</mat-hint>
                        </mat-form-field>
                      } @else {
                        <div class="info-row readonly-id">
                          <span class="info-label">ID</span>
                          <span class="info-value mono">{{ selectedAgent.id }}</span>
                        </div>
                      }
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Nombre</mat-label>
                        <input matInput [(ngModel)]="selectedAgent.name" placeholder="Nombre del agente">
                      </mat-form-field>
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Descripción</mat-label>
                        <textarea matInput [(ngModel)]="selectedAgent.description" rows="2"></textarea>
                      </mat-form-field>
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Rol</mat-label>
                        <input matInput [(ngModel)]="selectedAgent.role" placeholder="Ej: Diseñador Visual">
                      </mat-form-field>
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Expertise</mat-label>
                        <textarea matInput [(ngModel)]="selectedAgent.expertise" rows="2"></textarea>
                      </mat-form-field>
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Requisitos de tarea</mat-label>
                        <input matInput [(ngModel)]="selectedAgent.task_requirements">
                      </mat-form-field>
                      <div class="form-row-info">
                        <mat-form-field appearance="outline">
                          <mat-label>Versión actual</mat-label>
                          <input matInput [value]="selectedAgent.version || '1.0.0'" readonly>
                          <mat-hint>Se actualiza al guardar</mat-hint>
                        </mat-form-field>
                        <mat-form-field appearance="outline">
                          <mat-label>Icono</mat-label>
                          <input matInput [(ngModel)]="selectedAgent.icon" placeholder="smart_toy">
                          <mat-icon matSuffix>{{ selectedAgent.icon || 'smart_toy' }}</mat-icon>
                        </mat-form-field>
                      </div>
                      <mat-slide-toggle [(ngModel)]="selectedAgent.is_enabled" color="primary">
                        Agente habilitado
                      </mat-slide-toggle>
                    </div>
                    <div class="info-column">
                      <div class="info-card tools-card">
                        <div class="info-card-header">
                          <mat-icon>build</mat-icon>
                          <h3>Herramientas ({{ selectedAgent.domain_tools?.length || 0 }})</h3>
                          <button mat-stroked-button class="add-tool-btn" (click)="showToolPicker = !showToolPicker">
                            <mat-icon>{{ showToolPicker ? 'close' : 'add' }}</mat-icon>
                            {{ showToolPicker ? 'Cerrar' : 'Añadir' }}
                          </button>
                        </div>
                        <div class="info-card-content">
                          @if (showToolPicker) {
                            <div class="tool-picker">
                              <mat-form-field appearance="outline" class="full-width tool-search-field">
                                <mat-icon matPrefix>search</mat-icon>
                                <input matInput [(ngModel)]="toolSearchText" placeholder="Buscar herramienta...">
                              </mat-form-field>
                              <div class="tool-picker-grid">
                                @for (tool of filteredAvailableTools(); track tool.id) {
                                  <div class="tool-picker-item" (click)="addDomainTool(tool.id)"
                                       [class.already-added]="selectedAgent.domain_tools?.includes(tool.id)">
                                    <mat-icon class="tp-icon">{{ getToolTypeIcon(tool.id) }}</mat-icon>
                                    <div class="tp-info">
                                      <span class="tp-name">{{ tool.name || tool.id }}</span>
                                      @if (tool.description) {
                                        <span class="tp-desc">{{ tool.description }}</span>
                                      }
                                    </div>
                                    @if (selectedAgent.domain_tools?.includes(tool.id)) {
                                      <mat-icon class="tp-check">check_circle</mat-icon>
                                    } @else {
                                      <mat-icon class="tp-add">add_circle_outline</mat-icon>
                                    }
                                  </div>
                                }
                              </div>
                            </div>
                          }

                          @if (selectedAgent.domain_tools && selectedAgent.domain_tools.length > 0) {
                            <div class="tools-grid">
                              @for (toolId of selectedAgent.domain_tools; track toolId) {
                                <div class="tool-grid-item" [matTooltip]="getToolDescription(toolId)">
                                  <mat-icon class="tgi-icon">{{ getToolTypeIcon(toolId) }}</mat-icon>
                                  <div class="tgi-info">
                                    <span class="tgi-name">{{ getToolName(toolId) }}</span>
                                    <span class="tgi-id">{{ toolId }}</span>
                                  </div>
                                  <button mat-icon-button class="tgi-remove" (click)="removeDomainTool(toolId)" matTooltip="Quitar">
                                    <mat-icon>close</mat-icon>
                                  </button>
                                </div>
                              }
                            </div>
                          } @else if (!showToolPicker) {
                            <div class="empty-tools">
                              <mat-icon>extension_off</mat-icon>
                              <p>Sin herramientas de dominio</p>
                            </div>
                          }

                          <mat-slide-toggle [(ngModel)]="selectedAgent.core_tools_enabled" color="primary"
                                            class="core-tools-toggle">
                            Core tools (reflect, plan, delegate, finish)
                          </mat-slide-toggle>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </mat-tab>

              <!-- Tab de Skills -->
              <mat-tab label="Skills">
                <div class="tab-content">
                  <div class="skills-toolbar">
                    <div class="skills-info">
                      <mat-icon>auto_awesome</mat-icon>
                      <span>El LLM decide cuándo cargar cada skill según la tarea</span>
                    </div>
                    <button mat-raised-button color="primary" (click)="showAddSkillForm = !showAddSkillForm">
                      <mat-icon>{{ showAddSkillForm ? 'close' : 'add' }}</mat-icon>
                      {{ showAddSkillForm ? 'Cancelar' : 'Añadir Skill' }}
                    </button>
                  </div>

                  @if (showAddSkillForm) {
                    <mat-card class="add-skill-card">
                      <mat-card-content>
                        <div class="add-skill-form">
                          <mat-form-field appearance="outline">
                            <mat-label>ID del skill</mat-label>
                            <input matInput [(ngModel)]="newSkill.id" placeholder="data_analysis">
                            <mat-hint>Identificador único (snake_case)</mat-hint>
                          </mat-form-field>
                          <mat-form-field appearance="outline">
                            <mat-label>Nombre</mat-label>
                            <input matInput [(ngModel)]="newSkill.name" placeholder="Análisis de Datos">
                          </mat-form-field>
                          <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Descripción</mat-label>
                            <input matInput [(ngModel)]="newSkill.description" placeholder="Cuándo debe el LLM cargar este skill...">
                          </mat-form-field>
                          <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Contenido (Markdown)</mat-label>
                            <textarea matInput [(ngModel)]="newSkill.content" rows="8" placeholder="# Mi Skill\n\nInstrucciones..."></textarea>
                          </mat-form-field>
                          <div class="add-skill-actions">
                            <button mat-raised-button color="primary"
                                    [disabled]="!newSkill.id || !newSkill.name || addingSkill()"
                                    (click)="addSkill()">
                              @if (addingSkill()) {
                                <mat-spinner diameter="18"></mat-spinner>
                              } @else {
                                <mat-icon>add</mat-icon>
                              }
                              Añadir
                            </button>
                          </div>
                        </div>
                      </mat-card-content>
                    </mat-card>
                  }

                  @if (loadingSkills()) {
                    <div class="loading-container">
                      <mat-spinner diameter="32"></mat-spinner>
                    </div>
                  } @else if (agentSkills().length === 0 && !showAddSkillForm) {
                    <div class="empty-skills">
                      <mat-icon>school</mat-icon>
                      <h3>Sin skills especializados</h3>
                      <p>Añade skills para dotar al agente de conocimiento específico</p>
                    </div>
                  } @else {
                    <div class="skills-list">
                      @for (skill of agentSkills(); track skill.id) {
                        <mat-expansion-panel class="skill-panel" [expanded]="expandedSkill === skill.id">
                          <mat-expansion-panel-header (click)="toggleSkill(skill)">
                            <mat-panel-title>
                              <mat-icon class="skill-icon">school</mat-icon>
                              <span class="skill-name">{{ skill.name }}</span>
                            </mat-panel-title>
                            <mat-panel-description>
                              <span class="skill-id">{{ skill.id }}</span>
                              <button mat-icon-button class="skill-delete-btn" matTooltip="Eliminar skill"
                                      (click)="removeSkill(skill); $event.stopPropagation()">
                                <mat-icon>delete_outline</mat-icon>
                              </button>
                            </mat-panel-description>
                          </mat-expansion-panel-header>

                          <div class="skill-content">
                            <div class="skill-description">
                              <mat-icon>info</mat-icon>
                              <span>{{ skill.description }}</span>
                            </div>

                            @if (loadingSkillContent() === skill.id) {
                              <div class="skill-loading">
                                <mat-spinner diameter="24"></mat-spinner>
                                <span>Cargando contenido...</span>
                              </div>
                            } @else if (skill.content) {
                              <div class="skill-editor">
                                <div class="editor-header">
                                  <span class="editor-label">
                                    <mat-icon>description</mat-icon>
                                    Contenido del Skill ({{ skill.id }}.md)
                                  </span>
                                  <div class="editor-actions">
                                    <button mat-icon-button matTooltip="Guardar skill" (click)="saveSkillViaApi(skill)"
                                            [disabled]="!dirtySkills.has(skill.id)">
                                      <mat-icon [class.dirty]="dirtySkills.has(skill.id)">save</mat-icon>
                                    </button>
                                    <button mat-icon-button matTooltip="Copiar contenido" (click)="copySkillContent(skill)">
                                      <mat-icon>content_copy</mat-icon>
                                    </button>
                                    <button mat-icon-button matTooltip="Expandir" (click)="expandSkillEditor = !expandSkillEditor">
                                      <mat-icon>{{ expandSkillEditor ? 'fullscreen_exit' : 'fullscreen' }}</mat-icon>
                                    </button>
                                  </div>
                                </div>
                                <textarea
                                  class="skill-textarea"
                                  [class.expanded]="expandSkillEditor"
                                  [(ngModel)]="skill.content"
                                  (ngModelChange)="markSkillDirty(skill.id)"
                                  placeholder="Contenido markdown del skill..."></textarea>
                                <div class="editor-footer">
                                  <span class="char-count">{{ skill.content.length || 0 }} caracteres</span>
                                  @if (dirtySkills.has(skill.id)) {
                                    <span class="hint-unsaved">Cambios sin guardar</span>
                                  }
                                </div>
                              </div>
                            } @else {
                              <button mat-stroked-button color="primary" (click)="loadSkillContent(skill)">
                                <mat-icon>visibility</mat-icon>
                                Ver contenido
                              </button>
                            }
                          </div>
                        </mat-expansion-panel>
                      }
                    </div>
                  }
                </div>
              </mat-tab>

              <!-- Tab de Tests -->
              <mat-tab label="Tests">
                <div class="tab-content tests-tab-content">
                  @if (loadingTests()) {
                    <div class="loading-container">
                      <mat-spinner diameter="32"></mat-spinner>
                    </div>
                  } @else if (testCategories().length === 0) {
                    <div class="empty-tests">
                      <mat-icon>science</mat-icon>
                      <h3>Sin tests definidos</h3>
                      <p>Este agente no tiene tests configurados</p>
                    </div>
                  } @else {
                    <div class="tests-layout">
                      <!-- Panel izquierdo: Lista de tests -->
                      <div class="tests-list-panel">
                        <div class="tests-header">
                          <div class="tests-summary">
                            <span class="summary-item passed">
                              <mat-icon>check_circle</mat-icon>
                              {{ getTestStats().passed }}
                            </span>
                            <span class="summary-item failed">
                              <mat-icon>cancel</mat-icon>
                              {{ getTestStats().failed }}
                            </span>
                            <span class="summary-item pending">
                              <mat-icon>pending</mat-icon>
                              {{ getTestStats().pending }}
                            </span>
                          </div>
                          <button mat-raised-button color="primary" (click)="runAllTests()" [disabled]="runningAllTests()">
                            @if (runningAllTests()) {
                              <mat-spinner diameter="18"></mat-spinner>
                            } @else {
                              <mat-icon>play_arrow</mat-icon>
                            }
                            Todos
                          </button>
                        </div>

                        <div class="tests-categories">
                          @for (category of testCategories(); track category.file) {
                            <mat-expansion-panel class="category-panel" [expanded]="true">
                              <mat-expansion-panel-header>
                                <mat-panel-title>
                                  <mat-icon class="category-icon">{{ getCategoryIcon(category) }}</mat-icon>
                                  <span>{{ getCategoryName(category) }}</span>
                                  <span class="tests-count">({{ category.tests.length }})</span>
                                </mat-panel-title>
                              </mat-expansion-panel-header>
                              
                              <div class="tests-list">
                                @for (test of category.tests; track test.id) {
                                  <div class="test-item" 
                                       [class]="test.lastRun?.status || 'pending'"
                                       [class.selected]="selectedTest?.id === test.id"
                                       (click)="selectTest(test)">
                                    <div class="test-status">
                                      @if (runningTest() === test.id) {
                                        <mat-spinner diameter="18"></mat-spinner>
                                      } @else {
                                        <mat-icon [class]="test.lastRun?.status || 'pending'">
                                          {{ getStatusIcon(test.lastRun?.status) }}
                                        </mat-icon>
                                      }
                                    </div>
                                    <div class="test-info">
                                      <span class="test-id">{{ test.id }}</span>
                                      <span class="test-name">{{ test.name }}</span>
                                    </div>
                                    <button mat-icon-button matTooltip="Ejecutar" 
                                            (click)="runTest(test); $event.stopPropagation()" 
                                            [disabled]="runningTest() === test.id"
                                            class="run-btn">
                                      <mat-icon>play_arrow</mat-icon>
                                    </button>
                                  </div>
                                }
                              </div>
                            </mat-expansion-panel>
                          }
                        </div>
                      </div>

                      <!-- Panel derecho: Detalle del test -->
                      <div class="test-detail-panel">
                        @if (selectedTest) {
                          <div class="detail-header">
                            <span class="detail-id">{{ selectedTest.id }}</span>
                            <h3>{{ selectedTest.name }}</h3>
                            <p>{{ selectedTest.description }}</p>
                          </div>

                          <div class="detail-section">
                            <h4>Input</h4>
                            <div class="input-task">{{ selectedTest.input.task }}</div>
                            @if (selectedTest.input.context) {
                              <div class="input-context">{{ selectedTest.input.context }}</div>
                            }
                          </div>

                          <div class="detail-section">
                            <h4>Criterios de validación</h4>
                            <div class="criteria-list">
                              @for (criterion of selectedTest.expected.criteria; track $index) {
                                <mat-checkbox [(ngModel)]="criteriaChecks[$index]">
                                  {{ criterion }}
                                </mat-checkbox>
                              }
                            </div>
                          </div>

                          @if (currentTestResult()) {
                            <div class="detail-section result-section">
                              <h4>
                                Resultado 
                                <span class="duration">({{ currentTestResult()!.duration_ms }}ms)</span>
                              </h4>
                              
                              @if (currentTestResult()!.error) {
                                <div class="output-error">
                                  <mat-icon>error</mat-icon>
                                  {{ currentTestResult()!.error }}
                                </div>
                              } @else {
                                @if (currentTestResult()!.result?.images?.length) {
                                  <div class="output-images">
                                    @for (img of currentTestResult()!.result.images; track $index) {
                                      @if (img.url) {
                                        <img [src]="sanitizeImageUrl(img.url)" 
                                             class="result-image" alt="Generated image">
                                      }
                                    }
                                  </div>
                                }
                                @if (currentTestResult()!.result?.data?.html) {
                                  <button mat-stroked-button (click)="previewHtml(currentTestResult()!.result.data.html)">
                                    <mat-icon>preview</mat-icon>
                                    Ver presentación
                                  </button>
                                }
                                @if (currentTestResult()!.result?.response) {
                                  <div class="output-response">
                                    {{ currentTestResult()!.result.response }}
                                  </div>
                                }
                              }
                            </div>
                          } @else {
                            <div class="no-result">
                              <mat-icon>play_circle</mat-icon>
                              <p>Ejecuta el test para ver resultados</p>
                              <button mat-raised-button color="primary" (click)="runTest(selectedTest)" [disabled]="runningTest() === selectedTest.id">
                                @if (runningTest() === selectedTest.id) {
                                  <mat-spinner diameter="18"></mat-spinner>
                                } @else {
                                  <mat-icon>play_arrow</mat-icon>
                                }
                                Ejecutar Test
                              </button>
                            </div>
                          }

                          <div class="detail-section">
                            <mat-form-field appearance="outline" class="full-width">
                              <mat-label>Notas</mat-label>
                              <textarea matInput [(ngModel)]="testNotes" rows="2" 
                                        placeholder="Observaciones..."></textarea>
                            </mat-form-field>
                          </div>

                          <div class="detail-actions">
                            <button mat-button color="warn" (click)="markTestResult('fail')" [disabled]="savingTestResult()">
                              <mat-icon>close</mat-icon>
                              Fail
                            </button>
                            <button mat-raised-button color="primary" (click)="markTestResult('pass')" [disabled]="savingTestResult()">
                              <mat-icon>check</mat-icon>
                              Pass
                            </button>
                          </div>
                        } @else {
                          <div class="no-selection">
                            <mat-icon>touch_app</mat-icon>
                            <p>Selecciona un test de la lista</p>
                          </div>
                        }
                      </div>
                    </div>
                  }
                </div>
              </mat-tab>

              <!-- Tab de Configuración -->
              <mat-tab label="Configuración">
                <div class="tab-content">
                  @if (loadingConfig()) {
                    <div class="loading-container">
                      <mat-spinner diameter="32"></mat-spinner>
                    </div>
                  } @else {
                    <div class="config-form">
                      <mat-slide-toggle [(ngModel)]="agentConfig.enabled" color="primary">
                        Agente habilitado
                      </mat-slide-toggle>

                      <!-- Configuración de LLM - común a todos los agentes -->
                      <div class="config-section">
                        <div class="config-section-header">
                          <mat-icon>smart_toy</mat-icon>
                          <span>Modelo de Lenguaje (LLM)</span>
                          @if (loadingProviders()) {
                            <mat-spinner diameter="16"></mat-spinner>
                          }
                        </div>
                        
                        @if (dbProviders().length === 0 && !loadingProviders()) {
                          <div class="no-providers-warning">
                            <mat-icon>warning</mat-icon>
                            <span>No hay proveedores LLM configurados. <a routerLink="/settings">Configura uno en Ajustes</a></span>
                          </div>
                        } @else {
                          <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Proveedor LLM</mat-label>
                            <mat-select [(ngModel)]="agentConfig.llm_provider" 
                                        (ngModelChange)="onProviderChange($event)">
                              @for (provider of dbProviders(); track provider.id) {
                                <mat-option [value]="provider.id">
                                  <div class="provider-option">
                                    <span class="provider-name">{{ provider.name }}</span>
                                    <span class="provider-type">{{ provider.type }}</span>
                                    @if (provider.isDefault) {
                                      <mat-chip class="default-chip">Por defecto</mat-chip>
                                    }
                                  </div>
                                </mat-option>
                              }
                            </mat-select>
                            <mat-hint>
                              @if (getSelectedProvider()) {
                                {{ getSelectedProvider()?.baseUrl }} · Modelo: {{ getSelectedProvider()?.defaultModel }}
                              }
                            </mat-hint>
                          </mat-form-field>

                          @if (getSelectedProvider()) {
                            <div class="provider-info">
                              <div class="info-row">
                                <mat-icon>link</mat-icon>
                                <span>{{ getSelectedProvider()?.baseUrl }}</span>
                              </div>
                              <div class="info-row">
                                <mat-icon>memory</mat-icon>
                                <span>Modelo por defecto: <strong>{{ getSelectedProvider()?.defaultModel }}</strong></span>
                              </div>
                              @if (getSelectedProvider()?.apiKey) {
                                <div class="info-row">
                                  <mat-icon>key</mat-icon>
                                  <span>API Key configurada</span>
                                </div>
                              }
                            </div>
                          }

                          <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Modelo</mat-label>
                            <mat-select [(ngModel)]="agentConfig.llm_model">
                              <mat-option [value]="''">
                                <em>Usar default: {{ getSelectedProvider()?.defaultModel || '(ninguno)' }}</em>
                              </mat-option>
                              @if (loadingModels()) {
                                <mat-option disabled>
                                  <mat-spinner diameter="16"></mat-spinner>
                                  Cargando modelos...
                                </mat-option>
                              }
                              @for (model of availableModels(); track model) {
                                <mat-option [value]="model">{{ model }}</mat-option>
                              }
                            </mat-select>
                            <mat-hint>Selecciona un modelo o deja vacío para usar el default</mat-hint>
                          </mat-form-field>
                        }
                      </div>

                      <mat-divider></mat-divider>

                      <!-- System Prompt (guardado en agent_definitions) -->
                      <div class="prompt-section">
                        <div class="prompt-header">
                          <mat-icon>psychology</mat-icon>
                          <span>System Prompt</span>
                          @if (!isNewAgent()) {
                            <button mat-icon-button matTooltip="Restaurar desde última versión" (click)="resetPrompt()">
                              <mat-icon>restore</mat-icon>
                            </button>
                          }
                        </div>
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Instrucciones del sistema</mat-label>
                          <textarea matInput [(ngModel)]="selectedAgent.system_prompt" rows="8"
                                    placeholder="Instrucciones que definen el comportamiento del agente..."></textarea>
                          <mat-hint>Se guarda con el agente (versión automática al guardar)</mat-hint>
                        </mat-form-field>
                      </div>

                      

                      <div class="config-actions">
                        <button mat-raised-button color="primary" (click)="promptSaveDefinition()" [disabled]="savingDefinition()">
                          @if (savingDefinition()) {
                            <mat-spinner diameter="20"></mat-spinner>
                          } @else {
                            <mat-icon>save</mat-icon>
                          }
                          {{ isNewAgent() ? 'Crear agente' : 'Guardar versión' }}
                        </button>
                      </div>

                      <!-- Save dialog inline -->
                      @if (showSaveDialog) {
                        <div class="save-dialog-overlay" (click)="showSaveDialog = false">
                          <div class="save-dialog" (click)="$event.stopPropagation()">
                            <h3>
                              <mat-icon>save</mat-icon>
                              Guardar versión
                            </h3>
                            <mat-form-field appearance="outline" class="full-width">
                              <mat-label>Nueva versión</mat-label>
                              <input matInput [(ngModel)]="saveVersionText" placeholder="1.1.0">
                              <mat-hint>Actual: {{ selectedAgent.version || '1.0.0' }}</mat-hint>
                            </mat-form-field>
                            <mat-form-field appearance="outline" class="full-width">
                              <mat-label>Motivo del cambio (opcional)</mat-label>
                              <input matInput [(ngModel)]="saveChangeReason" placeholder="Ej: Mejorado prompt principal">
                            </mat-form-field>
                            <div class="save-dialog-actions">
                              <button mat-button (click)="showSaveDialog = false">Cancelar</button>
                              <button mat-raised-button color="primary" (click)="confirmSaveDefinition()"
                                      [disabled]="!saveVersionText.trim()">
                                <mat-icon>check</mat-icon>
                                Confirmar
                              </button>
                            </div>
                          </div>
                        </div>
                      }
                    </div>
                  }
                </div>
              </mat-tab>

              <!-- Tab Versiones (solo agentes existentes) -->
              @if (!isNewAgent()) {
                <mat-tab label="Versiones">
                  <div class="tab-content">
                    @if (loadingVersions()) {
                      <div class="loading-container">
                        <mat-spinner diameter="32"></mat-spinner>
                      </div>
                    } @else if (agentVersions().length === 0) {
                      <div class="empty-versions">
                        <mat-icon>history</mat-icon>
                        <p>No hay versiones anteriores. Cada guardado crea una nueva versión.</p>
                      </div>
                    } @else {
                      <div class="versions-list">
                        @for (ver of agentVersions(); track ver.id) {
                          <mat-card class="version-card">
                            <div class="version-row">
                              <div>
                                <strong>Versión {{ ver.version_number }}</strong>
                                <span class="version-date">{{ ver.created_at | date:'dd/MM/yyyy HH:mm' }}</span>
                              </div>
                              <button mat-stroked-button color="primary" (click)="restoreVersion(ver.version_number)">
                                <mat-icon>restore</mat-icon>
                                Restaurar
                              </button>
                            </div>
                            @if (ver.change_reason) {
                              <p class="version-reason">{{ ver.change_reason }}</p>
                            }
                          </mat-card>
                        }
                      </div>
                    }
                  </div>
                </mat-tab>
              }

              <!-- Tab de Test -->
              <mat-tab label="Estado">
                <div class="tab-content">
                  @if (testResult()) {
                    <div class="test-result" [class]="testResult()!.status">
                      <div class="result-header">
                        <mat-icon>{{ testResult()!.status === 'healthy' ? 'check_circle' : 'warning' }}</mat-icon>
                        <span>{{ testResult()!.status | uppercase }}</span>
                      </div>

                      <div class="checks-grid">
                        @for (check of getChecks(); track check.key) {
                          <div class="check-item" [class.passed]="check.value">
                            <mat-icon>{{ check.value ? 'check' : 'close' }}</mat-icon>
                            <span>{{ check.label }}</span>
                          </div>
                        }
                      </div>

                      <h4>Estado de Herramientas</h4>
                      <mat-list dense>
                        @for (tool of testResult()!.tools_status; track tool.id) {
                          <mat-list-item>
                            <mat-icon matListItemIcon [class]="tool.status">
                              {{ tool.status === 'ok' ? 'check_circle' : 'error' }}
                            </mat-icon>
                            <span matListItemTitle>{{ tool.name }}</span>
                          </mat-list-item>
                        }
                      </mat-list>
                    </div>
                  } @else {
                    <div class="empty-test">
                      <mat-icon>health_and_safety</mat-icon>
                      <p>Ejecuta un test para ver el estado del agente</p>
                      <button mat-raised-button color="primary" (click)="testAgent(selectedAgent.id)">
                        <mat-icon>play_arrow</mat-icon>
                        Ejecutar Test
                      </button>
                    </div>
                  }
                </div>
              </mat-tab>
            </mat-tab-group>
          </mat-card>
        }
      </mat-tab>

      <!-- Tab: Ejecutar -->
      <mat-tab label="Ejecutar" [disabled]="!executeAgent()">
        @if (executeAgent()) {
          <mat-card class="chat-panel">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>chat</mat-icon>
                Chat con {{ executeAgent()?.name }}
              </mat-card-title>
              <div class="chat-header-actions">
                <button mat-icon-button (click)="clearChat()" matTooltip="Limpiar chat">
                  <mat-icon>delete_sweep</mat-icon>
                </button>
                <button mat-icon-button (click)="closeExecution()" class="close-btn">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            </mat-card-header>
            <mat-card-content class="chat-content">
              <!-- Toggle: Usar config guardada vs Personalizar -->
              <div class="chat-config-bar">
                <div class="config-toggle-row">
                  <mat-slide-toggle 
                    [(ngModel)]="useSavedConfig" 
                    color="primary"
                    class="config-toggle">
                    Usar configuración guardada del agente
                  </mat-slide-toggle>
                </div>
                
                @if (useSavedConfig()) {
                  <!-- Mostrar info de la config guardada -->
                  <div class="saved-config-info">
                    @if (agentConfig.llm_provider) {
                      <div class="config-info-item">
                        <mat-icon>smart_toy</mat-icon>
                        <span class="config-label">Proveedor:</span>
                        <span class="config-value">{{ savedConfigProvider()?.name || 'Cargando...' }}</span>
                        <span class="config-type">({{ savedConfigProvider()?.type }})</span>
                      </div>
                      <div class="config-info-item">
                        <mat-icon>memory</mat-icon>
                        <span class="config-label">Modelo:</span>
                        <span class="config-value">{{ agentConfig.llm_model || savedConfigProvider()?.defaultModel || 'Por defecto' }}</span>
                      </div>
                    } @else {
                      <div class="no-config-warning">
                        <mat-icon>warning</mat-icon>
                        <span>No hay proveedor LLM configurado. <a (click)="switchToConfigTab()">Configurar ahora</a></span>
                      </div>
                    }
                  </div>
                } @else {
                  <!-- Selector LLM personalizado -->
                  <app-llm-selector
                    [(providerId)]="executeProviderId"
                    [(model)]="executeModel"
                    mode="compact"
                    (selectionChange)="onExecuteSelectionChange($event)">
                  </app-llm-selector>
                }
              </div>
              
              <!-- Chat -->
              <div class="chat-container-wrapper">
                <app-chat
                  [messages]="messages"
                  [features]="chatFeatures"
                  [isLoading]="executing"
                  [placeholder]="'Describe la tarea para ' + executeAgent()?.name + '...'"
                  [emptyMessage]="'Envía un mensaje para comenzar la conversación con ' + executeAgent()?.name"
                  (messageSent)="onChatMessageSent($event)"
                  (messageWithAttachments)="onChatMessageWithAttachments($event)">
                </app-chat>
              </div>
            </mat-card-content>
          </mat-card>
        }
      </mat-tab>
    </mat-tab-group>
  </div>
  `,
  styles: [`
    .subagents-page {
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin: 4px 0 0;
      font-size: 14px;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 64px;
      color: #666;
    }

    /* Subagents Grid */
    .subagents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }

    .subagent-card {
      border-radius: 12px;
      transition: transform 0.2s, box-shadow 0.2s;
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .subagent-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .subagent-card.selected {
      border: 2px solid #667eea;
    }

    .subagent-card mat-card-content {
      flex: 1 1 auto;
    }

    .subagent-card mat-card-actions {
      margin-top: auto;
      padding-top: 16px;
      border-top: 1px solid #f0f0f0;
    }

    .agent-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .agent-icon mat-icon {
      color: white;
      font-size: 24px;
    }

    .agent-icon.designer_agent {
      background: linear-gradient(135deg, #667eea 0%, #f093fb 100%);
    }

    .agent-icon.researcher_agent {
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }

    .agent-icon.sap_agent {
      background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
    }

    .agent-icon.sap_analyst {
      background: linear-gradient(135deg, #1e88e5 0%, #0d47a1 100%);
    }

    .agent-icon.communication_agent {
      background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }

    .agent-icon.rag_agent {
      background: linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%);
    }

    .agent-icon.mail_agent {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }

    .agent-icon.office_agent {
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }

    .status-chip {
      margin-left: auto !important;
      font-size: 10px !important;
    }

    .status-chip.active {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    .status-chip.inactive {
      background: #ffebee !important;
      color: #d32f2f !important;
    }

    .description {
      color: #666;
      font-size: 14px;
      margin-bottom: 16px;
    }

    .tools-section {
      margin-top: 12px;
    }

    .tools-label {
      font-size: 12px;
      color: #888;
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 8px;
    }

    .tools-label mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
      color: #667eea;
    }

    /* Mini grid for agent list cards */
    .tools-mini-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .tool-mini-item {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 3px 8px;
      background: #f1f5f9;
      border-radius: 6px;
      cursor: default;
    }

    .tmi-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
      color: #667eea;
    }

    .tmi-name {
      font-size: 11px;
      font-weight: 500;
      color: #334155;
    }

    .skills-section {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #f0f0f0;
    }

    .skills-label {
      font-size: 12px;
      color: #667eea;
      display: flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 8px;
    }

    .skills-label mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    .skills-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .skill-chip {
      font-size: 10px !important;
      min-height: 22px !important;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%) !important;
      color: #667eea !important;
      border: 1px solid rgba(102, 126, 234, 0.3) !important;
    }

    /* Detail Panel */
    .detail-panel {
      margin-top: 24px;
      border-radius: 12px;
    }

    .detail-panel mat-card-header {
      display: flex;
      align-items: center;
    }

    .detail-panel mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .close-btn {
      margin-left: auto !important;
    }

    .tab-content {
      padding: 24px;
    }

    /* Info Grid Layout */
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }

    .info-column {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .info-card {
      background: #f8f9fa;
      border-radius: 12px;
      border: 1px solid #e0e0e0;
      overflow: hidden;
    }

    .info-card-header {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
    }

    .info-card-header mat-icon {
      color: #667eea;
    }

    .info-card-header h3 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: #333;
      flex: 1;
    }

    .header-spinner {
      margin-left: auto;
    }

    .info-card-content {
      padding: 16px;
    }

    .info-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #eee;
    }

    .info-row:last-child {
      border-bottom: none;
    }

    .info-label {
      font-size: 13px;
      color: #666;
    }

    .info-value {
      font-size: 13px;
      font-weight: 500;
      color: #333;
    }

    .info-value.mono {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 12px;
      background: #e8e8e8;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .status-chip-small {
      font-size: 11px !important;
      min-height: 22px !important;
    }

    .description-text {
      margin: 0;
      font-size: 14px;
      line-height: 1.6;
      color: #555;
    }

    /* Tools Card */
    .tools-card {
      flex: 1;
    }

    .tools-card .info-card-header {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .add-tool-btn {
      margin-left: auto !important;
      font-size: 12px !important;
      height: 32px !important;
      line-height: 32px !important;
    }

    .add-tool-btn mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      margin-right: 4px;
    }

    .empty-tools {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
      color: #999;
      gap: 8px;
    }

    .empty-tools mat-icon {
      font-size: 36px;
      width: 36px;
      height: 36px;
      color: #ccc;
    }

    .empty-tools p {
      margin: 0;
      font-size: 13px;
    }

    .core-tools-toggle {
      margin-top: 12px;
      font-size: 13px;
    }

    /* Tool picker */
    .tool-picker {
      margin-bottom: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid #eee;
    }

    .tool-search-field {
      margin-bottom: 4px;
    }

    .tool-picker-grid {
      max-height: 240px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .tool-picker-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.15s;
    }

    .tool-picker-item:hover {
      background: #f0f4ff;
    }

    .tool-picker-item.already-added {
      opacity: 0.5;
    }

    .tp-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #667eea;
      flex-shrink: 0;
    }

    .tp-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .tp-name {
      font-size: 13px;
      font-weight: 500;
      color: #333;
    }

    .tp-desc {
      font-size: 11px;
      color: #888;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tp-check {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #4caf50;
      flex-shrink: 0;
    }

    .tp-add {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #bbb;
      flex-shrink: 0;
    }

    /* Tools grid (selected tools) */
    .tools-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }

    .tool-grid-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: #f1f5f9;
      border-radius: 8px;
      position: relative;
    }

    .tool-grid-item:hover {
      background: #e8eef6;
    }

    .tgi-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #667eea;
      flex-shrink: 0;
    }

    .tgi-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .tgi-name {
      font-size: 12px;
      font-weight: 500;
      color: #334155;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tgi-id {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 9px;
      color: #999;
    }

    .tgi-remove {
      width: 24px !important;
      height: 24px !important;
      line-height: 24px !important;
      opacity: 0;
      transition: opacity 0.15s;
      flex-shrink: 0;
    }

    .tool-grid-item:hover .tgi-remove {
      opacity: 1;
    }

    .tgi-remove mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: #999;
    }

    .info-section {
      margin-bottom: 24px;
    }

    .info-section h3 {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #333;
    }

    /* Config Form */
    .config-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .full-width {
      width: 100%;
    }

    .config-actions {
      margin-top: 16px;
    }

    /* Save dialog */
    .save-dialog-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .save-dialog {
      background: white;
      border-radius: 12px;
      padding: 24px;
      width: 420px;
      max-width: 90vw;
      box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    }

    .save-dialog h3 {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 0 0 20px;
      font-size: 18px;
      font-weight: 500;
    }

    .save-dialog h3 mat-icon {
      color: #667eea;
    }

    .save-dialog .full-width {
      width: 100%;
      margin-bottom: 4px;
    }

    .save-dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 16px;
    }

    /* Prompt Section */
    .prompt-section {
      margin-top: 16px;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 12px;
      border: 1px solid #e0e0e0;
    }

    .prompt-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      font-weight: 500;
      color: #667eea;
    }

    .prompt-header mat-icon {
      color: #667eea;
    }

    .prompt-header span {
      flex: 1;
    }

    .config-section-title {
      font-size: 14px;
      font-weight: 500;
      color: #555;
      margin: 16px 0 8px;
    }

    /* Config Section (LLM, etc.) */
    .config-section {
      padding: 16px;
      background: #f0f4ff;
      border-radius: 12px;
      border: 1px solid #d0d8f0;
      margin-bottom: 8px;
    }

    .config-section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
      font-weight: 500;
      color: #4a5568;
    }

    .config-section-header mat-icon {
      color: #667eea;
    }

    .config-row {
      display: flex;
      gap: 16px;
    }

    .half-width {
      flex: 1;
    }

    /* Provider Info */
    .no-providers-warning {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: #fff3e0;
      border-radius: 8px;
      color: #e65100;
    }

    .no-providers-warning a {
      color: #667eea;
      text-decoration: underline;
    }

    .provider-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .provider-name {
      font-weight: 500;
    }

    .provider-type {
      color: #888;
      font-size: 12px;
      background: #f0f0f0;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .default-chip {
      font-size: 10px !important;
      min-height: 18px !important;
      padding: 0 6px !important;
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    .provider-info {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 12px;
      margin: 8px 0;
    }

    .info-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #666;
      margin-bottom: 6px;
    }

    .info-row:last-child {
      margin-bottom: 0;
    }

    .info-row mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #888;
    }

    

    /* Test Result */
    .test-result {
      padding: 16px;
      border-radius: 8px;
    }

    .test-result.healthy {
      background: #e8f5e9;
    }

    .test-result.degraded {
      background: #fff3e0;
    }

    .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      margin-bottom: 16px;
    }

    .test-result.healthy .result-header mat-icon {
      color: #388e3c;
    }

    .test-result.degraded .result-header mat-icon {
      color: #f57c00;
    }

    .checks-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }

    .check-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      border-radius: 4px;
      background: white;
    }

    .check-item.passed mat-icon {
      color: #388e3c;
    }

    .check-item:not(.passed) mat-icon {
      color: #d32f2f;
    }

    mat-icon.ok {
      color: #388e3c;
    }

    mat-icon.missing_handler {
      color: #d32f2f;
    }

    .empty-test {
      text-align: center;
      padding: 32px;
      color: #666;
    }

    .empty-test mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #ccc;
    }

    /* Execute Panel */
    .execute-panel {
      margin-top: 24px;
      border-radius: 12px;
      border: 1px solid #e0e0e0;
    }

    .execute-panel mat-card-header {
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
      padding: 16px;
      border-radius: 12px 12px 0 0;
    }

    .execute-panel mat-card-title {
      display: flex;
      align-items: center;
      gap: 10px;
      color: #1a1a2e;
    }

    .execute-panel mat-card-title mat-icon {
      color: #667eea;
    }

    .execute-options {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .execute-result {
      padding: 16px;
      border-radius: 8px;
      margin: 16px;
    }

    .execute-result.success {
      background: #e8f5e9;
    }

    .execute-result.error {
      background: #ffebee;
    }

    /* Chat Panel */
    .chat-panel {
      margin-top: 24px;
      border-radius: 12px;
      border: 1px solid #e0e0e0;
    }

    .chat-panel mat-card-header {
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
      padding: 16px;
      border-radius: 12px 12px 0 0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .chat-panel mat-card-title {
      display: flex;
      align-items: center;
      gap: 10px;
      color: #1a1a2e;
      margin: 0;
    }

    .chat-panel mat-card-title mat-icon {
      color: #667eea;
    }

    .chat-header-actions {
      display: flex;
      gap: 8px;
    }

    .chat-content {
      display: flex;
      flex-direction: column;
      padding: 0 !important;
    }

    .chat-config-bar {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 16px;
      background: #fafafa;
      border-bottom: 1px solid #e0e0e0;
    }

    .config-toggle-row {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .config-toggle {
      font-size: 14px;
    }

    .saved-config-info {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px;
      background: #e3f2fd;
      border-radius: 8px;
      border-left: 4px solid #2196f3;
    }

    .config-info-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
    }

    .config-info-item mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #1976d2;
    }

    .config-label {
      font-weight: 500;
      color: #424242;
    }

    .config-value {
      color: #212121;
      font-weight: 600;
    }

    .config-type {
      color: #757575;
      font-size: 12px;
      text-transform: uppercase;
    }

    .no-config-warning {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px;
      background: #fff3e0;
      border-radius: 8px;
      border-left: 4px solid #ff9800;
      font-size: 14px;
      color: #e65100;
    }

    .no-config-warning mat-icon {
      color: #ff9800;
    }

    .no-config-warning a {
      color: #e65100;
      text-decoration: underline;
      cursor: pointer;
      font-weight: 500;
    }

    .config-field {
      flex: 1;
    }

    .chat-container-wrapper {
      flex: 1;
      min-height: 400px;
      max-height: 600px;
    }

    .chat-container-wrapper ::ng-deep .chat-container {
      border-radius: 0;
    }

    .execute-result .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }

    .execute-result.success .result-header mat-icon {
      color: #388e3c;
    }

    .execute-result.error .result-header mat-icon {
      color: #d32f2f;
    }

    .time {
      margin-left: auto;
      color: #888;
      font-size: 12px;
      background: rgba(0,0,0,0.05);
      padding: 4px 8px;
      border-radius: 12px;
    }

    /* Respuesta final mejorada */
    .final-response {
      background: #f8f9fa;
      border-radius: 12px;
      padding: 16px;
      margin-top: 16px;
      border: 1px solid #e0e0e0;
    }

    .response-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #667eea;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .response-label mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .response {
      white-space: pre-wrap;
      font-size: 14px;
      line-height: 1.6;
      margin: 0;
    }

    /* Tools usadas */
    .tools-used {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 16px;
      padding: 12px;
      background: rgba(102, 126, 234, 0.08);
      border-radius: 8px;
      font-size: 13px;
      color: #555;
    }

    .tools-used mat-icon {
      color: #667eea;
      font-size: 18px;
    }

    .tool-used-chip {
      font-size: 11px !important;
      background: white !important;
      border: 1px solid #667eea !important;
    }

    /* Imágenes generadas */
    .generated-images {
      margin-top: 16px;
    }

    .images-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #764ba2;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .images-label mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .images-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 16px;
    }

    .image-item {
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .image-item:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }

    .generated-image {
      width: 100%;
      display: block;
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

    /* Skills Tab Styles */
    .empty-skills {
      text-align: center;
      padding: 48px;
      color: #666;
    }

    .empty-skills mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
      margin-bottom: 16px;
    }

    .empty-skills h3 {
      margin: 0 0 8px;
      color: #333;
    }

    .empty-skills p {
      margin: 0;
      font-size: 14px;
    }

    .skills-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      gap: 16px;
    }

    .skills-info {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
      border-radius: 8px;
      font-size: 13px;
      color: #667eea;
      flex: 1;
    }

    .skills-info mat-icon {
      color: #667eea;
    }

    .add-skill-card {
      margin-bottom: 16px;
      border-radius: 12px !important;
      border: 2px dashed #667eea;
    }

    .add-skill-form {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .add-skill-form .full-width {
      grid-column: 1 / -1;
    }

    .add-skill-actions {
      grid-column: 1 / -1;
      display: flex;
      justify-content: flex-end;
    }

    .skill-delete-btn {
      width: 28px !important;
      height: 28px !important;
      line-height: 28px !important;
      margin-left: 8px;
    }

    .skill-delete-btn mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #999;
      transition: color 0.2s;
    }

    .skill-delete-btn:hover mat-icon {
      color: #f44336;
    }

    .dirty {
      color: #ff9800 !important;
    }

    .hint-unsaved {
      color: #ff9800;
      font-size: 12px;
      font-style: italic;
    }

    .skills-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .skill-panel {
      border-radius: 12px !important;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
    }

    .skill-panel .mat-expansion-panel-header {
      padding: 12px 24px;
    }

    .skill-icon {
      color: #667eea;
      margin-right: 12px;
    }

    .skill-name {
      font-weight: 600;
      color: #1a1a2e;
    }

    .skill-id {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 12px;
      color: #888;
      background: #f5f5f5;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .skill-content {
      padding: 16px 24px 24px;
    }

    .skill-description {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 12px 16px;
      background: #f8f9fa;
      border-radius: 8px;
      margin-bottom: 16px;
      font-size: 14px;
      color: #555;
    }

    .skill-description mat-icon {
      color: #667eea;
      font-size: 20px;
      margin-top: 2px;
    }

    .skill-loading {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 24px;
      color: #666;
    }

    .skill-editor {
      border: 1px solid #e0e0e0;
      border-radius: 12px;
      overflow: hidden;
    }

    .skill-editor .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
    }

    .editor-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #667eea;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .editor-label mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .editor-actions {
      display: flex;
      gap: 4px;
    }

    .skill-textarea {
      width: 100%;
      min-height: 300px;
      border: none;
      padding: 16px;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 13px;
      line-height: 1.6;
      resize: vertical;
      background: #fafbfc;
    }

    .skill-textarea:focus {
      outline: none;
      background: white;
    }

    .skill-textarea.expanded {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 1000;
      min-height: 100vh;
      border-radius: 0;
    }

    .editor-footer .hint-save {
      font-size: 12px;
      color: #666;
    }
    .editor-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: #f8f9fa;
      border-top: 1px solid #e0e0e0;
    }

    .char-count {
      font-size: 12px;
      color: #888;
    }

    /* Tests Tab Styles */
    .tests-tab-content {
      padding: 0 !important;
      height: calc(100vh - 400px);
      min-height: 500px;
    }

    .empty-tests {
      text-align: center;
      padding: 48px;
      color: #666;
    }

    .empty-tests mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
      margin-bottom: 16px;
    }

    .empty-versions {
      text-align: center;
      padding: 32px;
      color: #666;
    }
    .empty-versions mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #ccc;
      margin-bottom: 16px;
    }
    .versions-list { display: flex; flex-direction: column; gap: 12px; }
    .version-card { padding: 12px 16px; }
    .version-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .version-date { margin-left: 12px; font-size: 13px; color: #888; }
    .version-reason { font-size: 13px; color: #666; margin: 8px 0 0; }

    .info-edit-form .full-width { width: 100%; }
    .info-edit-form .form-row-info {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }
    .info-edit-form .form-row-info mat-form-field { flex: 1; }
    .info-edit-form .readonly-id {
      margin-bottom: 16px;
    }

    .tests-layout {
      display: flex;
      height: 100%;
      gap: 0;
    }

    .tests-list-panel {
      width: 350px;
      border-right: 1px solid #e0e0e0;
      display: flex;
      flex-direction: column;
      background: #fafafa;
    }

    .tests-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background: white;
      border-bottom: 1px solid #e0e0e0;
    }

    .tests-summary {
      display: flex;
      gap: 12px;
    }

    .summary-item {
      display: flex;
      align-items: center;
      gap: 4px;
      font-weight: 600;
      font-size: 13px;
    }

    .summary-item.passed { color: #388e3c; }
    .summary-item.failed { color: #d32f2f; }
    .summary-item.pending { color: #9e9e9e; }

    .summary-item mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .tests-categories {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
    }

    .category-panel {
      border-radius: 8px !important;
      margin-bottom: 8px !important;
      box-shadow: none !important;
    }

    .category-icon {
      color: #667eea;
      margin-right: 8px;
      font-size: 20px;
    }

    .tests-count {
      margin-left: 4px;
      color: #888;
      font-weight: 400;
      font-size: 12px;
    }

    .tests-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .test-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: white;
      border-radius: 6px;
      border-left: 3px solid #e0e0e0;
      cursor: pointer;
      transition: all 0.15s;
    }

    .test-item:hover {
      background: #f5f5f5;
    }

    .test-item.selected {
      background: #e3f2fd;
      border-left-color: #667eea;
    }

    .test-item.pass { border-left-color: #388e3c; }
    .test-item.fail { border-left-color: #d32f2f; }

    .test-status {
      width: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .test-status mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
    .test-status mat-icon.pass { color: #388e3c; }
    .test-status mat-icon.fail { color: #d32f2f; }
    .test-status mat-icon.pending { color: #bdbdbd; }

    .test-info {
      flex: 1;
      min-width: 0;
    }

    .test-id {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 10px;
      color: #667eea;
      font-weight: 600;
    }

    .test-name {
      font-size: 13px;
      font-weight: 500;
      color: #333;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .run-btn {
      opacity: 0;
      transition: opacity 0.15s;
    }

    .test-item:hover .run-btn {
      opacity: 1;
    }

    /* Panel derecho - Detalle */
    .test-detail-panel {
      flex: 1;
      padding: 20px;
      overflow-y: auto;
      background: white;
    }

    .detail-header {
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid #e0e0e0;
    }

    .detail-id {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 11px;
      color: #667eea;
      font-weight: 600;
      background: rgba(102, 126, 234, 0.1);
      padding: 2px 8px;
      border-radius: 4px;
    }

    .detail-header h3 {
      margin: 8px 0 4px;
      font-size: 18px;
      font-weight: 600;
    }

    .detail-header p {
      margin: 0;
      color: #666;
      font-size: 14px;
    }

    .detail-section {
      margin-bottom: 20px;
    }

    .detail-section h4 {
      font-size: 12px;
      font-weight: 600;
      color: #555;
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .input-task {
      padding: 12px;
      background: #f5f5f5;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.5;
    }

    .input-context {
      padding: 12px;
      background: #fff3e0;
      border-radius: 8px;
      font-size: 13px;
      margin-top: 8px;
      color: #e65100;
    }

    .criteria-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .criteria-list mat-checkbox {
      font-size: 14px;
    }

    .result-section {
      padding: 16px;
      background: #f0f7ff;
      border-radius: 12px;
      border: 1px solid #bbdefb;
    }

    .duration {
      font-weight: 400;
      font-size: 11px;
      color: #888;
      margin-left: 8px;
    }

    .output-error {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 12px;
      background: #ffebee;
      border-radius: 8px;
      color: #d32f2f;
      margin-top: 12px;
    }

    .output-images {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 12px 0;
    }

    .result-image {
      max-width: 100%;
      max-height: 300px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .output-response {
      white-space: pre-wrap;
      font-size: 14px;
      line-height: 1.6;
      padding: 12px;
      background: white;
      border-radius: 8px;
      margin-top: 12px;
      max-height: 200px;
      overflow-y: auto;
    }

    .no-result {
      text-align: center;
      padding: 40px 20px;
      background: #f5f5f5;
      border-radius: 12px;
      color: #666;
    }

    .no-result mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #bdbdbd;
      margin-bottom: 12px;
    }

    .no-result p {
      margin: 0 0 16px;
    }

    .no-selection {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #999;
    }

    .no-selection mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ddd;
      margin-bottom: 16px;
    }

    .detail-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      padding-top: 16px;
      border-top: 1px solid #e0e0e0;
    }
  `]
})
export class SubagentsComponent implements OnInit {
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);
  private sanitizer = inject(DomSanitizer);
  private llmSelectionService = inject(LlmSelectionService);
  private authService = inject(AuthService);
  private sseStream = inject(SseStreamService);

  subagents = signal<Subagent[]>([]);
  agentTools = signal<SubagentTool[]>([]);
  agentSkills = signal<Skill[]>([]);
  testResult = signal<TestResult | null>(null);
  executeResult = signal<ExecuteResult | null>(null);

  loading = signal(true);
  loadingTools = signal(false);
  loadingConfig = signal(false);
  loadingSkills = signal(false);
  loadingSkillContent = signal<string | null>(null);
  savingConfig = signal(false);
  savingSkill = signal(false);
  savingDefinition = signal(false);
  testingAgent = signal<string | null>(null);
  executing = signal(false);

  // Chat unificado
  messages = signal<ChatMessage[]>([]);
  chatFeatures = {
    intermediateSteps: true,
    images: true,
    videos: true,
    presentations: false,
    streaming: true,
    tokens: true,
    timestamps: true,
    clearButton: true,
    configPanel: false,
    attachments: true
  };

  selectedAgent: Subagent | null = null;
  isNewAgent = signal(false);
  executeAgent = signal<Subagent | null>(null);
  /** Session ID para memoria conversacional del agente (misma conversación = mismo session_id) */
  subagentSessionId = signal<string | null>(null);
  activeTabIndex = 0; // 0 = Agentes, 1 = Configuración, 2 = Ejecutar
  availableToolsList = signal<{ id: string; name: string; description: string }[]>([]);
  agentVersions = signal<{ id: number; version_number: number; created_at: string; change_reason?: string }[]>([]);
  loadingVersions = signal(false);
  restoringVersion = signal(false);

  showToolPicker = false;
  toolSearchText = '';
  showSaveDialog = false;
  saveVersionText = '';
  saveChangeReason = '';

  agentConfig: SubagentConfig = {
    enabled: true,
    settings: {}
  };

  // LLM Providers from database
  dbProviders = signal<DBLLMProvider[]>([]);
  loadingProviders = signal(false);
  availableModels = signal<string[]>([]);
  loadingModels = signal(false);
  customModelName = '';

  // Skills editor
  expandedSkill: string | null = null;
  expandSkillEditor = false;
  dirtySkills = new Set<string>();
  showAddSkillForm = false;
  addingSkill = signal(false);
  newSkill = { id: '', name: '', description: '', content: '' };

  // Tests
  testCategories = signal<TestCategory[]>([]);
  loadingTests = signal(false);
  runningTest = signal<string | null>(null);
  runningAllTests = signal(false);
  currentTestResult = signal<TestRunResult | null>(null);
  savingTestResult = signal(false);
  selectedTest: SubagentTest | null = null;
  criteriaChecks: boolean[] = [];
  testNotes = '';

  // Execute form - sincronizado con configuración del agente
  executeTask = '';
  executeContext = '';
  executeProviderId: string | number | null = null;
  executeModel = '';
  
  // Toggle: usar config guardada del agente vs personalizar
  useSavedConfig = signal(true); // Por defecto usar la config guardada
  
  savedConfigProvider(): DBLLMProvider | undefined {
    const providerId = this.agentConfig.llm_provider;
    if (!providerId) return undefined;
    return this.dbProviders().find(p => p.id.toString() === providerId.toString());
  }

  ngOnInit(): void {
    this.loadSubagents();
    this.loadProviders();
    this.loadAvailableTools();
  }

  loadAvailableTools(): void {
    this.http.get<{ tools: { id: string; name: string; description: string }[] }>(
      `${environment.apiUrl}/agent-definitions/meta/available-tools`
    ).subscribe({
      next: (res) => this.availableToolsList.set(res.tools || []),
      error: () => {}
    });
  }

  // --- Tool grid helpers ---

  getToolName(toolId: string): string {
    const t = this.availableToolsList().find(t => t.id === toolId);
    return t?.name || toolId;
  }

  getToolDescription(toolId: string): string {
    const t = this.availableToolsList().find(t => t.id === toolId);
    return t?.description || '';
  }

  getToolTypeIcon(toolId: string): string {
    const id = (toolId || '').toLowerCase();
    if (id.includes('bi_') || id.includes('sap') || id.includes('bw')) return 'storage';
    if (id.includes('search') || id.includes('rag') || id.includes('busca')) return 'search';
    if (id.includes('file') || id.includes('read') || id.includes('write')) return 'folder';
    if (id.includes('web') || id.includes('http') || id.includes('fetch')) return 'language';
    if (id.includes('exec') || id.includes('bash') || id.includes('shell')) return 'terminal';
    if (id.includes('date') || id.includes('time') || id.includes('calendario')) return 'schedule';
    if (id.includes('delegate') || id.includes('team')) return 'share';
    if (id.includes('reflect') || id.includes('think') || id.includes('plan')) return 'psychology';
    if (id.includes('slide') || id.includes('present')) return 'slideshow';
    if (id.includes('image') || id.includes('genera')) return 'palette';
    return 'extension';
  }

  filteredAvailableTools(): { id: string; name: string; description: string }[] {
    const search = (this.toolSearchText || '').toLowerCase().trim();
    const tools = this.availableToolsList();
    if (!search) return tools;
    return tools.filter(t =>
      t.id.toLowerCase().includes(search) ||
      (t.name || '').toLowerCase().includes(search) ||
      (t.description || '').toLowerCase().includes(search)
    );
  }

  addDomainTool(toolId: string): void {
    if (!this.selectedAgent) return;
    if (!this.selectedAgent.domain_tools) this.selectedAgent.domain_tools = [];
    if (this.selectedAgent.domain_tools.includes(toolId)) return;
    this.selectedAgent.domain_tools = [...this.selectedAgent.domain_tools, toolId];
  }

  removeDomainTool(toolId: string): void {
    if (!this.selectedAgent?.domain_tools) return;
    this.selectedAgent.domain_tools = this.selectedAgent.domain_tools.filter(t => t !== toolId);
  }

  loadSubagents(): void {
    this.loading.set(true);
    this.http.get<{ definitions: any[] }>(`${environment.apiUrl}/agent-definitions`)
      .subscribe({
        next: (response) => {
          const list = (response.definitions || []).map((d: any) => this.mapDefinitionToSubagent(d));
          this.subagents.set(list);
          this.loading.set(false);
        },
        error: (err) => {
          console.error('Error loading subagents:', err);
          this.snackBar.open('Error cargando agentes', 'Cerrar', { duration: 3000 });
          this.loading.set(false);
        }
      });
  }

  private mapDefinitionToSubagent(d: any): Subagent {
    const skills: Skill[] = (d.skills || []).map((s: any) => ({
      id: s.id || '',
      name: s.name || '',
      description: s.description || '',
      content: s.content ?? '',
      loaded: !!s.content
    }));
    return {
      id: d.agent_id,
      name: d.name || d.agent_id,
      description: d.description || '',
      version: d.version || '1.0.0',
      domain_tools: d.domain_tools || [],
      skills,
      status: d.is_enabled !== false ? 'active' : 'inactive',
      icon: d.icon || 'smart_toy',
      system_prompt: d.system_prompt,
      role: d.role,
      expertise: d.expertise,
      task_requirements: d.task_requirements,
      core_tools_enabled: d.core_tools_enabled !== false,
      is_enabled: d.is_enabled !== false,
      settings: d.settings || {}
    };
  }

  selectAgent(agent: Subagent): void {
    this.isNewAgent.set(false);
    this.selectedAgent = agent;
    this.activeTabIndex = 1;
    this.testResult.set(null);
    this.expandedSkill = null;
    this.dirtySkills.clear();
    this.selectedTest = null;
    this.currentTestResult.set(null);
    this.loadAgentTools(agent.id);
    this.loadAgentConfig(agent.id);
    this.agentSkills.set(agent.skills || []);
    this.loadingSkills.set(false);
    this.loadAgentTests(agent.id);
    this.loadAgentVersions(agent.id);
  }

  loadAgentVersions(agentId: string): void {
    this.loadingVersions.set(true);
    this.agentVersions.set([]);
    this.http.get<{ versions: any[] }>(`${environment.apiUrl}/agent-definitions/${agentId}/versions`)
      .subscribe({
        next: (res) => {
          this.agentVersions.set(res.versions || []);
          this.loadingVersions.set(false);
        },
        error: () => this.loadingVersions.set(false)
      });
  }

  restoreVersion(versionNumber: number): void {
    if (!this.selectedAgent || this.isNewAgent() || !confirm(`¿Restaurar versión ${versionNumber}?`)) return;
    this.restoringVersion.set(true);
    this.http.post<any>(
      `${environment.apiUrl}/agent-definitions/${this.selectedAgent.id}/restore/${versionNumber}`,
      {}
    ).subscribe({
      next: () => {
        this.restoringVersion.set(false);
        this.snackBar.open(`Versión ${versionNumber} restaurada`, 'Cerrar', { duration: 3000 });
        this.loadSubagents();
        const updated = this.subagents().find(a => a.id === this.selectedAgent!.id);
        if (updated) {
          this.selectedAgent = updated;
          this.agentSkills.set(updated.skills || []);
        }
      },
      error: () => this.restoringVersion.set(false)
    });
  }

  startNewAgent(): void {
    this.isNewAgent.set(true);
    this.selectedAgent = {
      id: '',
      name: '',
      description: '',
      version: '1.0.0',
      domain_tools: [],
      skills: [],
      status: 'active',
      icon: 'smart_toy',
      system_prompt: '',
      role: '',
      expertise: '',
      task_requirements: '',
      core_tools_enabled: true,
      is_enabled: true
    };
    this.activeTabIndex = 1;
    this.agentTools.set([]);
    this.agentSkills.set([]);
    this.agentConfig = { enabled: true, settings: {} };
    this.testCategories.set([]);
  }

  closeConfiguration(): void {
    this.activeTabIndex = 0;
    this.selectedAgent = null;
    this.isNewAgent.set(false);
  }

  loadAgentTools(agentId: string): void {
    this.loadingTools.set(true);
    this.http.get<any>(`${environment.apiUrl}/subagents/${agentId}/tools`)
      .subscribe({
        next: (response) => {
          this.agentTools.set(response.tools || []);
          this.loadingTools.set(false);
        },
        error: (err) => {
          console.error('Error loading tools:', err);
          this.loadingTools.set(false);
        }
      });
  }

  loadAgentConfig(agentId: string): void {
    this.loadingConfig.set(true);
    this.http.get<any>(`${environment.apiUrl}/subagents/${agentId}/config`)
      .subscribe({
        next: (response) => {
          this.agentConfig = response.config || { enabled: true, settings: {} };
          this.loadingConfig.set(false);
          
          // Cargar modelos del provider seleccionado
          if (this.agentConfig.llm_provider) {
            this.loadModelsForProvider(this.agentConfig.llm_provider);
          }
        },
        error: (err) => {
          console.error('Error loading config:', err);
          this.loadingConfig.set(false);
        }
      });
  }

  // LLM Provider helpers
  loadProviders(): void {
    this.loadingProviders.set(true);
    this.http.get<DBLLMProvider[]>(`${environment.apiUrl}/config/llm-providers?active_only=true`)
      .subscribe({
        next: (providers) => {
          this.dbProviders.set(providers);
          this.loadingProviders.set(false);
          
          // Si no hay proveedor seleccionado, usar el por defecto
          if (!this.agentConfig.llm_provider && providers.length > 0) {
            const defaultProvider = providers.find(p => p.isDefault) || providers[0];
            this.agentConfig.llm_provider = defaultProvider.id.toString();
          }
        },
        error: (err) => {
          console.error('Error loading providers:', err);
          this.loadingProviders.set(false);
        }
      });
  }

  getSelectedProvider(): DBLLMProvider | undefined {
    if (!this.agentConfig.llm_provider) return undefined;
    return this.dbProviders().find(p => 
      p.id.toString() === this.agentConfig.llm_provider?.toString()
    );
  }
  
  getProviderById(providerId: number | string | null | undefined): DBLLMProvider | undefined {
    if (!providerId) return undefined;
    return this.dbProviders().find(p => 
      p.id.toString() === providerId.toString()
    );
  }
  
  switchToConfigTab(): void {
    this.activeTabIndex = 1; // Tab de configuración
  }

  onProviderChange(newProviderId: any): void {
    // Limpiar modelo override al cambiar proveedor
    this.agentConfig.llm_model = '';
    this.customModelName = '';
    // Cargar modelos del nuevo provider
    this.loadModelsForProvider(newProviderId);
  }

  loadModelsForProvider(providerId: any): void {
    const provider = this.dbProviders().find(p => p.id.toString() === providerId?.toString());
    if (!provider) {
      this.availableModels.set([]);
      return;
    }

    this.loadingModels.set(true);
    
    // Pasar provider_type y api_key para providers que lo requieren (OpenAI-compatible, etc.)
    const params: any = { 
      provider_url: provider.baseUrl,
      provider_type: provider.type || 'ollama'
    };
    if (provider.apiKey) {
      params.api_key = provider.apiKey;
    }

    this.http.get<{ models: { name: string }[] }>(
      `${environment.apiUrl}/llm/models`,
      { params }
    ).subscribe({
      next: (response) => {
        const models = response.models.map(m => m.name);
        this.availableModels.set(models);
        this.loadingModels.set(false);
        
        // Si el modelo actual no está en la lista, ponerlo como custom
        if (this.agentConfig.llm_model && !models.includes(this.agentConfig.llm_model)) {
          this.customModelName = this.agentConfig.llm_model;
        }
      },
      error: () => {
        // En caso de error, al menos mostrar el modelo por defecto del provider
        const defaultModels = provider.defaultModel ? [provider.defaultModel] : [];
        this.availableModels.set(defaultModels);
        this.loadingModels.set(false);
      }
    });
  }

  saveConfig(): void {
    if (!this.selectedAgent) return;
    this.savingConfig.set(true);
    this.http.put<any>(`${environment.apiUrl}/subagents/${this.selectedAgent.id}/config`, this.agentConfig)
      .subscribe({
        next: () => {
          this.snackBar.open('Configuración LLM guardada', 'Cerrar', { duration: 3000 });
          this.savingConfig.set(false);
        },
        error: (err) => {
          this.snackBar.open('Error guardando configuración', 'Cerrar', { duration: 3000 });
          this.savingConfig.set(false);
        }
      });
  }

  promptSaveDefinition(): void {
    if (!this.selectedAgent) return;
    if (this.isNewAgent()) {
      this.saveDefinition(this.selectedAgent.version || '1.0.0', '');
      return;
    }
    this.saveVersionText = this.bumpVersion(this.selectedAgent.version || '1.0.0');
    this.saveChangeReason = '';
    this.showSaveDialog = true;
  }

  confirmSaveDefinition(): void {
    this.showSaveDialog = false;
    this.saveDefinition(this.saveVersionText.trim(), this.saveChangeReason.trim());
  }

  private bumpVersion(current: string): string {
    const parts = current.split('.').map(Number);
    if (parts.length === 3 && parts.every(n => !isNaN(n))) {
      parts[2]++;
      return parts.join('.');
    }
    return current;
  }

  saveDefinition(version: string, changeReason: string): void {
    if (!this.selectedAgent) return;
    const isNew = this.isNewAgent();
    if (isNew && !this.selectedAgent.id?.trim()) {
      this.snackBar.open('Indica el ID del agente en la pestaña Información', 'Cerrar', { duration: 4000 });
      return;
    }
    this.savingDefinition.set(true);
    const skills = this.agentSkills().map(s => ({
      id: s.id,
      name: s.name,
      description: s.description || '',
      content: s.content ?? ''
    }));
    const payload: any = {
      agent_id: this.selectedAgent.id.trim(),
      name: this.selectedAgent.name || this.selectedAgent.id,
      description: this.selectedAgent.description || '',
      role: this.selectedAgent.role || '',
      expertise: this.selectedAgent.expertise || '',
      task_requirements: this.selectedAgent.task_requirements || '',
      system_prompt: this.selectedAgent.system_prompt || '',
      domain_tools: this.selectedAgent.domain_tools || [],
      core_tools_enabled: this.selectedAgent.core_tools_enabled !== false,
      skills,
      is_enabled: this.selectedAgent.is_enabled !== false,
      version,
      icon: this.selectedAgent.icon || 'smart_toy',
      settings: this.selectedAgent.settings || {}
    };
    if (changeReason) {
      payload.change_reason = changeReason;
    }
    const apiUrl = `${environment.apiUrl}/agent-definitions`;
    const req = isNew
      ? this.http.post<any>(apiUrl, payload)
      : this.http.put<any>(`${apiUrl}/${this.selectedAgent.id}`, payload);
    req.subscribe({
      next: () => {
        this.savingDefinition.set(false);
        this.dirtySkills.clear();
        if (isNew) {
          this.snackBar.open('Agente creado', 'Cerrar', { duration: 3000 });
          this.loadSubagents();
          this.closeConfiguration();
        } else {
          this.selectedAgent!.version = version;
          this.snackBar.open(`Guardado v${version}`, 'Cerrar', { duration: 3000 });
          this.loadSubagents();
          this.loadAgentVersions(this.selectedAgent!.id);
          this.agentConfig.enabled = this.selectedAgent!.is_enabled !== false;
          this.http.put<any>(`${environment.apiUrl}/subagents/${this.selectedAgent!.id}/config`, this.agentConfig).subscribe();
        }
      },
      error: (err) => {
        this.savingDefinition.set(false);
        const d = err.error?.detail;
        const msg = typeof d === 'string' ? d : (d?.msg || err.message || 'Error guardando');
        this.snackBar.open(msg, 'Cerrar', { duration: 4000 });
      }
    });
  }

  testAgent(agentId: string): void {
    this.testingAgent.set(agentId);
    this.http.post<TestResult>(`${environment.apiUrl}/subagents/${agentId}/test`, {})
      .subscribe({
        next: (result) => {
          this.testResult.set(result);
          this.testingAgent.set(null);
          
          const status = result.status === 'healthy' ? 'OK' : 'Degradado';
          this.snackBar.open(`Test completado: ${status}`, 'Cerrar', { duration: 3000 });
        },
        error: (err) => {
          this.snackBar.open('Error ejecutando test', 'Cerrar', { duration: 3000 });
          this.testingAgent.set(null);
        }
      });
  }

  openExecutePanel(agent: Subagent): void {
    this.executeAgent.set(agent);
    this.executeResult.set(null);
    this.executeTask = '';
    this.executeContext = '';
    this.messages.set([]);
    this.subagentSessionId.set(null);
    this.activeTabIndex = 2;

    this._syncLlmFromConfig();

    this.http.get<any>(`${environment.apiUrl}/subagents/${agent.id}/config`)
      .subscribe({
        next: (response) => {
          this.agentConfig = response.config || { enabled: true, settings: {} };
          this._syncLlmFromConfig();
        },
        error: () => {
          this._syncLlmFromConfig();
        }
      });
  }

  private _syncLlmFromConfig(): void {
    if (this.agentConfig.llm_provider) {
      this.executeProviderId = this.agentConfig.llm_provider;

      const provider = this.dbProviders().find(p =>
        p.id.toString() === this.agentConfig.llm_provider?.toString()
      );

      if (provider) {
        this.executeModel = this.agentConfig.llm_model || provider.defaultModel || '';
      } else {
        this.executeModel = this.agentConfig.llm_model || '';
      }
    } else {
      const defaultProvider = this.dbProviders().find(p => p.isDefault);
      if (defaultProvider) {
        this.executeProviderId = defaultProvider.id;
        this.executeModel = defaultProvider.defaultModel || '';
      } else if (this.dbProviders().length > 0) {
        this.executeProviderId = this.dbProviders()[0].id;
        this.executeModel = this.dbProviders()[0].defaultModel || '';
      }
    }
  }

  closeExecution(): void {
    this.activeTabIndex = 0; // Switch back to subagents list
    this.executeAgent.set(null);
    this.messages.set([]);
    this.subagentSessionId.set(null);
    this.executeResult.set(null);
  }

  /**
   * Helper para obtener la configuración LLM actual (para tests y ejecución)
   */
  private getExecutionLlmConfig(): { llm_url: string; model: string; provider_type: string; api_key?: string } | null {
    const config = this.llmSelectionService.buildExecutionConfig(
      this.executeProviderId,
      this.executeModel
    );
    
    if (!config) return null;
    
    return {
      llm_url: config.provider_url,
      model: config.model,
      provider_type: config.provider_type,
      api_key: config.api_key
    };
  }

  async executeSubagent(): Promise<void> {
    const agent = this.executeAgent();
    if (!agent || !this.executeTask.trim()) {
      this.snackBar.open('Ingresa una tarea', 'Cerrar', { duration: 3000 });
      return;
    }

    this.executing.set(true);

    if (!this.skipUserMessageInChat) {
      const userMessage: ChatMessage = {
        role: 'user',
        content: this.executeTask,
        timestamp: new Date()
      };
      this.messages.update(msgs => [...msgs, userMessage]);
    }
    this.skipUserMessageInChat = false;

    let sessionId = this.subagentSessionId();
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      this.subagentSessionId.set(sessionId);
    }

    let payload: any = {
      task: this.executeTask,
      context: this.executeContext || null,
      session_id: sessionId
    };

    if (!this.useSavedConfig()) {
      const llmConfig = this.llmSelectionService.buildExecutionConfig(
        this.executeProviderId,
        this.executeModel
      );
      if (!llmConfig) {
        this.executing.set(false);
        this.snackBar.open('Selecciona un proveedor LLM válido', 'Cerrar', { duration: 3000 });
        return;
      }
      payload = {
        ...payload,
        llm_url: llmConfig.provider_url,
        model: llmConfig.model,
        provider_type: llmConfig.provider_type,
        api_key: llmConfig.api_key
      };
    }

    const result = await this.sseStream.stream({
      url: `${environment.apiUrl}/subagents/${agent.id}/execute/stream`,
      payload,
      messages: this.messages,
    });

    this.executing.set(false);
    if (result.error) {
      this.messages.update(msgs => [...msgs, {
        role: 'assistant' as const,
        content: result.error!,
        timestamp: new Date()
      }]);
      this.snackBar.open('Error ejecutando agente', 'Cerrar', { duration: 3000 });
    }
  }

  private skipUserMessageInChat = false;

  // Handler para mensajes del ChatComponent
  onChatMessageSent(message: string): void {
    this.executeTask = message;
    this.executeSubagent();
  }

  onChatMessageWithAttachments(event: {message: string; attachments: ChatAttachment[]}): void {
    const userEmail = this.authService.currentUser()?.email;
    const uploadUrl = `${environment.apiUrl}/workspace/files/upload${userEmail ? '?user_id=' + encodeURIComponent(userEmail) : ''}`;

    let completed = 0;
    const total = event.attachments.length;
    const uploadedPaths: string[] = [];

    for (const att of event.attachments) {
      att.uploadStatus = 'uploading';
      const formData = new FormData();
      formData.append('file', att.file);
      formData.append('path', 'uploads');
      this.http.post<any>(uploadUrl, formData).subscribe({
        next: (res) => {
          att.uploadStatus = 'done';
          att.workspacePath = res.path;
          uploadedPaths.push(res.path);
          completed++;
          if (completed === total) {
            this.sendMessageWithAttachmentContext(event.message, event.attachments, uploadedPaths);
          }
        },
        error: () => {
          att.uploadStatus = 'error';
          completed++;
          if (completed === total) {
            this.sendMessageWithAttachmentContext(event.message, event.attachments, uploadedPaths);
          }
        }
      });
    }
  }

  private sendMessageWithAttachmentContext(message: string, attachments: ChatAttachment[], paths: string[]): void {
    const fileList = paths.map(p => `/workspace/${p}`).join(', ');
    const prefix = paths.length === 1
      ? `[Archivo adjunto: ${fileList}]\n`
      : `[Archivos adjuntos: ${fileList}]\n`;
    const fullMessage = prefix + (message || 'Analiza el archivo adjunto.');

    this.messages.update(msgs => [...msgs, {
      role: 'user' as const,
      content: message || 'Analiza el archivo adjunto.',
      timestamp: new Date(),
      attachments
    }]);

    this.executeTask = fullMessage;
    this.skipUserMessageInChat = true;
    this.executeSubagent();
  }

  // Handler para cambios en el selector LLM de ejecución
  onExecuteSelectionChange(event: any): void {
    this.executeProviderId = event.providerId;
    this.executeModel = event.model;
  }

  clearChat(): void {
    this.messages.set([]);
    this.subagentSessionId.set(null);
    this.executeResult.set(null);
  }

  closeChat(): void {
    this.executeAgent.set(null);
    this.messages.set([]);
    this.subagentSessionId.set(null);
    this.executeResult.set(null);
  }

  getChecks(): Array<{key: string; label: string; value: boolean}> {
    const result = this.testResult();
    if (!result?.checks) return [];

    const labels: Record<string, string> = {
      registered: 'Registrado',
      has_tools: 'Tiene herramientas',
      all_handlers_present: 'Handlers OK'
    };

    return Object.entries(result.checks).map(([key, value]) => ({
      key,
      label: labels[key] || key,
      value
    }));
  }

  resetPrompt(): void {
    if (!this.selectedAgent || this.isNewAgent()) return;
    this.http.get<any>(`${environment.apiUrl}/agent-definitions/${this.selectedAgent.id}`).subscribe({
      next: (d) => {
        this.selectedAgent!.system_prompt = d.system_prompt ?? '';
        this.snackBar.open('Prompt recargado desde servidor', 'Cerrar', { duration: 2000 });
      },
      error: () => this.snackBar.open('Error recargando prompt', 'Cerrar', { duration: 2000 })
    });
  }

  // Skills methods
  loadAgentSkills(agentId: string): void {
    this.loadingSkills.set(true);
    this.agentSkills.set([]);
    
    this.http.get<any>(`${environment.apiUrl}/subagents/${agentId}/skills`)
      .subscribe({
        next: (response) => {
          this.agentSkills.set(response.skills || []);
          this.loadingSkills.set(false);
        },
        error: (err) => {
          console.error('Error loading skills:', err);
          this.agentSkills.set([]);
          this.loadingSkills.set(false);
        }
      });
  }

  toggleSkill(skill: Skill): void {
    if (this.expandedSkill === skill.id) {
      this.expandedSkill = null;
    } else {
      this.expandedSkill = skill.id;
      // Cargar contenido si no está cargado
      if (!skill.content && !skill.loaded) {
        this.loadSkillContent(skill);
      }
    }
  }

  loadSkillContent(skill: Skill): void {
    if (!this.selectedAgent) return;
    
    this.loadingSkillContent.set(skill.id);
    
    this.http.get<any>(`${environment.apiUrl}/subagents/${this.selectedAgent.id}/skills/${skill.id}`)
      .subscribe({
        next: (response) => {
          // Actualizar el skill en el array
          const skills = this.agentSkills();
          const idx = skills.findIndex(s => s.id === skill.id);
          if (idx >= 0) {
            skills[idx] = {
              ...skills[idx],
              content: response.content || '',
              loaded: true
            };
            this.agentSkills.set([...skills]);
          }
          this.loadingSkillContent.set(null);
        },
        error: (err) => {
          console.error('Error loading skill content:', err);
          this.snackBar.open('Error cargando contenido del skill', 'Cerrar', { duration: 3000 });
          this.loadingSkillContent.set(null);
        }
      });
  }

  markSkillDirty(skillId: string): void {
    this.dirtySkills.add(skillId);
  }

  saveSkillContent(skill: Skill): void {
    if (!this.selectedAgent || !skill.content) return;
    
    this.savingSkill.set(true);
    
    this.http.put<any>(`${environment.apiUrl}/subagents/${this.selectedAgent.id}/skills/${skill.id}`, {
      content: skill.content
    }).subscribe({
      next: () => {
        this.dirtySkills.delete(skill.id);
        this.savingSkill.set(false);
        this.snackBar.open(`Skill "${skill.name}" guardado`, 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error saving skill:', err);
        this.snackBar.open('Error guardando skill', 'Cerrar', { duration: 3000 });
        this.savingSkill.set(false);
      }
    });
  }

  copySkillContent(skill: Skill): void {
    if (!skill.content) return;

    navigator.clipboard.writeText(skill.content).then(() => {
      this.snackBar.open('Contenido copiado', 'Cerrar', { duration: 2000 });
    });
  }

  addSkill(): void {
    if (!this.selectedAgent || !this.newSkill.id || !this.newSkill.name) return;

    this.addingSkill.set(true);
    const agentId = this.selectedAgent.id;

    this.http.post<any>(
      `${environment.apiUrl}/agent-definitions/${agentId}/skills`,
      this.newSkill
    ).subscribe({
      next: () => {
        this.agentSkills.update(skills => [...skills, { ...this.newSkill, loaded: true }]);
        this.snackBar.open(`Skill "${this.newSkill.name}" añadido`, 'Cerrar', { duration: 3000 });
        this.newSkill = { id: '', name: '', description: '', content: '' };
        this.showAddSkillForm = false;
        this.addingSkill.set(false);
        this.loadSubagents();
      },
      error: (err) => {
        const msg = err.error?.detail || 'Error añadiendo skill';
        this.snackBar.open(msg, 'Cerrar', { duration: 4000 });
        this.addingSkill.set(false);
      }
    });
  }

  removeSkill(skill: Skill): void {
    if (!this.selectedAgent) return;
    if (!confirm(`¿Eliminar el skill "${skill.name}" de este agente?`)) return;

    const agentId = this.selectedAgent.id;

    this.http.delete<any>(
      `${environment.apiUrl}/agent-definitions/${agentId}/skills/${skill.id}`
    ).subscribe({
      next: () => {
        this.agentSkills.update(skills => skills.filter(s => s.id !== skill.id));
        this.snackBar.open(`Skill "${skill.name}" eliminado`, 'Cerrar', { duration: 3000 });
        this.loadSubagents();
      },
      error: (err) => {
        const msg = err.error?.detail || 'Error eliminando skill';
        this.snackBar.open(msg, 'Cerrar', { duration: 3000 });
      }
    });
  }

  saveSkillViaApi(skill: Skill): void {
    if (!this.selectedAgent || !skill.content) return;

    const agentId = this.selectedAgent.id;

    this.http.put<any>(
      `${environment.apiUrl}/agent-definitions/${agentId}/skills/${skill.id}`,
      { content: skill.content }
    ).subscribe({
      next: () => {
        this.dirtySkills.delete(skill.id);
        this.snackBar.open(`Skill "${skill.name}" guardado`, 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        const msg = err.error?.detail || 'Error guardando skill';
        this.snackBar.open(msg, 'Cerrar', { duration: 3000 });
      }
    });
  }

  // Tests methods
  loadAgentTests(agentId: string): void {
    this.loadingTests.set(true);
    this.testCategories.set([]);
    
    this.http.get<any>(`${environment.apiUrl}/subagents/${agentId}/tests`)
      .subscribe({
        next: (response) => {
          this.testCategories.set(response.categories || []);
          this.loadingTests.set(false);
        },
        error: (err) => {
          console.error('Error loading tests:', err);
          this.testCategories.set([]);
          this.loadingTests.set(false);
        }
      });
  }

  getTestStats(): { passed: number; failed: number; pending: number } {
    let passed = 0, failed = 0, pending = 0;
    
    for (const category of this.testCategories()) {
      for (const test of category.tests) {
        if (test.lastRun?.status === 'pass') passed++;
        else if (test.lastRun?.status === 'fail') failed++;
        else pending++;
      }
    }
    
    return { passed, failed, pending };
  }

  getCategoryStats(category: TestCategory): { passed: number } {
    let passed = 0;
    for (const test of category.tests) {
      if (test.lastRun?.status === 'pass') passed++;
    }
    return { passed };
  }

  getCategoryIcon(category: TestCategory): string {
    if (category.category === 'tool') return 'build';
    if (category.category === 'skill') return 'school';
    if (category.category === 'integration') return 'integration_instructions';
    return 'science';
  }

  getCategoryName(category: TestCategory): string {
    if (category.tool_id) return category.tool_id;
    if (category.skill_id) return `skill: ${category.skill_id}`;
    return category.category;
  }

  getStatusIcon(status?: string): string {
    if (status === 'pass') return 'check_circle';
    if (status === 'fail') return 'cancel';
    return 'radio_button_unchecked';
  }

  selectTest(test: SubagentTest): void {
    this.selectedTest = test;
    this.criteriaChecks = test.expected.criteria.map(() => false);
    this.testNotes = test.lastRun?.notes || '';
    this.currentTestResult.set(null);
  }

  runTest(test: SubagentTest): void {
    if (!this.selectedAgent) return;
    
    this.runningTest.set(test.id);
    this.selectedTest = test;
    this.criteriaChecks = test.expected.criteria.map(() => false);
    
    // Obtener configuración LLM para tests
    const llmConfig = this.getExecutionLlmConfig();
    if (!llmConfig) {
      this.snackBar.open('Configura un proveedor LLM válido', 'Cerrar', { duration: 3000 });
      this.runningTest.set(null);
      return;
    }
    
    this.http.post<TestRunResult>(
      `${environment.apiUrl}/subagents/${this.selectedAgent.id}/tests/${test.id}/run`,
      null,
      {
        params: {
          llm_url: llmConfig.llm_url,
          model: llmConfig.model,
          provider_type: llmConfig.provider_type,
          ...(llmConfig.api_key && { api_key: llmConfig.api_key })
        }
      }
    ).subscribe({
      next: (result) => {
        this.currentTestResult.set(result);
        this.runningTest.set(null);
        this.snackBar.open(`Test ${test.id} ejecutado`, 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error running test:', err);
        this.runningTest.set(null);
        this.snackBar.open('Error ejecutando test', 'Cerrar', { duration: 3000 });
      }
    });
  }

  async runAllTests(): Promise<void> {
    if (!this.selectedAgent) return;
    
    this.runningAllTests.set(true);
    
    const allTests: SubagentTest[] = [];
    for (const category of this.testCategories()) {
      allTests.push(...category.tests);
    }
    
    for (const test of allTests) {
      await this.runTestAsync(test);
    }
    
    this.runningAllTests.set(false);
    this.snackBar.open(`${allTests.length} tests ejecutados`, 'Cerrar', { duration: 3000 });
  }

  private runTestAsync(test: SubagentTest): Promise<void> {
    return new Promise((resolve) => {
      if (!this.selectedAgent) {
        resolve();
        return;
      }
      
      this.runningTest.set(test.id);
      
      // Obtener configuración LLM para tests
      const llmConfig = this.getExecutionLlmConfig();
      if (!llmConfig) {
        this.runningTest.set(null);
        resolve();
        return;
      }
      
      this.http.post<TestRunResult>(
        `${environment.apiUrl}/subagents/${this.selectedAgent.id}/tests/${test.id}/run`,
        null,
        {
          params: {
            llm_url: llmConfig.llm_url,
            model: llmConfig.model,
            provider_type: llmConfig.provider_type,
            ...(llmConfig.api_key && { api_key: llmConfig.api_key })
          }
        }
      ).subscribe({
        next: () => {
          this.runningTest.set(null);
          resolve();
        },
        error: () => {
          this.runningTest.set(null);
          resolve();
        }
      });
    });
  }

  updateCriteriaStatus(): void {
    // Los checkboxes se actualizan con ngModel
  }

  markTestResult(status: 'pass' | 'fail'): void {
    if (!this.selectedAgent || !this.selectedTest) return;
    
    this.savingTestResult.set(true);
    
    this.http.put<any>(
      `${environment.apiUrl}/subagents/${this.selectedAgent.id}/tests/${this.selectedTest.id}/result`,
      {
        status: status,
        notes: this.testNotes
      }
    ).subscribe({
      next: () => {
        // Actualizar el test en la lista
        const categories = this.testCategories();
        for (const category of categories) {
          const test = category.tests.find(t => t.id === this.selectedTest?.id);
          if (test) {
            test.lastRun = {
              status: status,
              timestamp: new Date().toISOString(),
              notes: this.testNotes
            };
          }
        }
        this.testCategories.set([...categories]);
        
        this.savingTestResult.set(false);
        this.snackBar.open(`Test marcado como ${status}`, 'Cerrar', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error saving test result:', err);
        this.savingTestResult.set(false);
        this.snackBar.open('Error guardando resultado', 'Cerrar', { duration: 3000 });
      }
    });
  }

  previewHtml(html: string): void {
    const win = window.open('', '_blank');
    if (win) {
      win.document.write(html);
      win.document.close();
    }
  }

  /**
   * Sanitiza una URL de imagen (HTTP o data URL) para uso seguro en el template.
   */
  sanitizeImageUrl(url: string): SafeUrl {
    if (!url) return '';
    // Data URLs necesitan bypass de seguridad
    if (url.startsWith('data:')) {
      return this.sanitizer.bypassSecurityTrustUrl(url);
    }
    // URLs HTTP normales no necesitan sanitización
    return url;
  }
}
