import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatExpansionModule } from '@angular/material/expansion';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface AgentDefinition {
  id: number;
  agent_id: string;
  name: string;
  description: string | null;
  role: string | null;
  expertise: string | null;
  task_requirements: string | null;
  system_prompt: string;
  domain_tools: string[];
  core_tools_enabled: boolean;
  skills: { id: string; name: string; description: string; content: string }[];
  is_enabled: boolean;
  version: string;
  icon: string | null;
  settings: Record<string, any>;
  created_at: string | null;
  updated_at: string | null;
}

interface AgentVersion {
  id: number;
  agent_definition_id: number;
  version_number: number;
  snapshot: Record<string, any>;
  changed_by: string | null;
  change_reason: string | null;
  created_at: string | null;
}

interface AvailableTool {
  id: string;
  name: string;
  description: string;
}

@Component({
  selector: 'app-agent-definitions',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatTabsModule,
    MatExpansionModule,
  ],
  template: `
    <div class="section-header">
      <h2>Agentes</h2>
      <button mat-raised-button color="primary" (click)="startCreate()">
        <mat-icon>add</mat-icon>
        Nuevo Agente
      </button>
    </div>

    <!-- Editor panel -->
    @if (editing()) {
      <mat-card class="form-card">
        <mat-card-header>
          <mat-card-title>{{ isNew() ? 'Nuevo' : 'Editar' }} Agente</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <mat-tab-group animationDuration="150ms">
            <!-- General tab -->
            <mat-tab label="General">
              <div class="tab-inner">
                <form [formGroup]="form">
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>ID</mat-label>
                      <input matInput formControlName="agent_id" placeholder="my_agent"
                             [readonly]="!isNew()">
                      <mat-hint>Identificador unico (snake_case)</mat-hint>
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                      <mat-label>Nombre</mat-label>
                      <input matInput formControlName="name" placeholder="Mi Agente">
                    </mat-form-field>
                  </div>
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Descripcion</mat-label>
                    <input matInput formControlName="description">
                  </mat-form-field>
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Rol</mat-label>
                      <input matInput formControlName="role" placeholder="Especialista en...">
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                      <mat-label>Icono</mat-label>
                      <input matInput formControlName="icon" placeholder="smart_toy">
                      <mat-icon matSuffix>{{ form.get('icon')?.value || 'smart_toy' }}</mat-icon>
                    </mat-form-field>
                  </div>
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Expertise</mat-label>
                    <textarea matInput formControlName="expertise" rows="2"></textarea>
                  </mat-form-field>
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Requisitos de tarea</mat-label>
                    <input matInput formControlName="task_requirements">
                  </mat-form-field>
                  <div class="form-row">
                    <mat-slide-toggle formControlName="is_enabled" color="primary">
                      Habilitado
                    </mat-slide-toggle>
                    <mat-slide-toggle formControlName="core_tools_enabled" color="primary">
                      Core tools
                    </mat-slide-toggle>
                  </div>
                </form>
              </div>
            </mat-tab>

            <!-- Prompt tab -->
            <mat-tab label="Prompt">
              <div class="tab-inner">
                <mat-form-field appearance="outline" class="full-width prompt-field">
                  <mat-label>System Prompt</mat-label>
                  <textarea matInput [formControl]="$any(form.get('system_prompt'))"
                            rows="20" class="monospace"></textarea>
                  <mat-hint>{{ form.get('system_prompt')?.value?.length || 0 }} caracteres</mat-hint>
                </mat-form-field>
              </div>
            </mat-tab>

            <!-- Tools tab -->
            <mat-tab label="Tools">
              <div class="tab-inner">
                <p class="info-text">Selecciona las herramientas de dominio que este agente puede usar.</p>
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Domain Tools</mat-label>
                  <mat-select [formControl]="$any(form.get('domain_tools'))" multiple>
                    @for (tool of availableTools(); track tool.id) {
                      <mat-option [value]="tool.id">
                        {{ tool.id }} — {{ tool.description | slice:0:60 }}
                      </mat-option>
                    }
                  </mat-select>
                  <mat-hint>{{ form.get('domain_tools')?.value?.length || 0 }} tools seleccionadas</mat-hint>
                </mat-form-field>
              </div>
            </mat-tab>

            <!-- Skills tab -->
            <mat-tab label="Skills">
              <div class="tab-inner">
                <div class="section-header">
                  <p class="info-text">Skills con contenido markdown embebido.</p>
                  <button mat-stroked-button (click)="addSkill()">
                    <mat-icon>add</mat-icon> Anadir Skill
                  </button>
                </div>
                @for (skill of skillsArray.controls; track skill; let i = $index) {
                  <mat-expansion-panel>
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        {{ skill.get('name')?.value || 'Nuevo Skill' }}
                      </mat-panel-title>
                      <mat-panel-description>
                        {{ skill.get('id')?.value }}
                      </mat-panel-description>
                    </mat-expansion-panel-header>
                    <div [formGroup]="$any(skill)">
                      <div class="form-row">
                        <mat-form-field appearance="outline">
                          <mat-label>ID</mat-label>
                          <input matInput formControlName="id">
                        </mat-form-field>
                        <mat-form-field appearance="outline">
                          <mat-label>Nombre</mat-label>
                          <input matInput formControlName="name">
                        </mat-form-field>
                      </div>
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Descripcion</mat-label>
                        <input matInput formControlName="description">
                      </mat-form-field>
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Contenido (Markdown)</mat-label>
                        <textarea matInput formControlName="content" rows="12" class="monospace"></textarea>
                        <mat-hint>{{ skill.get('content')?.value?.length || 0 }} caracteres</mat-hint>
                      </mat-form-field>
                      <button mat-button color="warn" (click)="removeSkill(i)">
                        <mat-icon>delete</mat-icon> Eliminar skill
                      </button>
                    </div>
                  </mat-expansion-panel>
                }
              </div>
            </mat-tab>

            <!-- Versions tab -->
            @if (!isNew()) {
              <mat-tab label="Versiones">
                <div class="tab-inner">
                  @if (loadingVersions()) {
                    <mat-spinner diameter="32"></mat-spinner>
                  } @else if (versions().length === 0) {
                    <p class="info-text">No hay versiones anteriores.</p>
                  } @else {
                    <div class="versions-list">
                      @for (ver of versions(); track ver.id) {
                        <mat-card class="version-card">
                          <div class="version-header">
                            <div>
                              <strong>Version {{ ver.version_number }}</strong>
                              <span class="version-date">{{ ver.created_at | date:'dd/MM/yyyy HH:mm' }}</span>
                            </div>
                            <button mat-stroked-button color="primary"
                                    (click)="restoreVersion(ver.version_number)"
                                    matTooltip="Restaurar esta version">
                              <mat-icon>restore</mat-icon> Restaurar
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
          </mat-tab-group>

          <div class="form-actions">
            <button mat-button (click)="cancelEdit()">Cancelar</button>
            <button mat-raised-button color="primary" (click)="save()" [disabled]="saving() || form.invalid">
              @if (saving()) {
                <mat-spinner diameter="20"></mat-spinner>
              } @else {
                <mat-icon>save</mat-icon> Guardar
              }
            </button>
          </div>
        </mat-card-content>
      </mat-card>
    }

    <!-- Agents list -->
    <div class="providers-list">
      @for (agent of agents(); track agent.agent_id) {
        <mat-card class="provider-card">
          <div class="provider-header">
            <div class="provider-info">
              <mat-icon class="provider-type-icon agent-icon">{{ agent.icon || 'smart_toy' }}</mat-icon>
              <div>
                <h3>{{ agent.name }}</h3>
                <p>{{ agent.description }}</p>
              </div>
            </div>
            <mat-chip [class]="agent.is_enabled ? 'active' : 'inactive'">
              {{ agent.is_enabled ? 'Activo' : 'Inactivo' }}
            </mat-chip>
          </div>
          <div class="provider-details">
            <span><strong>ID:</strong> {{ agent.agent_id }}</span>
            <span><strong>Tools:</strong> {{ agent.domain_tools.length }}</span>
            <span><strong>Skills:</strong> {{ agent.skills.length }}</span>
            <span><strong>Version:</strong> {{ agent.version }}</span>
          </div>
          <div class="provider-actions">
            <button mat-icon-button (click)="startEdit(agent)" matTooltip="Editar">
              <mat-icon>edit</mat-icon>
            </button>
            <button mat-icon-button color="warn" (click)="deleteAgent(agent)" matTooltip="Eliminar">
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </mat-card>
      } @empty {
        <div class="empty-state">
          <mat-icon>smart_toy</mat-icon>
          <p>No hay agentes definidos</p>
          <button mat-stroked-button (click)="startCreate()">Crear el primero</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }
    h2 { margin: 0; font-size: 18px; font-weight: 600; }
    .form-card { margin-bottom: 24px; border: 1px solid #e0e0e0; }
    .tab-inner { padding: 16px 0; }
    .form-row {
      display: flex; gap: 16px; margin-bottom: 16px; align-items: center;
    }
    .form-row mat-form-field { flex: 1; }
    .full-width { width: 100%; }
    .prompt-field textarea { min-height: 300px; }
    .monospace { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; }
    .form-actions {
      display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; padding-top: 16px;
      border-top: 1px solid #eee;
    }
    .providers-list { display: grid; gap: 16px; }
    .provider-card { padding: 16px; border-radius: 8px; }
    .provider-header {
      display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;
    }
    .provider-info { display: flex; gap: 12px; align-items: center; }
    .provider-type-icon {
      width: 48px; height: 48px; border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-size: 24px; background: #f5f5f5;
    }
    .agent-icon { background: #e3f2fd; color: #1565c0; }
    .provider-info h3 { margin: 0; font-size: 16px; font-weight: 600; }
    .provider-info p { margin: 4px 0 0; font-size: 13px; color: #666; }
    mat-chip.active { background: #e8f5e9 !important; color: #388e3c !important; }
    mat-chip.inactive { background: #fafafa !important; color: #9e9e9e !important; }
    .provider-details {
      display: flex; gap: 24px; font-size: 13px; color: #666; margin-bottom: 12px;
    }
    .provider-actions { display: flex; justify-content: flex-end; gap: 8px; }
    .empty-state { text-align: center; padding: 48px; color: #666; }
    .empty-state mat-icon { font-size: 64px; width: 64px; height: 64px; color: #ccc; margin-bottom: 16px; }
    .info-text { color: #666; font-size: 14px; margin: 0 0 16px; }
    .versions-list { display: grid; gap: 12px; }
    .version-card { padding: 12px 16px; }
    .version-header {
      display: flex; justify-content: space-between; align-items: center;
    }
    .version-date { margin-left: 12px; font-size: 13px; color: #888; }
    .version-reason { font-size: 13px; color: #666; margin: 8px 0 0; }
    mat-expansion-panel { margin-bottom: 12px; }
  `]
})
export class AgentDefinitionsComponent implements OnInit {
  private readonly API = `${environment.apiUrl}/agent-definitions`;

