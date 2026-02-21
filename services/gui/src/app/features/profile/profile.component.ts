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
import { ProfileService, UserProfile, UserTask, UserPreferences } from '../../core/services/profile.service';

const DEFAULT_USER_ID = 'jordip@khlloreda.com';

@Component({
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatTabsModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatSlideToggleModule, MatChipsModule, MatIconModule,
    MatCardModule, MatSnackBarModule, MatProgressSpinnerModule,
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
      </mat-tab-group>
    </div>
  `,
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

  constructor(private profileService: ProfileService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.loadProfile();
    this.loadTasks();
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
}
