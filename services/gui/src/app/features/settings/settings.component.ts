import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTabsModule } from '@angular/material/tabs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTableModule } from '@angular/material/table';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { StrapiService } from '../../core/services/strapi.service';
import { LlmProvider, McpConnection } from '../../core/models';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatTableModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatChipsModule
  ],
  template: `
    <div class="settings-page">
      <h1>Configuración</h1>
      <p class="subtitle">Gestiona las conexiones y configuraciones del sistema</p>

      <mat-tab-group animationDuration="200ms">
        <!-- LLM Providers Tab -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>smart_toy</mat-icon>
            <span>Proveedores LLM</span>
          </ng-template>

          <div class="tab-content">
            <div class="section-header">
              <h2>Proveedores de LLM</h2>
              <button mat-raised-button color="primary" (click)="showLlmForm.set(true)">
                <mat-icon>add</mat-icon>
                Añadir Proveedor
              </button>
            </div>

            <!-- Form para nuevo/editar LLM Provider -->
            @if (showLlmForm()) {
              <mat-card class="form-card">
                <mat-card-header>
                  <mat-card-title>{{ editingLlm() ? 'Editar' : 'Nuevo' }} Proveedor LLM</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="llmForm" (ngSubmit)="saveLlmProvider()">
                    <div class="form-row">
                      <mat-form-field appearance="outline">
                        <mat-label>Nombre</mat-label>
                        <input matInput formControlName="name" placeholder="Mi Ollama Local">
                      </mat-form-field>

                      <mat-form-field appearance="outline">
                        <mat-label>Tipo</mat-label>
                        <mat-select formControlName="type">
                          <mat-option value="ollama">Ollama</mat-option>
                          <mat-option value="openai">OpenAI</mat-option>
                          <mat-option value="gemini">Google Gemini</mat-option>
                          <mat-option value="anthropic">Anthropic Claude</mat-option>
                          <mat-option value="azure">Azure OpenAI</mat-option>
                          <mat-option value="groq">Groq</mat-option>
                          <mat-option value="custom">Personalizado</mat-option>
                        </mat-select>
                      </mat-form-field>
                    </div>

                    <div class="form-row">
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>URL Base</mat-label>
                        <input matInput formControlName="baseUrl" placeholder="http://localhost:11434">
                        <mat-hint>URL del servidor de LLM</mat-hint>
                      </mat-form-field>
                    </div>

                    <div class="form-row">
                      <mat-form-field appearance="outline">
                        <mat-label>API Key</mat-label>
                        <input matInput formControlName="apiKey" type="password" placeholder="sk-...">
                        <mat-hint>Opcional para Ollama local</mat-hint>
                      </mat-form-field>

                      <mat-form-field appearance="outline">
                        <mat-label>Modelo por defecto</mat-label>
                        <input matInput formControlName="defaultModel" placeholder="llama3.2">
                      </mat-form-field>
                    </div>

                    <div class="form-row">
                      <mat-form-field appearance="outline">
                        <mat-label>Modelo de Embeddings</mat-label>
                        <input matInput formControlName="embeddingModel" placeholder="nomic-embed-text">
                      </mat-form-field>

                      <mat-slide-toggle formControlName="isActive" color="primary">
                        Activo
                      </mat-slide-toggle>
                    </div>

                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Descripción</mat-label>
                      <textarea matInput formControlName="description" rows="2"></textarea>
                    </mat-form-field>

                    <div class="form-actions">
                      <button mat-button type="button" (click)="cancelLlmEdit()">Cancelar</button>
                      <button mat-raised-button color="primary" type="submit" [disabled]="llmForm.invalid || savingLlm()">
                        @if (savingLlm()) {
                          <mat-spinner diameter="20"></mat-spinner>
                        } @else {
                          <mat-icon>save</mat-icon>
                          Guardar
                        }
                      </button>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            }

            <!-- Lista de LLM Providers -->
            <div class="providers-list">
              @for (provider of llmProviders(); track provider.id) {
                <mat-card class="provider-card">
                  <div class="provider-header">
                    <div class="provider-info">
                      <mat-icon class="provider-type-icon" [class]="provider.type">
                        {{ getProviderIcon(provider.type) }}
                      </mat-icon>
                      <div>
                        <h3>{{ provider.name }}</h3>
                        <p>{{ provider.baseUrl }}</p>
                      </div>
                    </div>
                    <mat-chip [class]="provider.isActive ? 'active' : 'inactive'">
                      {{ provider.isActive ? 'Activo' : 'Inactivo' }}
                    </mat-chip>
                  </div>
                  <div class="provider-details">
                    <span><strong>Tipo:</strong> {{ provider.type | uppercase }}</span>
                    <span><strong>Modelo:</strong> {{ provider.defaultModel || 'No definido' }}</span>
                  </div>
                  <div class="provider-actions">
                    <button mat-icon-button (click)="editLlmProvider(provider)" matTooltip="Editar">
                      <mat-icon>edit</mat-icon>
                    </button>
                    <button mat-icon-button color="warn" (click)="deleteLlmProvider(provider)" matTooltip="Eliminar">
                      <mat-icon>delete</mat-icon>
                    </button>
                  </div>
                </mat-card>
              } @empty {
                <div class="empty-state">
                  <mat-icon>smart_toy</mat-icon>
                  <p>No hay proveedores LLM configurados</p>
                  <button mat-stroked-button (click)="showLlmForm.set(true)">
                    Añadir el primero
                  </button>
                </div>
              }
            </div>
          </div>
        </mat-tab>

        <!-- MCP Connections Tab -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>extension</mat-icon>
            <span>Conexiones MCP</span>
          </ng-template>

          <div class="tab-content">
            <div class="section-header">
              <h2>Conexiones MCP</h2>
              <button mat-raised-button color="primary" (click)="showMcpForm.set(true)">
                <mat-icon>add</mat-icon>
                Añadir Conexión
              </button>
            </div>

            <!-- Form para nuevo/editar MCP Connection -->
            @if (showMcpForm()) {
              <mat-card class="form-card">
                <mat-card-header>
                  <mat-card-title>{{ editingMcp() ? 'Editar' : 'Nueva' }} Conexión MCP</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="mcpForm" (ngSubmit)="saveMcpConnection()">
                    <div class="form-row">
                      <mat-form-field appearance="outline">
                        <mat-label>Nombre</mat-label>
                        <input matInput formControlName="name" placeholder="GitHub MCP">
                      </mat-form-field>

                      <mat-form-field appearance="outline">
                        <mat-label>Tipo</mat-label>
                        <mat-select formControlName="type">
                          <mat-option value="stdio">STDIO</mat-option>
                          <mat-option value="sse">SSE</mat-option>
                          <mat-option value="http">HTTP</mat-option>
                        </mat-select>
                      </mat-form-field>
                    </div>

                    <div class="form-row">
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>Comando (para STDIO)</mat-label>
                        <input matInput formControlName="command" placeholder="npx">
                      </mat-form-field>
                    </div>

                    <div class="form-row">
                      <mat-form-field appearance="outline" class="full-width">
                        <mat-label>URL del Servidor (para SSE/HTTP)</mat-label>
                        <input matInput formControlName="serverUrl" placeholder="http://localhost:3000">
                      </mat-form-field>
                    </div>

                    <mat-slide-toggle formControlName="isActive" color="primary">
                      Activo
                    </mat-slide-toggle>

                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Descripción</mat-label>
                      <textarea matInput formControlName="description" rows="2"></textarea>
                    </mat-form-field>

                    <div class="form-actions">
                      <button mat-button type="button" (click)="cancelMcpEdit()">Cancelar</button>
                      <button mat-raised-button color="primary" type="submit" [disabled]="mcpForm.invalid || savingMcp()">
                        @if (savingMcp()) {
                          <mat-spinner diameter="20"></mat-spinner>
                        } @else {
                          <mat-icon>save</mat-icon>
                          Guardar
                        }
                      </button>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            }

            <!-- Lista de MCP Connections -->
            <div class="providers-list">
              @for (connection of mcpConnections(); track connection.id) {
                <mat-card class="provider-card">
                  <div class="provider-header">
                    <div class="provider-info">
                      <mat-icon class="provider-type-icon mcp">extension</mat-icon>
                      <div>
                        <h3>{{ connection.name }}</h3>
                        <p>{{ connection.type | uppercase }} - {{ connection.command || connection.serverUrl }}</p>
                      </div>
                    </div>
                    <mat-chip [class]="connection.isActive ? 'active' : 'inactive'">
                      {{ connection.isActive ? 'Activo' : 'Inactivo' }}
                    </mat-chip>
                  </div>
                  <div class="provider-actions">
                    <button mat-icon-button (click)="editMcpConnection(connection)" matTooltip="Editar">
                      <mat-icon>edit</mat-icon>
                    </button>
                    <button mat-icon-button color="warn" (click)="deleteMcpConnection(connection)" matTooltip="Eliminar">
                      <mat-icon>delete</mat-icon>
                    </button>
                  </div>
                </mat-card>
              } @empty {
                <div class="empty-state">
                  <mat-icon>extension</mat-icon>
                  <p>No hay conexiones MCP configuradas</p>
                  <button mat-stroked-button (click)="showMcpForm.set(true)">
                    Añadir la primera
                  </button>
                </div>
              }
            </div>
          </div>
        </mat-tab>

        <!-- General Settings Tab -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>tune</mat-icon>
            <span>General</span>
          </ng-template>

          <div class="tab-content">
            <h2>Configuración General</h2>
            <p class="info-text">Configuraciones adicionales del sistema se gestionarán aquí.</p>
            
            <mat-card class="info-card">
              <mat-card-content>
                <mat-icon>info</mat-icon>
                <p>Las configuraciones generales del sistema están en desarrollo.</p>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .settings-page {
      max-width: 1200px;
      margin: 0 auto;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin-top: 4px;
      margin-bottom: 24px;
    }

    h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }

    mat-tab-group {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    .tab-content {
      padding: 24px;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .form-card {
      margin-bottom: 24px;
      border: 1px solid #e0e0e0;
    }

    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .form-row mat-form-field {
      flex: 1;
    }

    .full-width {
      width: 100%;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 16px;
    }

    .providers-list {
      display: grid;
      gap: 16px;
    }

    .provider-card {
      padding: 16px;
      border-radius: 8px;
    }

    .provider-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }

    .provider-info {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .provider-type-icon {
      width: 48px;
      height: 48px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      background: #f5f5f5;
    }

    .provider-type-icon.ollama { background: #e3f2fd; color: #1976d2; }
    .provider-type-icon.openai { background: #e8f5e9; color: #388e3c; }
    .provider-type-icon.gemini { background: #fff3e0; color: #f57c00; }
    .provider-type-icon.anthropic { background: #fce4ec; color: #c2185b; }
    .provider-type-icon.mcp { background: #f3e5f5; color: #7b1fa2; }

    .provider-info h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }

    .provider-info p {
      margin: 4px 0 0;
      font-size: 13px;
      color: #666;
    }

    mat-chip.active {
      background: #e8f5e9 !important;
      color: #388e3c !important;
    }

    mat-chip.inactive {
      background: #fafafa !important;
      color: #9e9e9e !important;
    }

    .provider-details {
      display: flex;
      gap: 24px;
      font-size: 13px;
      color: #666;
      margin-bottom: 12px;
    }

    .provider-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

    .empty-state {
      text-align: center;
      padding: 48px;
      color: #666;
    }

    .empty-state mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      color: #ccc;
      margin-bottom: 16px;
    }

    .info-card {
      background: #f5f5f5;
    }

    .info-card mat-card-content {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .info-card mat-icon {
      color: #1976d2;
    }

    ::ng-deep .mat-mdc-tab .mdc-tab__text-label {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  `]
})
export class SettingsComponent implements OnInit {
  // LLM Providers
  llmProviders = signal<LlmProvider[]>([]);
  showLlmForm = signal(false);
  editingLlm = signal<LlmProvider | null>(null);
  savingLlm = signal(false);
  llmForm: FormGroup;

