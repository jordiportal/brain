import { Component, OnInit, Input, Output, EventEmitter, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { StrapiService } from '../../../core/services/config.service';
import { ApiService } from '../../../core/services/api.service';
import { LlmProvider } from '../../../core/models';

interface ChainConfig {
  use_memory?: boolean;
  temperature?: number;
  max_memory_messages?: number;
  system_prompt?: string;
  max_iterations?: number;
  ask_before_continue?: boolean;
  agents?: string[];
  skills?: any[];
}

interface ChainFull {
  id: string;
  name: string;
  description: string;
  type: string;
  version: string;
  nodes: any[];
  edges: any[];
  config: ChainConfig;
}

interface ToolInfo {
  id: string;
  name: string;
  description: string;
  type?: string;
}

interface SubagentInfo {
  id: string;
  name: string;
  description: string;
  version: string;
  domain_tools: string[];
  status: string;
  icon: string;
}

interface ChainVersion {
  id: number;
  version_number: number;
  snapshot: any;
  changed_by?: string;
  change_reason?: string;
  created_at: string;
}

@Component({
  selector: 'app-chain-editor',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatCardModule, MatButtonModule, MatIconModule, MatInputModule, MatFormFieldModule,
    MatSelectModule, MatSliderModule, MatProgressSpinnerModule, MatSnackBarModule,
    MatTooltipModule, MatDividerModule, MatChipsModule, MatTabsModule, MatCheckboxModule,
    MatSlideToggleModule
  ],
  template: `
    <div class="editor-container">
      <!-- Header -->
      <div class="editor-header">
        <div class="chain-title">
          <mat-icon class="type-icon agent">psychology</mat-icon>
          <div>
            <h2>{{ editName || 'Cargando...' }}</h2>
            <span class="chain-meta">v{{ editVersion }} · {{ chain?.type | uppercase }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button mat-button (click)="close.emit()">
            <mat-icon>close</mat-icon>
            Cerrar
          </button>
          <button mat-raised-button color="primary"
                  [disabled]="saving() || !dirty()"
                  (click)="promptSave()">
            @if (saving()) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              <mat-icon>save</mat-icon>
            }
            Guardar
          </button>
        </div>
      </div>

      <!-- Save dialog overlay -->
      @if (showSaveDialog) {
        <div class="save-dialog-overlay" (click)="showSaveDialog = false">
          <div class="save-dialog" (click)="$event.stopPropagation()">
            <h3><mat-icon>save</mat-icon> Guardar versión</h3>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Nueva versión</mat-label>
              <input matInput [(ngModel)]="saveVersionText" placeholder="1.0.1">
              <mat-hint>Actual: {{ editVersion }}</mat-hint>
            </mat-form-field>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Motivo del cambio (opcional)</mat-label>
              <input matInput [(ngModel)]="saveChangeReason" placeholder="Ej: Añadidas herramientas de SAP">
            </mat-form-field>
            <div class="save-dialog-actions">
              <button mat-button (click)="showSaveDialog = false">Cancelar</button>
              <button mat-raised-button color="primary" (click)="confirmSave()"
                      [disabled]="!saveVersionText.trim()">
                <mat-icon>check</mat-icon> Confirmar
              </button>
            </div>
          </div>
        </div>
      }

      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="48"></mat-spinner>
          <p>Cargando asistente...</p>
        </div>
      } @else if (chain) {
        <mat-tab-group animationDuration="200ms">

          <!-- TAB: Información -->
          <mat-tab label="Información">
            <div class="tab-content">
              <!-- LLM Config -->
              <div class="llm-config-bar">
                <mat-form-field appearance="outline">
                  <mat-label>Proveedor LLM</mat-label>
                  <mat-select [(ngModel)]="selectedProviderId" (selectionChange)="onProviderChange()">
                    @for (p of llmProviders(); track p.id) {
                      <mat-option [value]="p.id">{{ p.name }} ({{ p.type }})</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Modelo</mat-label>
                  <mat-select [(ngModel)]="selectedModel" (selectionChange)="markDirty()" [disabled]="loadingModels()">
                    @if (loadingModels()) { <mat-option disabled>Cargando...</mat-option> }
                    @for (m of availableModels(); track m) {
                      <mat-option [value]="m">{{ m }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="info-grid">
                <div class="info-col">
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Nombre</mat-label>
                    <input matInput [(ngModel)]="editName" (ngModelChange)="markDirty()">
                  </mat-form-field>
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Descripción</mat-label>
                    <textarea matInput [(ngModel)]="editDescription" (ngModelChange)="markDirty()" rows="3"></textarea>
                  </mat-form-field>
                  <div class="config-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Temperatura</mat-label>
                      <input matInput type="number" step="0.1" min="0" max="2"
                             [(ngModel)]="editTemperature" (ngModelChange)="markDirty()">
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                      <mat-label>Max Iteraciones</mat-label>
                      <input matInput type="number" min="5" max="50"
                             [(ngModel)]="editMaxIterations" (ngModelChange)="markDirty()">
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                      <mat-label>Versión</mat-label>
                      <input matInput [value]="editVersion" readonly>
                    </mat-form-field>
                  </div>
                </div>
                <div class="info-col prompt-col">
                  <div class="prompt-header">
                    <h3><mat-icon>description</mat-icon> System Prompt</h3>
                    <span class="prompt-stats">{{ systemPrompt.length }} chars</span>
                  </div>
                  <textarea class="prompt-textarea"
                            [(ngModel)]="systemPrompt"
                            (ngModelChange)="markDirty()"
                            placeholder="Define el comportamiento del asistente..."></textarea>
                </div>
              </div>
            </div>
          </mat-tab>

          <!-- TAB: Herramientas -->
          <mat-tab label="Herramientas">
            <div class="tab-content">
              <div class="section-header">
                <h3><mat-icon>build</mat-icon> Herramientas asignadas ({{ selectedTools.length }})</h3>
                <button mat-stroked-button (click)="showToolPicker = !showToolPicker">
                  <mat-icon>{{ showToolPicker ? 'close' : 'add' }}</mat-icon>
                  {{ showToolPicker ? 'Cerrar' : 'Añadir' }}
                </button>
              </div>

              @if (showToolPicker) {
                <div class="picker">
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Buscar herramienta...</mat-label>
                    <input matInput [(ngModel)]="toolSearch">
                    <mat-icon matPrefix>search</mat-icon>
                  </mat-form-field>
                  <div class="picker-grid">
                    @for (tool of filteredAllTools(); track tool.id) {
                      <div class="picker-item" [class.selected]="selectedTools.includes(tool.id)"
                           (click)="toggleTool(tool.id)">
                        <mat-icon class="pi-icon">{{ getToolIcon(tool.type) }}</mat-icon>
                        <div class="pi-info">
                          <span class="pi-name">{{ tool.name }}</span>
                          <span class="pi-desc">{{ tool.description }}</span>
                        </div>
                        <mat-icon class="pi-check">{{ selectedTools.includes(tool.id) ? 'check_circle' : 'add_circle_outline' }}</mat-icon>
                      </div>
                    }
                  </div>
                </div>
              }

              @if (selectedTools.length > 0) {
                <div class="items-grid">
                  @for (toolId of selectedTools; track toolId) {
                    <div class="item-card">
                      <mat-icon class="ic-icon">{{ getToolIcon(getToolById(toolId)?.type) }}</mat-icon>
                      <div class="ic-info">
                        <span class="ic-name">{{ getToolById(toolId)?.name || toolId }}</span>
                        <span class="ic-id">{{ toolId }}</span>
                      </div>
                      <button mat-icon-button class="ic-remove" (click)="removeTool(toolId)" matTooltip="Quitar">
                        <mat-icon>close</mat-icon>
                      </button>
                    </div>
                  }
                </div>
              } @else if (!showToolPicker) {
                <div class="empty-section">
                  <mat-icon>build</mat-icon>
                  <p>No hay herramientas asignadas</p>
                </div>
              }
            </div>
          </mat-tab>

          <!-- TAB: Agentes -->
          <mat-tab label="Agentes">
            <div class="tab-content">
              <div class="section-header">
                <h3><mat-icon>smart_toy</mat-icon> Agentes asignados ({{ selectedAgents.length }})</h3>
                <button mat-stroked-button (click)="showAgentPicker = !showAgentPicker">
                  <mat-icon>{{ showAgentPicker ? 'close' : 'add' }}</mat-icon>
                  {{ showAgentPicker ? 'Cerrar' : 'Añadir' }}
                </button>
              </div>

              @if (showAgentPicker) {
                <div class="picker">
                  <div class="picker-grid">
                    @for (agent of allSubagents(); track agent.id) {
                      <div class="picker-item" [class.selected]="selectedAgents.includes(agent.id)"
                           (click)="toggleAgent(agent.id)">
                        <mat-icon class="pi-icon">{{ agent.icon || 'smart_toy' }}</mat-icon>
                        <div class="pi-info">
                          <span class="pi-name">{{ agent.name }}</span>
                          <span class="pi-desc">{{ agent.description }}</span>
                        </div>
                        <mat-icon class="pi-check">{{ selectedAgents.includes(agent.id) ? 'check_circle' : 'add_circle_outline' }}</mat-icon>
                      </div>
                    }
                  </div>
                </div>
              }

              @if (selectedAgents.length > 0) {
                <div class="items-grid">
                  @for (agentId of selectedAgents; track agentId) {
                    <div class="item-card">
                      <mat-icon class="ic-icon">{{ getAgentById(agentId)?.icon || 'smart_toy' }}</mat-icon>
                      <div class="ic-info">
                        <span class="ic-name">{{ getAgentById(agentId)?.name || agentId }}</span>
                        <span class="ic-id">{{ agentId }}</span>
                      </div>
                      <button mat-icon-button class="ic-remove" (click)="removeAgent(agentId)" matTooltip="Quitar">
                        <mat-icon>close</mat-icon>
                      </button>
                    </div>
                  }
                </div>
              } @else if (!showAgentPicker) {
                <div class="empty-section">
                  <mat-icon>smart_toy</mat-icon>
                  <p>No hay agentes asignados</p>
                </div>
              }
            </div>
          </mat-tab>

          <!-- TAB: Versiones -->
          <mat-tab label="Versiones">
            <div class="tab-content">
              @if (loadingVersions()) {
                <div class="loading-container small">
                  <mat-spinner diameter="32"></mat-spinner>
                </div>
              } @else if (versions().length === 0) {
                <div class="empty-section">
                  <mat-icon>history</mat-icon>
                  <p>No hay versiones guardadas aún</p>
                </div>
              } @else {
                <div class="versions-list">
                  @for (v of versions(); track v.id) {
                    <div class="version-item">
                      <div class="vi-info">
                        <span class="vi-number">#{{ v.version_number }}</span>
                        <span class="vi-version">v{{ v.snapshot?.version || '?' }}</span>
                        <span class="vi-date">{{ v.created_at | date:'dd/MM/yyyy HH:mm' }}</span>
                      </div>
                      @if (v.change_reason) {
                        <span class="vi-reason">{{ v.change_reason }}</span>
                      }
                      <button mat-stroked-button (click)="restoreVersion(v.version_number)"
                              matTooltip="Restaurar esta versión">
                        <mat-icon>restore</mat-icon> Restaurar
                      </button>
                    </div>
                  }
                </div>
              }
            </div>
          </mat-tab>
        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    .editor-container { display: flex; flex-direction: column; height: 100%; background: #f8fafc; }
    .editor-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: white; border-bottom: 1px solid #e2e8f0; }
    .chain-title { display: flex; align-items: center; gap: 16px; }
    .type-icon { width: 48px; height: 48px; font-size: 24px; display: flex; align-items: center; justify-content: center; border-radius: 12px; color: white; }
    .type-icon.agent { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .chain-title h2 { margin: 0; font-size: 20px; font-weight: 600; }
    .chain-meta { font-size: 12px; color: #64748b; }
    .header-actions { display: flex; gap: 12px; align-items: center; }
    .loading-container { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: #64748b; }
    .loading-container.small { padding: 48px; }

    .tab-content { padding: 24px; }

    /* Info tab */
    .llm-config-bar { display: flex; gap: 16px; margin-bottom: 16px; }
    .llm-config-bar mat-form-field { min-width: 220px; }
    .info-grid { display: flex; gap: 24px; }
    .info-col { flex: 1; }
    .prompt-col { flex: 1.5; display: flex; flex-direction: column; }
    .config-row { display: flex; gap: 16px; }
    .config-row mat-form-field { flex: 1; }
    .prompt-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .prompt-header h3 { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; color: #334155; }
    .prompt-stats { font-size: 12px; color: #94a3b8; }
    .prompt-textarea { flex: 1; min-height: 280px; width: 100%; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; font-family: 'Monaco','Menlo',monospace; font-size: 13px; line-height: 1.6; resize: none; background: #f8fafc; }
    .prompt-textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
    .full-width { width: 100%; }

    /* Picker shared */
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .section-header h3 { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600; color: #1e293b; }
    .picker { margin-bottom: 24px; padding: 16px; background: #f1f5f9; border-radius: 12px; }
    .picker-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; max-height: 320px; overflow-y: auto; }
    .picker-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: white; border-radius: 8px; cursor: pointer; border: 2px solid transparent; transition: border-color 0.15s; }
    .picker-item:hover { border-color: #cbd5e1; }
    .picker-item.selected { border-color: #667eea; background: #f0f0ff; }
    .pi-icon { color: #667eea; font-size: 20px; width: 20px; height: 20px; }
    .pi-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
    .pi-name { font-size: 13px; font-weight: 600; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pi-desc { font-size: 11px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pi-check { font-size: 20px; width: 20px; height: 20px; }
    .picker-item.selected .pi-check { color: #667eea; }
    .picker-item:not(.selected) .pi-check { color: #cbd5e1; }

    /* Items grid */
    .items-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
    .item-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: white; border-radius: 10px; border: 1px solid #e2e8f0; position: relative; }
    .item-card:hover .ic-remove { opacity: 1; }
    .ic-icon { color: #667eea; font-size: 22px; width: 22px; height: 22px; }
    .ic-info { flex: 1; display: flex; flex-direction: column; min-width: 0; }
    .ic-name { font-size: 13px; font-weight: 600; color: #1e293b; }
    .ic-id { font-size: 11px; color: #94a3b8; font-family: monospace; }
    .ic-remove { opacity: 0; transition: opacity 0.15s; }

    .empty-section { text-align: center; padding: 48px; color: #94a3b8; }
    .empty-section mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 8px; }
    .empty-section p { margin: 0; }

    /* Versions */
    .versions-list { display: flex; flex-direction: column; gap: 8px; }
    .version-item { display: flex; align-items: center; gap: 16px; padding: 12px 16px; background: white; border-radius: 10px; border: 1px solid #e2e8f0; }
    .vi-info { display: flex; align-items: center; gap: 12px; flex: 1; }
    .vi-number { font-weight: 700; color: #667eea; font-size: 14px; min-width: 30px; }
    .vi-version { font-family: monospace; font-size: 13px; color: #334155; background: #f1f5f9; padding: 2px 8px; border-radius: 4px; }
    .vi-date { font-size: 12px; color: #94a3b8; }
    .vi-reason { font-size: 12px; color: #64748b; font-style: italic; flex: 1; }

    /* Save dialog */
    .save-dialog-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); z-index: 1000; display: flex; align-items: center; justify-content: center; }
    .save-dialog { background: white; border-radius: 16px; padding: 24px; width: 400px; max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
    .save-dialog h3 { margin: 0 0 16px; display: flex; align-items: center; gap: 8px; font-size: 18px; }
    .save-dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
  `]
})
export class ChainEditorComponent implements OnInit {
  @Input() chainId!: string;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);
  private strapiService = inject(StrapiService);
  private apiService = inject(ApiService);

  chain: ChainFull | null = null;
  loading = signal(true);
  saving = signal(false);
  dirty = signal(false);

  // Editable fields
  editName = '';
  editDescription = '';
  editVersion = '1.0.0';
  editTemperature = 0.5;
  editMaxIterations = 15;
  systemPrompt = '';

  // Tools
  selectedTools: string[] = [];
  allTools = signal<ToolInfo[]>([]);
  showToolPicker = false;
  toolSearch = '';

  // Agents
  selectedAgents: string[] = [];
  allSubagents = signal<SubagentInfo[]>([]);
  showAgentPicker = false;

  // Versions
  versions = signal<ChainVersion[]>([]);
  loadingVersions = signal(false);
  showSaveDialog = false;
  saveVersionText = '';
  saveChangeReason = '';

  // LLM
  llmProviders = signal<LlmProvider[]>([]);
  availableModels = signal<string[]>([]);
  selectedProviderId: number | null = null;
  selectedModel = '';
  loadingModels = signal(false);

  ngOnInit(): void {
    this.loadChainDetails();
    this.loadLlmProviders();
    this.loadAllTools();
    this.loadVersions();
  }

  markDirty(): void { this.dirty.set(true); }

  // ---- Data loading ----

  loadChainDetails(): void {
    this.loading.set(true);
    this.http.get<any>(`${environment.apiUrl}/chains/${this.chainId}/details`).subscribe({
      next: (res) => {
        this.chain = res.chain;
        this.editName = res.chain.name;
        this.editDescription = res.chain.description || '';
        this.editVersion = res.chain_version || res.chain.version || '1.0.0';
        this.editTemperature = res.chain.config?.temperature ?? 0.5;
        this.editMaxIterations = res.chain.config?.max_iterations ?? 15;
        this.systemPrompt = res.system_prompt || '';
        this.selectedTools = res.chain_tools || [];
        this.selectedAgents = res.chain_agents || [];
        this.allSubagents.set(res.subagents || []);

        if (res.llm_provider) {
          this.selectedProviderId = res.llm_provider.id;
          this.selectedModel = res.llm_provider.defaultModel || '';
        }
        if (res.default_llm) {
          this.selectedProviderId = res.default_llm.provider_id;
          this.selectedModel = res.default_llm.model || '';
        }

        this.loading.set(false);
      },
      error: () => {
        this.snackBar.open('Error al cargar el asistente', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  loadAllTools(): void {
    this.http.get<{ tools: ToolInfo[] }>(`${environment.apiUrl}/agent-definitions/meta/available-tools`).subscribe({
      next: (res) => this.allTools.set(res.tools || []),
      error: () => {}
    });
  }

  loadVersions(): void {
    this.loadingVersions.set(true);
    this.http.get<{ versions: ChainVersion[] }>(`${environment.apiUrl}/chains/${this.chainId}/versions`).subscribe({
      next: (res) => { this.versions.set(res.versions || []); this.loadingVersions.set(false); },
      error: () => this.loadingVersions.set(false)
    });
  }

  loadLlmProviders(): void {
    this.strapiService.getLlmProviders().subscribe({
      next: (providers) => {
        this.llmProviders.set(providers);
        if (this.selectedProviderId) {
          const p = providers.find(pr => pr.id === this.selectedProviderId);
          if (p) this.loadModelsForProvider(p);
        } else if (providers.length > 0) {
          const active = providers.find(p => p.isActive) || providers[0];
          this.selectedProviderId = active.id;
          this.loadModelsForProvider(active);
        }
      },
      error: () => {}
    });
  }

  onProviderChange(): void {
    const p = this.llmProviders().find(pr => pr.id === this.selectedProviderId);
    if (p) { this.loadModelsForProvider(p); this.markDirty(); }
  }

  loadModelsForProvider(provider: LlmProvider): void {
    this.loadingModels.set(true);
    this.availableModels.set([]);
    this.apiService.getLlmModels({ providerUrl: provider.baseUrl, providerType: provider.type, apiKey: provider.apiKey }).subscribe({
      next: (res) => {
        const models = res.models?.map(m => m.name) || [];
        this.availableModels.set(models);
        if (!this.selectedModel && models.length > 0) {
          this.selectedModel = provider.defaultModel && models.includes(provider.defaultModel) ? provider.defaultModel : models[0];
        }
        this.loadingModels.set(false);
      },
      error: () => {
        if (provider.defaultModel) { this.availableModels.set([provider.defaultModel]); this.selectedModel = provider.defaultModel; }
        this.loadingModels.set(false);
      }
    });
  }

  // ---- Tools ----

  filteredAllTools(): ToolInfo[] {
    const s = this.toolSearch.toLowerCase();
    return this.allTools().filter(t => !s || t.name.toLowerCase().includes(s) || t.id.toLowerCase().includes(s) || (t.description || '').toLowerCase().includes(s));
  }

  toggleTool(id: string): void {
    if (this.selectedTools.includes(id)) this.removeTool(id);
    else { this.selectedTools = [...this.selectedTools, id]; this.markDirty(); }
  }

  removeTool(id: string): void {
    this.selectedTools = this.selectedTools.filter(t => t !== id);
    this.markDirty();
  }

  getToolById(id: string): ToolInfo | undefined {
    return this.allTools().find(t => t.id === id);
  }

  getToolIcon(type?: string): string {
    const icons: Record<string, string> = {
      core: 'extension', builtin: 'extension', domain: 'handyman',
      openapi: 'api', mcp: 'hub', custom: 'code', web: 'language',
      filesystem: 'folder', execution: 'terminal', reasoning: 'psychology'
    };
    return icons[type || ''] || 'build';
  }

  // ---- Agents ----

  toggleAgent(id: string): void {
    if (this.selectedAgents.includes(id)) this.removeAgent(id);
    else { this.selectedAgents = [...this.selectedAgents, id]; this.markDirty(); }
  }

  removeAgent(id: string): void {
    this.selectedAgents = this.selectedAgents.filter(a => a !== id);
    this.markDirty();
  }

  getAgentById(id: string): SubagentInfo | undefined {
    return this.allSubagents().find(a => a.id === id);
  }

  // ---- Save with versioning ----

  promptSave(): void {
    this.saveVersionText = this.bumpVersion(this.editVersion);
    this.saveChangeReason = '';
    this.showSaveDialog = true;
  }

  confirmSave(): void {
    this.showSaveDialog = false;
    this.executeSave(this.saveVersionText.trim(), this.saveChangeReason.trim());
  }

  private bumpVersion(current: string): string {
    const parts = current.split('.').map(Number);
    if (parts.length === 3 && parts.every(n => !isNaN(n))) { parts[2]++; return parts.join('.'); }
    return current;
  }

  private executeSave(version: string, changeReason: string): void {
    this.saving.set(true);

    const payload: any = {
      name: this.editName,
      description: this.editDescription,
      version,
      system_prompt: this.systemPrompt,
      tools: this.selectedTools,
      agents: this.selectedAgents,
      temperature: this.editTemperature,
      max_iterations: this.editMaxIterations,
    };
    if (changeReason) payload.change_reason = changeReason;

    this.http.put(`${environment.apiUrl}/chains/${this.chainId}/full`, payload).subscribe({
      next: () => {
        if (this.selectedProviderId) {
          this.http.put(`${environment.apiUrl}/chains/${this.chainId}/llm-config`, {
            provider_id: this.selectedProviderId, model: this.selectedModel
          }).subscribe();
        }

        this.editVersion = version;
        this.dirty.set(false);
        this.saving.set(false);
        this.snackBar.open(`Guardado v${version}`, 'Cerrar', { duration: 3000 });
        this.loadVersions();
        this.saved.emit();
      },
      error: (err) => {
        this.saving.set(false);
        const msg = err.error?.detail || 'Error al guardar';
        this.snackBar.open(msg, 'Cerrar', { duration: 5000 });
      }
    });
  }

  // ---- Versions ----

  restoreVersion(versionNumber: number): void {
    if (!confirm(`¿Restaurar a la versión #${versionNumber}?`)) return;
    this.http.post(`${environment.apiUrl}/chains/${this.chainId}/restore/${versionNumber}`, {}).subscribe({
      next: () => {
        this.snackBar.open(`Versión #${versionNumber} restaurada`, 'Cerrar', { duration: 3000 });
        this.loadChainDetails();
        this.loadVersions();
        this.dirty.set(false);
        this.saved.emit();
      },
      error: () => this.snackBar.open('Error restaurando versión', 'Cerrar', { duration: 3000 })
    });
  }
}