  agents = signal<AgentDefinition[]>([]);
  availableTools = signal<AvailableTool[]>([]);
  editing = signal(false);
  isNew = signal(false);
  saving = signal(false);
  versions = signal<AgentVersion[]>([]);
  loadingVersions = signal(false);

  form: FormGroup;

  get skillsArray(): FormArray {
    return this.form.get('skills') as FormArray;
  }

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private snackBar: MatSnackBar,
  ) {
    this.form = this._buildForm();
  }

  ngOnInit(): void {
    this.loadAgents();
    this.loadAvailableTools();
  }

  loadAgents(): void {
    this.http.get<{ definitions: AgentDefinition[] }>(this.API).subscribe({
      next: (res) => this.agents.set(res.definitions),
      error: () => this.snackBar.open('Error cargando agentes', 'Cerrar', { duration: 3000 }),
    });
  }

  loadAvailableTools(): void {
    this.http.get<{ tools: AvailableTool[] }>(`${this.API}/meta/available-tools`).subscribe({
      next: (res) => this.availableTools.set(res.tools),
      error: () => {},
    });
  }

  startCreate(): void {
    this.form = this._buildForm();
    this.isNew.set(true);
    this.editing.set(true);
    this.versions.set([]);
  }

  startEdit(agent: AgentDefinition): void {
    this.form = this._buildForm(agent);
    this.isNew.set(false);
    this.editing.set(true);
    this._loadVersions(agent.agent_id);
  }

  cancelEdit(): void {
    this.editing.set(false);
    this.isNew.set(false);
    this.versions.set([]);
  }

  save(): void {
    if (this.form.invalid) return;
    this.saving.set(true);

    const val = this.form.value;
    val.skills = val.skills || [];

    const req = this.isNew()
      ? this.http.post<AgentDefinition>(this.API, val)
      : this.http.put<AgentDefinition>(`${this.API}/${val.agent_id}`, val);

    req.subscribe({
      next: () => {
        this.snackBar.open('Agente guardado', 'Cerrar', { duration: 3000 });
        this.saving.set(false);
        this.cancelEdit();
        this.loadAgents();
      },
      error: (err) => {
        const msg = err.error?.detail || 'Error guardando agente';
        this.snackBar.open(msg, 'Cerrar', { duration: 4000 });
        this.saving.set(false);
      },
    });
  }

  deleteAgent(agent: AgentDefinition): void {
    if (!confirm(`¿Eliminar el agente "${agent.name}"?`)) return;
    this.http.delete(`${this.API}/${agent.agent_id}`).subscribe({
      next: () => {
        this.snackBar.open('Agente eliminado', 'Cerrar', { duration: 3000 });
        this.loadAgents();
      },
      error: () => this.snackBar.open('Error eliminando agente', 'Cerrar', { duration: 3000 }),
    });
  }

  restoreVersion(versionNumber: number): void {
    const agentId = this.form.get('agent_id')?.value;
    if (!agentId || !confirm(`¿Restaurar version ${versionNumber}?`)) return;

    this.http.post<any>(`${this.API}/${agentId}/restore/${versionNumber}`, {}).subscribe({
      next: (res) => {
        this.snackBar.open(`Version ${versionNumber} restaurada`, 'Cerrar', { duration: 3000 });
        this.loadAgents();
        if (res.definition) {
          this.startEdit(res.definition);
        }
      },
      error: () => this.snackBar.open('Error restaurando version', 'Cerrar', { duration: 3000 }),
    });
  }

  addSkill(): void {
    this.skillsArray.push(this.fb.group({
      id: ['', Validators.required],
      name: ['', Validators.required],
      description: [''],
      content: [''],
    }));
  }

  removeSkill(index: number): void {
    this.skillsArray.removeAt(index);
  }

  private _loadVersions(agentId: string): void {
    this.loadingVersions.set(true);
    this.http.get<{ versions: AgentVersion[] }>(`${this.API}/${agentId}/versions`).subscribe({
      next: (res) => { this.versions.set(res.versions); this.loadingVersions.set(false); },
      error: () => this.loadingVersions.set(false),
    });
  }

  private _buildForm(agent?: AgentDefinition): FormGroup {
    const skillsArray = this.fb.array(
      (agent?.skills || []).map(s => this.fb.group({
        id: [s.id, Validators.required],
        name: [s.name, Validators.required],
        description: [s.description || ''],
        content: [s.content || ''],
      }))
    );

    return this.fb.group({
      agent_id: [agent?.agent_id || '', Validators.required],
      name: [agent?.name || '', Validators.required],
      description: [agent?.description || ''],
      role: [agent?.role || ''],
      expertise: [agent?.expertise || ''],
      task_requirements: [agent?.task_requirements || ''],
      system_prompt: [agent?.system_prompt || '', Validators.required],
      domain_tools: [agent?.domain_tools || []],
      core_tools_enabled: [agent?.core_tools_enabled ?? true],
      skills: skillsArray,
      is_enabled: [agent?.is_enabled ?? true],
      version: [agent?.version || '1.0.0'],
      icon: [agent?.icon || ''],
      settings: [agent?.settings || {}],
    });
  }
}