  // MCP Connections
  mcpConnections = signal<McpConnection[]>([]);
  showMcpForm = signal(false);
  editingMcp = signal<McpConnection | null>(null);
  savingMcp = signal(false);
  mcpForm: FormGroup;

  constructor(
    private fb: FormBuilder,
    private strapiService: StrapiService,
    private snackBar: MatSnackBar
  ) {
    this.llmForm = this.fb.group({
      name: ['', Validators.required],
      type: ['ollama', Validators.required],
      baseUrl: ['http://localhost:11434', Validators.required],
      apiKey: [''],
      defaultModel: ['llama3.2'],
      embeddingModel: ['nomic-embed-text'],
      isActive: [true],
      description: ['']
    });

    this.mcpForm = this.fb.group({
      name: ['', Validators.required],
      type: ['stdio', Validators.required],
      command: [''],
      serverUrl: [''],
      isActive: [true],
      description: ['']
    });
  }

  ngOnInit(): void {
    this.loadLlmProviders();
    this.loadMcpConnections();
  }

  // LLM Providers Methods
  loadLlmProviders(): void {
    this.strapiService.getLlmProviders().subscribe({
      next: (providers) => this.llmProviders.set(providers),
      error: (err) => this.snackBar.open('Error cargando proveedores LLM', 'Cerrar', { duration: 3000 })
    });
  }

