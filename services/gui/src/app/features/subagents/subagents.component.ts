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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatBadgeModule } from '@angular/material/badge';
import { MatListModule } from '@angular/material/list';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { environment } from '../../../environments/environment';

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
  default_provider?: string;
  default_model?: string;
  settings: Record<string, any>;
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
    images: Array<{url?: string; base64?: string}>;
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
    MatCheckboxModule
  ],
  template: `
    <div class="subagents-page">
      <div class="page-header">
        <div>
          <h1>Subagentes Especializados</h1>
          <p class="subtitle">Agentes de dominio para tareas específicas</p>
        </div>
        <button mat-raised-button color="primary" (click)="loadSubagents()" [disabled]="loading()">
          @if (loading()) {
            <mat-spinner diameter="20"></mat-spinner>
          } @else {
            <mat-icon>refresh</mat-icon>
          }
          Actualizar
        </button>
      </div>

      <!-- Grid de Subagentes -->
      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="48"></mat-spinner>
          <p>Cargando subagentes...</p>
        </div>
      } @else {
        <div class="subagents-grid">
          @for (agent of subagents(); track agent.id) {
            <mat-card class="subagent-card" [class.selected]="selectedAgent?.id === agent.id">
              <mat-card-header>
                <div class="agent-icon" [class]="agent.id">
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
                
                <div class="tools-section">
                  <span class="tools-label">Herramientas:</span>
                  <div class="tools-chips">
                    @for (tool of agent.domain_tools; track tool) {
                      <mat-chip class="tool-chip">{{ tool }}</mat-chip>
                    }
                  </div>
                </div>

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
              <h3>No hay subagentes registrados</h3>
              <p>Los subagentes se registran automáticamente al iniciar la API</p>
              <button mat-raised-button color="primary" (click)="loadSubagents()">
                <mat-icon>refresh</mat-icon>
                Recargar
              </button>
            </div>
          }
        </div>

        <!-- Panel de Detalles/Configuración -->
        @if (selectedAgent) {
          <mat-card class="detail-panel">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>{{ selectedAgent.icon }}</mat-icon>
                {{ selectedAgent.name }}
              </mat-card-title>
              <button mat-icon-button (click)="selectedAgent = null" class="close-btn">
                <mat-icon>close</mat-icon>
              </button>
            </mat-card-header>

            <mat-tab-group>
              <!-- Tab de Información -->
              <mat-tab label="Información">
                <div class="tab-content">
                  <div class="info-section">
                    <h3>Descripción</h3>
                    <p>{{ selectedAgent.description }}</p>
                  </div>

                  <div class="info-section">
                    <h3>Herramientas Disponibles</h3>
                    @if (loadingTools()) {
                      <mat-spinner diameter="24"></mat-spinner>
                    } @else {
                      <mat-list>
                        @for (tool of agentTools(); track tool.id) {
                          <mat-list-item>
                            <mat-icon matListItemIcon>build</mat-icon>
                            <div matListItemTitle>{{ tool.name }}</div>
                            <div matListItemLine>{{ tool.description }}</div>
                          </mat-list-item>
                        }
                      </mat-list>
                    }
                  </div>
                </div>
              </mat-tab>

              <!-- Tab de Skills -->
              <mat-tab label="Skills">
                <div class="tab-content">
                  @if (loadingSkills()) {
                    <div class="loading-container">
                      <mat-spinner diameter="32"></mat-spinner>
                    </div>
                  } @else if (agentSkills().length === 0) {
                    <div class="empty-skills">
                      <mat-icon>school</mat-icon>
                      <h3>Sin skills especializados</h3>
                      <p>Este subagente no tiene skills configurados</p>
                    </div>
                  } @else {
                    <div class="skills-header">
                      <div class="skills-info">
                        <mat-icon>auto_awesome</mat-icon>
                        <span>El LLM decide cuándo cargar cada skill según la tarea</span>
                      </div>
                    </div>

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
                                  <span class="char-count">{{ skill.content?.length || 0 }} caracteres</span>
                                  @if (dirtySkills.has(skill.id)) {
                                    <button mat-raised-button color="primary" (click)="saveSkillContent(skill)" [disabled]="savingSkill()">
                                      @if (savingSkill()) {
                                        <mat-spinner diameter="16"></mat-spinner>
                                      } @else {
                                        <mat-icon>save</mat-icon>
                                      }
                                      Guardar Skill
                                    </button>
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
                <div class="tab-content">
                  @if (loadingTests()) {
                    <div class="loading-container">
                      <mat-spinner diameter="32"></mat-spinner>
                    </div>
                  } @else if (testCategories().length === 0) {
                    <div class="empty-tests">
                      <mat-icon>science</mat-icon>
                      <h3>Sin tests definidos</h3>
                      <p>Este subagente no tiene tests configurados</p>
                    </div>
                  } @else {
                    <div class="tests-header">
                      <div class="tests-summary">
                        <span class="summary-item passed">
                          <mat-icon>check_circle</mat-icon>
                          {{ getTestStats().passed }} pass
                        </span>
                        <span class="summary-item failed">
                          <mat-icon>cancel</mat-icon>
                          {{ getTestStats().failed }} fail
                        </span>
                        <span class="summary-item pending">
                          <mat-icon>pending</mat-icon>
                          {{ getTestStats().pending }} pending
                        </span>
                      </div>
                      <button mat-raised-button color="primary" (click)="runAllTests()" [disabled]="runningAllTests()">
                        @if (runningAllTests()) {
                          <mat-spinner diameter="18"></mat-spinner>
                        } @else {
                          <mat-icon>play_arrow</mat-icon>
                        }
                        Ejecutar Todos
                      </button>
                    </div>

                    <div class="tests-categories">
                      @for (category of testCategories(); track category.file) {
                        <mat-expansion-panel class="category-panel">
                          <mat-expansion-panel-header>
                            <mat-panel-title>
                              <mat-icon class="category-icon">{{ getCategoryIcon(category) }}</mat-icon>
                              <span>{{ getCategoryName(category) }}</span>
                              <span class="tests-count">({{ category.tests.length }} tests)</span>
                            </mat-panel-title>
                            <mat-panel-description>
                              <span class="category-stats">
                                {{ getCategoryStats(category).passed }}/{{ category.tests.length }} ✓
                              </span>
                            </mat-panel-description>
                          </mat-expansion-panel-header>
                          
                          <div class="tests-list">
                            @for (test of category.tests; track test.id) {
                              <div class="test-item" [class]="test.lastRun?.status || 'pending'">
                                <div class="test-status">
                                  @if (runningTest() === test.id) {
                                    <mat-spinner diameter="20"></mat-spinner>
                                  } @else {
                                    <mat-icon [class]="test.lastRun?.status || 'pending'">
                                      {{ getStatusIcon(test.lastRun?.status) }}
                                    </mat-icon>
                                  }
                                </div>
                                <div class="test-info">
                                  <span class="test-id">{{ test.id }}</span>
                                  <span class="test-name">{{ test.name }}</span>
                                  <span class="test-desc">{{ test.description }}</span>
                                </div>
                                <div class="test-actions">
                                  <button mat-icon-button matTooltip="Ejecutar test" 
                                          (click)="runTest(test)" [disabled]="runningTest() === test.id">
                                    <mat-icon>play_arrow</mat-icon>
                                  </button>
                                  <button mat-icon-button matTooltip="Ver detalles" 
                                          (click)="selectTest(test)">
                                    <mat-icon>visibility</mat-icon>
                                  </button>
                                </div>
                              </div>
                            }
                          </div>
                        </mat-expansion-panel>
                      }
                    </div>

                    <!-- Panel de resultado del test seleccionado -->
                    @if (selectedTest) {
                      <mat-card class="test-result-panel">
                        <mat-card-header>
                          <mat-card-title>
                            <mat-icon>science</mat-icon>
                            {{ selectedTest.id }}: {{ selectedTest.name }}
                          </mat-card-title>
                          <button mat-icon-button (click)="selectedTest = null" class="close-btn">
                            <mat-icon>close</mat-icon>
                          </button>
                        </mat-card-header>
                        
                        <mat-card-content>
                          <div class="test-input">
                            <h4>Input</h4>
                            <div class="input-task">{{ selectedTest.input.task }}</div>
                            @if (selectedTest.input.context) {
                              <div class="input-context">{{ selectedTest.input.context }}</div>
                            }
                          </div>

                          <div class="test-criteria">
                            <h4>Criterios de validación</h4>
                            <div class="criteria-list">
                              @for (criterion of selectedTest.expected.criteria; track $index) {
                                <div class="criterion-item">
                                  <mat-checkbox [(ngModel)]="criteriaChecks[$index]" 
                                                (change)="updateCriteriaStatus()">
                                    {{ criterion }}
                                  </mat-checkbox>
                                </div>
                              }
                            </div>
                          </div>

                          @if (currentTestResult()) {
                            <div class="test-output">
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
                                <div class="output-content">
                                  @if (currentTestResult()!.result?.images?.length) {
                                    <div class="output-images">
                                      @for (img of currentTestResult()!.result.images; track $index) {
                                        <img [src]="img.url || ('data:image/png;base64,' + img.base64)" 
                                             class="result-image" alt="Generated image">
                                      }
                                    </div>
                                  }
                                  @if (currentTestResult()!.result?.data?.html) {
                                    <div class="output-html">
                                      <button mat-stroked-button (click)="previewHtml(currentTestResult()!.result.data.html)">
                                        <mat-icon>preview</mat-icon>
                                        Ver presentación
                                      </button>
                                    </div>
                                  }
                                  <div class="output-response">
                                    {{ currentTestResult()!.result?.response }}
                                  </div>
                                </div>
                              }
                            </div>
                          }

                          <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Notas</mat-label>
                            <textarea matInput [(ngModel)]="testNotes" rows="2" 
                                      placeholder="Observaciones sobre el resultado..."></textarea>
                          </mat-form-field>
                        </mat-card-content>

                        <mat-card-actions align="end">
                          <button mat-button color="warn" (click)="markTestResult('fail')" [disabled]="savingTestResult()">
                            <mat-icon>close</mat-icon>
                            Marcar Fail
                          </button>
                          <button mat-raised-button color="primary" (click)="markTestResult('pass')" [disabled]="savingTestResult()">
                            <mat-icon>check</mat-icon>
                            Marcar Pass
                          </button>
                        </mat-card-actions>
                      </mat-card>
                    }
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
                        Subagente habilitado
                      </mat-slide-toggle>

                      <!-- System Prompt - común a todos los subagentes -->
                      <div class="prompt-section">
                        <div class="prompt-header">
                          <mat-icon>psychology</mat-icon>
                          <span>System Prompt</span>
                          <button mat-icon-button matTooltip="Restaurar prompt por defecto" (click)="resetPrompt()">
                            <mat-icon>restore</mat-icon>
                          </button>
                        </div>
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Instrucciones del sistema</mat-label>
                          <textarea matInput [(ngModel)]="agentConfig.system_prompt" rows="8"
                                    placeholder="Instrucciones que definen el comportamiento del subagente..."></textarea>
                          <mat-hint>Define cómo el subagente procesa las solicitudes</mat-hint>
                        </mat-form-field>
                      </div>

                      @if (selectedAgent.id === 'designer_agent') {
                        <mat-divider></mat-divider>
                        <h4 class="config-section-title">Configuración de Media</h4>
                        
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Proveedor por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.default_provider">
                            <mat-option value="openai">OpenAI (DALL-E)</mat-option>
                            <mat-option value="replicate">Replicate (Flux/SD)</mat-option>
                          </mat-select>
                        </mat-form-field>

                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Modelo por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.default_model">
                            <mat-option value="dall-e-3">DALL-E 3</mat-option>
                            <mat-option value="dall-e-2">DALL-E 2</mat-option>
                            <mat-option value="flux-schnell">Flux Schnell</mat-option>
                          </mat-select>
                        </mat-form-field>

                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Tamaño por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.settings['default_size']">
                            <mat-option value="1024x1024">1024x1024 (Cuadrado)</mat-option>
                            <mat-option value="1792x1024">1792x1024 (Paisaje)</mat-option>
                            <mat-option value="1024x1792">1024x1792 (Retrato)</mat-option>
                          </mat-select>
                        </mat-form-field>
                      }

                      @if (selectedAgent.id === 'designer_agent') {
                        <mat-divider></mat-divider>
                        <h4 class="config-section-title">Configuración de Presentaciones</h4>
                        
                        <mat-form-field appearance="outline" class="full-width">
                          <mat-label>Estilo por defecto</mat-label>
                          <mat-select [(ngModel)]="agentConfig.settings['default_style']">
                            <mat-option value="modern">Moderno</mat-option>
                            <mat-option value="corporate">Corporativo</mat-option>
                            <mat-option value="minimal">Minimalista</mat-option>
                          </mat-select>
                        </mat-form-field>
                      }

                      <div class="config-actions">
                        <button mat-raised-button color="primary" (click)="saveConfig()" [disabled]="savingConfig()">
                          @if (savingConfig()) {
                            <mat-spinner diameter="20"></mat-spinner>
                          } @else {
                            <mat-icon>save</mat-icon>
                          }
                          Guardar Configuración
                        </button>
                      </div>
                    </div>
                  }
                </div>
              </mat-tab>

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
                      <p>Ejecuta un test para ver el estado del subagente</p>
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

        <!-- Panel de Ejecución -->
        @if (executeAgent) {
          <mat-card class="execute-panel">
            <mat-card-header>
              <mat-card-title>
                <mat-icon>play_circle</mat-icon>
                Ejecutar {{ executeAgent.name }}
              </mat-card-title>
              <button mat-icon-button (click)="executeAgent = null" class="close-btn">
                <mat-icon>close</mat-icon>
              </button>
            </mat-card-header>

            <mat-card-content>
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Tarea a ejecutar</mat-label>
                <textarea matInput [(ngModel)]="executeTask" rows="3" 
                          placeholder="Ej: Genera una imagen de un gato astronauta"></textarea>
              </mat-form-field>

              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Contexto adicional (opcional)</mat-label>
                <textarea matInput [(ngModel)]="executeContext" rows="2"></textarea>
              </mat-form-field>

              <div class="execute-options">
                <mat-form-field appearance="outline">
                  <mat-label>LLM URL</mat-label>
                  <input matInput [(ngModel)]="executeLlmUrl" placeholder="http://192.168.7.101:11434">
                </mat-form-field>

                <mat-form-field appearance="outline">
                  <mat-label>Modelo</mat-label>
                  <input matInput [(ngModel)]="executeModel" placeholder="gpt-oss:120b">
                </mat-form-field>
              </div>
            </mat-card-content>

            <mat-card-actions>
              <button mat-raised-button color="primary" (click)="executeSubagent()" [disabled]="executing()">
                @if (executing()) {
                  <mat-spinner diameter="20"></mat-spinner>
                  Ejecutando...
                } @else {
                  <mat-icon>play_arrow</mat-icon>
                  Ejecutar
                }
              </button>
            </mat-card-actions>

            @if (executeResult()) {
              <mat-divider></mat-divider>
              <div class="execute-result" [class]="executeResult()!.result.success ? 'success' : 'error'">
                <div class="result-header">
                  <mat-icon>{{ executeResult()!.result.success ? 'check_circle' : 'error' }}</mat-icon>
                  <span>{{ executeResult()!.result.success ? 'Éxito' : 'Error' }}</span>
                  <span class="time">{{ executeResult()!.result.execution_time_ms }}ms</span>
                </div>

                <!-- Tools usadas como chips -->
                @if (executeResult()!.result.tools_used?.length) {
                  <div class="tools-used">
                    <mat-icon>build</mat-icon>
                    <span>Herramientas:</span>
                    @for (tool of executeResult()!.result.tools_used; track tool) {
                      <mat-chip class="tool-used-chip">{{ tool }}</mat-chip>
                    }
                  </div>
                }

                <!-- Respuesta final con estilo mejorado -->
                <div class="final-response">
                  <div class="response-label">
                    <mat-icon>auto_awesome</mat-icon>
                    Respuesta
                  </div>
                  <p class="response">{{ executeResult()!.result.response }}</p>
                </div>

                <!-- Imágenes generadas -->
                @if (executeResult()!.result.images?.length) {
                  <div class="generated-images">
                    <div class="images-label">
                      <mat-icon>image</mat-icon>
                      Imágenes Generadas
                    </div>
                    <div class="images-grid">
                      @for (img of executeResult()!.result.images; track $index) {
                        <div class="image-item">
                          @if (img.url) {
                            <img [src]="img.url" alt="Generated image" class="generated-image">
                          }
                        </div>
                      }
                    </div>
                  </div>
                }
              </div>
            }
          </mat-card>
        }
      }
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
    }

    .subagent-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .subagent-card.selected {
      border: 2px solid #667eea;
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
      display: block;
      margin-bottom: 8px;
    }

    .tools-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tool-chip {
      font-size: 11px !important;
      min-height: 24px !important;
      background: #f5f5f5 !important;
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

    .skills-header {
      margin-bottom: 16px;
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
    }

    .skills-info mat-icon {
      color: #667eea;
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

    .tests-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 12px;
    }

    .tests-summary {
      display: flex;
      gap: 24px;
    }

    .summary-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-weight: 500;
      font-size: 14px;
    }

    .summary-item.passed { color: #388e3c; }
    .summary-item.failed { color: #d32f2f; }
    .summary-item.pending { color: #f57c00; }

    .summary-item mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .tests-categories {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .category-panel {
      border-radius: 12px !important;
    }

    .category-icon {
      color: #667eea;
      margin-right: 12px;
    }

    .tests-count {
      margin-left: 8px;
      color: #888;
      font-weight: 400;
    }

    .category-stats {
      font-size: 12px;
      color: #388e3c;
      font-weight: 500;
    }

    .tests-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 8px 0;
    }

    .test-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: #f8f9fa;
      border-radius: 8px;
      border-left: 3px solid #e0e0e0;
      transition: all 0.2s;
    }

    .test-item:hover {
      background: #f0f0f0;
    }

    .test-item.pass {
      border-left-color: #388e3c;
      background: rgba(56, 142, 60, 0.05);
    }

    .test-item.fail {
      border-left-color: #d32f2f;
      background: rgba(211, 47, 47, 0.05);
    }

    .test-item.pending {
      border-left-color: #f57c00;
    }

    .test-status {
      width: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .test-status mat-icon.pass { color: #388e3c; }
    .test-status mat-icon.fail { color: #d32f2f; }
    .test-status mat-icon.pending { color: #bdbdbd; }

    .test-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .test-id {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 11px;
      color: #667eea;
      font-weight: 600;
    }

    .test-name {
      font-weight: 500;
      color: #333;
    }

    .test-desc {
      font-size: 12px;
      color: #888;
    }

    .test-actions {
      display: flex;
      gap: 4px;
    }

    /* Test Result Panel */
    .test-result-panel {
      margin-top: 20px;
      border-radius: 12px;
      border: 2px solid #667eea;
    }

    .test-result-panel mat-card-header {
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
      padding: 16px;
      border-radius: 12px 12px 0 0;
    }

    .test-result-panel mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
    }

    .test-result-panel mat-card-title mat-icon {
      color: #667eea;
    }

    .test-input {
      margin-bottom: 20px;
    }

    .test-input h4, .test-criteria h4, .test-output h4 {
      font-size: 13px;
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
    }

    .input-context {
      padding: 12px;
      background: #fff3e0;
      border-radius: 8px;
      font-size: 13px;
      margin-top: 8px;
      color: #e65100;
    }

    .test-criteria {
      margin-bottom: 20px;
    }

    .criteria-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .criterion-item {
      font-size: 14px;
    }

    .test-output {
      margin-bottom: 20px;
    }

    .duration {
      font-weight: 400;
      font-size: 12px;
      color: #888;
    }

    .output-error {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px;
      background: #ffebee;
      border-radius: 8px;
      color: #d32f2f;
    }

    .output-content {
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .output-images {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 12px;
    }

    .result-image {
      max-width: 300px;
      max-height: 200px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .output-html {
      margin-bottom: 12px;
    }

    .output-response {
      white-space: pre-wrap;
      font-size: 14px;
      line-height: 1.6;
    }
  `]
})
export class SubagentsComponent implements OnInit {
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);

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
  testingAgent = signal<string | null>(null);
  executing = signal(false);

  selectedAgent: Subagent | null = null;
  executeAgent: Subagent | null = null;

  agentConfig: SubagentConfig = {
    enabled: true,
    settings: {}
  };

  // Skills editor
  expandedSkill: string | null = null;
  expandSkillEditor = false;
  dirtySkills = new Set<string>();

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

  // Execute form
  executeTask = '';
  executeContext = '';
  executeLlmUrl = 'http://192.168.7.101:11434';
  executeModel = 'gpt-oss:120b';

  ngOnInit(): void {
    this.loadSubagents();
  }

  loadSubagents(): void {
    this.loading.set(true);
    this.http.get<any>(`${environment.apiUrl}/subagents`)
      .subscribe({
        next: (response) => {
          this.subagents.set(response.subagents || []);
          this.loading.set(false);
        },
        error: (err) => {
          console.error('Error loading subagents:', err);
          this.snackBar.open('Error cargando subagentes', 'Cerrar', { duration: 3000 });
          this.loading.set(false);
        }
      });
  }

  selectAgent(agent: Subagent): void {
    this.selectedAgent = agent;
    this.testResult.set(null);
    this.expandedSkill = null;
    this.dirtySkills.clear();
    this.selectedTest = null;
    this.currentTestResult.set(null);
    this.loadAgentTools(agent.id);
    this.loadAgentConfig(agent.id);
    this.loadAgentSkills(agent.id);
    this.loadAgentTests(agent.id);
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
        },
        error: (err) => {
          console.error('Error loading config:', err);
          this.loadingConfig.set(false);
        }
      });
  }

  saveConfig(): void {
    if (!this.selectedAgent) return;

    this.savingConfig.set(true);
    this.http.put<any>(`${environment.apiUrl}/subagents/${this.selectedAgent.id}/config`, this.agentConfig)
      .subscribe({
        next: () => {
          this.snackBar.open('Configuración guardada', 'Cerrar', { duration: 3000 });
          this.savingConfig.set(false);
        },
        error: (err) => {
          this.snackBar.open('Error guardando configuración', 'Cerrar', { duration: 3000 });
          this.savingConfig.set(false);
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
    this.executeAgent = agent;
    this.executeResult.set(null);
    this.executeTask = '';
    this.executeContext = '';
  }

  executeSubagent(): void {
    if (!this.executeAgent || !this.executeTask.trim()) {
      this.snackBar.open('Ingresa una tarea', 'Cerrar', { duration: 3000 });
      return;
    }

    this.executing.set(true);
    this.executeResult.set(null);

    this.http.post<ExecuteResult>(`${environment.apiUrl}/subagents/${this.executeAgent.id}/execute`, {
      task: this.executeTask,
      context: this.executeContext || null,
      llm_url: this.executeLlmUrl,
      model: this.executeModel,
      provider_type: 'ollama'
    }).subscribe({
      next: (result) => {
        this.executeResult.set(result);
        this.executing.set(false);
        
        if (result.result.success) {
          this.snackBar.open('Ejecución completada', 'Cerrar', { duration: 3000 });
        } else {
          this.snackBar.open('Error en la ejecución', 'Cerrar', { duration: 3000 });
        }
      },
      error: (err) => {
        this.snackBar.open('Error ejecutando subagente', 'Cerrar', { duration: 3000 });
        this.executing.set(false);
      }
    });
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
    if (!this.selectedAgent) return;
    
    // Recargar config desde el servidor para obtener el prompt original
    this.loadAgentConfig(this.selectedAgent.id);
    this.snackBar.open('Prompt restaurado', 'Cerrar', { duration: 2000 });
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
    
    this.http.post<TestRunResult>(
      `${environment.apiUrl}/subagents/${this.selectedAgent.id}/tests/${test.id}/run`,
      null,
      {
        params: {
          llm_url: this.executeLlmUrl,
          model: this.executeModel,
          provider_type: 'ollama'
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
      
      this.http.post<TestRunResult>(
        `${environment.apiUrl}/subagents/${this.selectedAgent.id}/tests/${test.id}/run`,
        null,
        {
          params: {
            llm_url: this.executeLlmUrl,
            model: this.executeModel,
            provider_type: 'ollama'
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
}
