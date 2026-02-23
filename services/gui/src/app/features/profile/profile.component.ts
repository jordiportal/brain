import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTabsModule } from '@angular/material/tabs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { ProfileService, UserProfile, UserTask, UserPreferences, WorkspaceFile } from '../../core/services/profile.service';

const DEFAULT_USER_ID = 'jordip@khlloreda.com';

@Component({
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatTabsModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatSlideToggleModule, MatChipsModule, MatIconModule,
    MatCardModule, MatSnackBarModule, MatProgressSpinnerModule,
    MatTooltipModule, MatDividerModule,
  ],
  selector: 'app-profile',
  template: `
    <div style="padding: 24px; max-width: 900px; margin: auto;">
      <h2 style="margin-bottom: 16px;">Mi Perfil</h2>

      <mat-tab-group>
        <!-- TAB: Mi Asistente -->
        <mat-tab label="Mi Asistente">
          <div style="padding: 16px 0;">
            @if (loading()) {
              <mat-spinner diameter="32"></mat-spinner>
            } @else {
              <mat-form-field appearance="outline" style="width: 100%;">
                <mat-label>Instrucciones personales para el LLM</mat-label>
                <textarea matInput
                  [ngModel]="personalPrompt()"
                  (ngModelChange)="personalPrompt.set($event)"
                  rows="5"
                  placeholder="Ej: Tutéame, responde en catalán, soy director de IT..."></textarea>
                <mat-hint>Se inyecta como instrucción adicional en cada conversación</mat-hint>
              </mat-form-field>

              <mat-form-field appearance="outline" style="margin-top: 16px;">
                <mat-label>Zona horaria</mat-label>
                <mat-select [ngModel]="timezone()" (ngModelChange)="timezone.set($event)">
                  @for (tz of timezones; track tz) {
                    <mat-option [value]="tz">{{ tz }}</mat-option>
                  }
                </mat-select>
              </mat-form-field>

              <h3 style="margin-top: 24px;">Remitentes importantes</h3>
              <mat-chip-set>
                @for (s of importantSenders(); track s; let i = $index) {
                  <mat-chip (removed)="removeSender(i)">
                    {{ s }}
                    <button matChipRemove><mat-icon>cancel</mat-icon></button>
                  </mat-chip>
                }
              </mat-chip-set>
              <mat-form-field appearance="outline" style="margin-top: 8px;">
                <mat-label>Añadir remitente</mat-label>
                <input matInput
                  [ngModel]="newSender()"
                  (ngModelChange)="newSender.set($event)"
                  (keydown.enter)="$event.preventDefault(); addSender()"
                  placeholder="email@ejemplo.com" />
              </mat-form-field>

              <h3 style="margin-top: 16px;">Palabras clave de proyectos</h3>
              <mat-chip-set>
                @for (k of projectKeywords(); track k; let i = $index) {
                  <mat-chip (removed)="removeKeyword(i)">
                    {{ k }}
                    <button matChipRemove><mat-icon>cancel</mat-icon></button>
                  </mat-chip>
                }
              </mat-chip-set>
              <mat-form-field appearance="outline" style="margin-top: 8px;">
                <mat-label>Añadir palabra clave</mat-label>
                <input matInput
                  [ngModel]="newKeyword()"
                  (ngModelChange)="newKeyword.set($event)"
                  (keydown.enter)="$event.preventDefault(); addKeyword()"
                  placeholder="proyecto-x" />
              </mat-form-field>

              <div style="margin-top: 24px;">
                <button mat-raised-button color="primary" (click)="saveProfile()" [disabled]="saving()">
                  {{ saving() ? 'Guardando...' : 'Guardar perfil' }}
                </button>
              </div>
            }
          </div>
        </mat-tab>

        <!-- TAB: Tareas Programadas -->
        <mat-tab label="Tareas Programadas">
          <div style="padding: 16px 0;">
            <p style="color: #666;">Gestiona resúmenes de correo, agenda y otras tareas programadas.</p>

            @for (task of tasks(); track task.id) {
              <mat-card style="margin-bottom: 12px;">
                <mat-card-header>
                  <mat-card-title>{{ task.name }}</mat-card-title>
                  <mat-card-subtitle>{{ task.type }} · {{ cronLabel(task.cron_expression) }}</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <mat-slide-toggle [checked]="task.is_active" (change)="toggleTask(task)">Activa</mat-slide-toggle>
                  @if (task.last_run_at) {
                    <p style="font-size: 0.85rem; color: #888; margin-top: 8px;">
                      Última ejecución: {{ task.last_run_at | date:'short' }} — {{ task.last_status }}
                    </p>
                  }
                </mat-card-content>
                <mat-card-actions>
                  <button mat-button (click)="runNow(task)">Ejecutar ahora</button>
                  <button mat-button color="warn" (click)="deleteTask(task)">Eliminar</button>
                </mat-card-actions>
              </mat-card>
            }

            @if (tasks().length === 0) {
              <p>No hay tareas programadas.</p>
            }
          </div>
        </mat-tab>

        <!-- TAB: Sandbox -->
        <mat-tab label="Sandbox">
          <div style="padding: 16px 0;">
            <!-- Breadcrumb -->
            <div class="sandbox-breadcrumb">
              <button mat-button (click)="navigateTo('')" [disabled]="currentPath() === ''">
                <mat-icon>home</mat-icon> workspace
              </button>
              @for (crumb of breadcrumbs(); track crumb.path) {
                <mat-icon style="vertical-align: middle; color: #999;">chevron_right</mat-icon>
                <button mat-button (click)="navigateTo(crumb.path)">{{ crumb.name }}</button>
              }
            </div>

            @if (wsLoading()) {
              <mat-spinner diameter="28" style="margin: 24px auto;"></mat-spinner>
            } @else {
              <div class="sandbox-file-list">
                @if (currentPath() !== '') {
                  <div class="sandbox-file-row sandbox-dir-row" (click)="navigateUp()">
                    <mat-icon class="sandbox-file-icon" style="color: #78909c;">subdirectory_arrow_left</mat-icon>
                    <span class="sandbox-file-name">..</span>
                    <span class="sandbox-file-meta"></span>
                    <span class="sandbox-file-actions"></span>
                  </div>
                }

                @for (f of wsFiles(); track f.name) {
                  <div class="sandbox-file-row" [class.sandbox-dir-row]="f.is_directory"
                       (click)="f.is_directory ? navigateTo(joinPath(currentPath(), f.name)) : null">
                    <mat-icon class="sandbox-file-icon" [style.color]="f.is_directory ? '#ffa726' : '#90a4ae'">
                      {{ f.is_directory ? 'folder' : fileIcon(f.name) }}
                    </mat-icon>
                    <span class="sandbox-file-name">{{ f.name }}</span>
                    <span class="sandbox-file-meta">{{ f.is_directory ? '' : formatSize(f.size) }}</span>
                    <span class="sandbox-file-actions">
                      @if (!f.is_directory) {
                        <button mat-icon-button matTooltip="Descargar"
                                (click)="downloadFile(f); $event.stopPropagation()">
                          <mat-icon>download</mat-icon>
                        </button>
                        <button mat-icon-button matTooltip="Eliminar" color="warn"
                                (click)="deleteFile(f); $event.stopPropagation()">
                          <mat-icon>delete</mat-icon>
                        </button>
                      }
                    </span>
                  </div>
                }

                @if (wsFiles().length === 0 && currentPath() === '') {
                  <p style="text-align: center; color: #999; margin-top: 24px;">
                    El sandbox está vacío.
                  </p>
                }
              </div>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .sandbox-breadcrumb {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 2px;
      margin-bottom: 12px;
      padding: 8px 4px;
      background: #f5f5f5;
      border-radius: 8px;
    }
    .sandbox-file-list {
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      overflow: hidden;
    }
    .sandbox-file-row {
      display: flex;
      align-items: center;
      padding: 10px 16px;
      gap: 12px;
      border-bottom: 1px solid #f0f0f0;
      transition: background 0.15s;
    }
    .sandbox-file-row:last-child {
      border-bottom: none;
    }
    .sandbox-file-row:hover {
      background: #fafafa;
    }
    .sandbox-dir-row {
      cursor: pointer;
    }
    .sandbox-dir-row:hover {
      background: #fff3e0;
    }
    .sandbox-file-icon {
      flex-shrink: 0;
    }
    .sandbox-file-name {
      flex: 1;
      font-size: 14px;
      font-weight: 400;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sandbox-dir-row .sandbox-file-name {
      font-weight: 500;
    }
    .sandbox-file-meta {
      flex-shrink: 0;
      font-size: 12px;
      color: #999;
      min-width: 70px;
      text-align: right;
    }
    .sandbox-file-actions {
      flex-shrink: 0;
      display: flex;
      gap: 2px;
    }
  `],
})
export class ProfileComponent implements OnInit {
  userId = signal(DEFAULT_USER_ID);
  loading = signal(false);
  saving = signal(false);
  personalPrompt = signal('');
  timezone = signal('Europe/Madrid');
  importantSenders = signal<string[]>([]);
  projectKeywords = signal<string[]>([]);
  newSender = signal('');
  newKeyword = signal('');
  tasks = signal<UserTask[]>([]);
  timezones = ['Europe/Madrid', 'Europe/London', 'UTC', 'America/New_York', 'America/Los_Angeles', 'Asia/Tokyo'];