  getProviderIcon(type: string): string {
    const icons: Record<string, string> = {
      ollama: 'memory',
      openai: 'auto_awesome',
      gemini: 'diamond',
      anthropic: 'psychology',
      azure: 'cloud',
      groq: 'bolt',
      custom: 'settings'
    };
    return icons[type] || 'smart_toy';
  }

  editLlmProvider(provider: LlmProvider): void {
    this.editingLlm.set(provider);
    this.llmForm.patchValue(provider);
    this.showLlmForm.set(true);
  }

  cancelLlmEdit(): void {
    this.showLlmForm.set(false);
    this.editingLlm.set(null);
    this.llmForm.reset({ type: 'ollama', baseUrl: 'http://localhost:11434', isActive: true });
  }

  saveLlmProvider(): void {
    if (this.llmForm.invalid) return;

    this.savingLlm.set(true);
    const data = this.llmForm.value;

    const request = this.editingLlm()
      ? this.strapiService.updateLlmProvider(this.editingLlm()!.documentId, data)
      : this.strapiService.createLlmProvider(data);

    request.subscribe({
      next: () => {
        this.snackBar.open('Proveedor guardado correctamente', 'Cerrar', { duration: 3000 });
        this.loadLlmProviders();
        this.cancelLlmEdit();
        this.savingLlm.set(false);
      },
      error: (err) => {
        this.snackBar.open('Error guardando proveedor', 'Cerrar', { duration: 3000 });
        this.savingLlm.set(false);
      }
    });
  }

  deleteLlmProvider(provider: LlmProvider): void {
    if (confirm(`¿Eliminar el proveedor "${provider.name}"?`)) {
      this.strapiService.deleteLlmProvider(provider.documentId).subscribe({
        next: () => {
          this.snackBar.open('Proveedor eliminado', 'Cerrar', { duration: 3000 });
          this.loadLlmProviders();
        },
        error: () => this.snackBar.open('Error eliminando proveedor', 'Cerrar', { duration: 3000 })
      });
    }
  }

  // MCP Connections Methods
  loadMcpConnections(): void {
    this.strapiService.getMcpConnections().subscribe({
      next: (connections) => this.mcpConnections.set(connections),
      error: (err) => this.snackBar.open('Error cargando conexiones MCP', 'Cerrar', { duration: 3000 })
    });
  }

  editMcpConnection(connection: McpConnection): void {
    this.editingMcp.set(connection);
    this.mcpForm.patchValue(connection);
    this.showMcpForm.set(true);
  }

  cancelMcpEdit(): void {
    this.showMcpForm.set(false);
    this.editingMcp.set(null);
    this.mcpForm.reset({ type: 'stdio', isActive: true });
  }

  saveMcpConnection(): void {
    if (this.mcpForm.invalid) return;

    this.savingMcp.set(true);
    const data = this.mcpForm.value;

    const request = this.editingMcp()
      ? this.strapiService.updateMcpConnection(this.editingMcp()!.documentId, data)
      : this.strapiService.createMcpConnection(data);

    request.subscribe({
      next: () => {
        this.snackBar.open('Conexión guardada correctamente', 'Cerrar', { duration: 3000 });
        this.loadMcpConnections();
        this.cancelMcpEdit();
        this.savingMcp.set(false);
      },
      error: (err) => {
        this.snackBar.open('Error guardando conexión', 'Cerrar', { duration: 3000 });
        this.savingMcp.set(false);
      }
    });
  }

  deleteMcpConnection(connection: McpConnection): void {
    if (confirm(`¿Eliminar la conexión "${connection.name}"?`)) {
      this.strapiService.deleteMcpConnection(connection.documentId).subscribe({
        next: () => {
          this.snackBar.open('Conexión eliminada', 'Cerrar', { duration: 3000 });
          this.loadMcpConnections();
        },
        error: () => this.snackBar.open('Error eliminando conexión', 'Cerrar', { duration: 3000 })
      });
    }
  }
}