  // Sandbox explorer
  currentPath = signal('');
  wsFiles = signal<WorkspaceFile[]>([]);
  wsLoading = signal(false);
  breadcrumbs = signal<{ name: string; path: string }[]>([]);

  constructor(private profileService: ProfileService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.loadProfile();
    this.loadTasks();
    this.loadWorkspace('');
  }

  loadProfile(): void {
    this.loading.set(true);
    this.profileService.getProfile(this.userId()).subscribe({
      next: (p) => {
        this.personalPrompt.set(p.personal_prompt ?? '');
        this.timezone.set(p.timezone ?? 'Europe/Madrid');
        this.importantSenders.set(p.preferences?.importantSenders ?? []);
        this.projectKeywords.set(p.preferences?.projectKeywords ?? []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  loadTasks(): void {
    this.profileService.getTasks(this.userId()).subscribe({
      next: (r) => this.tasks.set(r.items ?? []),
      error: () => this.tasks.set([]),
    });
  }

  saveProfile(): void {
    this.saving.set(true);
    const prefs: UserPreferences = {
      importantSenders: this.importantSenders(),
      projectKeywords: this.projectKeywords(),
    };
    this.profileService.updateProfile(this.userId(), {
      personal_prompt: this.personalPrompt(),
      timezone: this.timezone(),
      preferences: prefs,
    }).subscribe({
      next: () => { this.saving.set(false); this.snack.open('Perfil guardado', 'OK', { duration: 2000 }); },
      error: () => { this.saving.set(false); this.snack.open('Error al guardar', 'OK', { duration: 3000 }); },
    });
  }

  addSender(): void {
    const v = this.newSender().trim();
    if (!v) return;
    this.importantSenders.update(s => [...s, v]);
    this.newSender.set('');
  }
  removeSender(i: number): void { this.importantSenders.update(s => s.filter((_, j) => j !== i)); }
  addKeyword(): void {
    const v = this.newKeyword().trim();
    if (!v) return;
    this.projectKeywords.update(k => [...k, v]);
    this.newKeyword.set('');
  }
  removeKeyword(i: number): void { this.projectKeywords.update(k => k.filter((_, j) => j !== i)); }

  toggleTask(task: UserTask): void {
    this.profileService.updateTask(task.id, { is_active: !task.is_active }).subscribe({
      next: () => this.loadTasks(),
    });
  }

  runNow(task: UserTask): void {
    this.profileService.runTaskNow(task.id).subscribe({
      next: () => this.snack.open('Tarea ejecutándose...', 'OK', { duration: 2000 }),
    });
  }

  deleteTask(task: UserTask): void {
    if (!confirm('¿Eliminar esta tarea?')) return;
    this.profileService.deleteTask(task.id).subscribe({ next: () => this.loadTasks() });
  }

  cronLabel(cron: string): string {
    const p = cron.trim().split(/\s+/);
    if (p.length !== 5) return cron;
    const [min, hour, , , dow] = p;
    if (min === '0' && hour === '8' && dow === '1-5') return 'L-V a las 8:00';
    if (min === '0' && hour === '9' && dow === '*') return 'Cada día a las 9:00';
    return cron;
  }

  // --- Sandbox Explorer ---

  loadWorkspace(path: string): void {
    this.wsLoading.set(true);
    this.currentPath.set(path);
    this.updateBreadcrumbs(path);
    this.profileService.listWorkspace(path).subscribe({
      next: (listing) => {
        const sorted = [...listing.files].sort((a, b) => {
          if (a.is_directory !== b.is_directory) return a.is_directory ? -1 : 1;
          return a.name.localeCompare(b.name);
        });
        this.wsFiles.set(sorted);
        this.wsLoading.set(false);
      },
      error: () => {
        this.wsFiles.set([]);
        this.wsLoading.set(false);
      },
    });
  }

  navigateTo(path: string): void {
    this.loadWorkspace(path);
  }

  navigateUp(): void {
    const parts = this.currentPath().split('/').filter(Boolean);
    parts.pop();
    this.navigateTo(parts.join('/'));
  }

  joinPath(base: string, name: string): string {
    return base ? `${base}/${name}` : name;
  }

  updateBreadcrumbs(path: string): void {
    if (!path) {
      this.breadcrumbs.set([]);
      return;
    }
    const parts = path.split('/').filter(Boolean);
    const crumbs = parts.map((name, i) => ({
      name,
      path: parts.slice(0, i + 1).join('/'),
    }));
    this.breadcrumbs.set(crumbs);
  }

  downloadFile(f: WorkspaceFile): void {
    const filePath = this.joinPath(this.currentPath(), f.name);
    const url = this.profileService.getFileUrl(filePath);
    const a = document.createElement('a');
    a.href = url;
    a.download = f.name;
    a.target = '_blank';
    a.click();
  }

  deleteFile(f: WorkspaceFile): void {
    if (!confirm(`¿Eliminar "${f.name}"?`)) return;
    const filePath = this.joinPath(this.currentPath(), f.name);
    this.profileService.deleteWorkspaceFile(filePath).subscribe({
      next: () => {
        this.snack.open('Archivo eliminado', 'OK', { duration: 2000 });
        this.loadWorkspace(this.currentPath());
      },
      error: () => this.snack.open('Error al eliminar', 'OK', { duration: 3000 }),
    });
  }

  formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
  }

  fileIcon(name: string): string {
    const ext = name.split('.').pop()?.toLowerCase() ?? '';
    const icons: Record<string, string> = {
      py: 'code', js: 'code', ts: 'code', json: 'data_object',
      csv: 'table_chart', xlsx: 'table_chart', xls: 'table_chart',
      pdf: 'picture_as_pdf',
      png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', webp: 'image', svg: 'image',
      mp4: 'movie', webm: 'movie', mov: 'movie',
      txt: 'description', md: 'description', log: 'description',
      zip: 'archive', tar: 'archive', gz: 'archive',
      sh: 'terminal', bash: 'terminal',
      html: 'language', css: 'palette', sql: 'storage',
    };
    return icons[ext] ?? 'insert_drive_file';
  }
}
