import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface UserInfo {
  id: number;
  email: string;
  firstname: string;
  lastname: string;
  role: string;
  is_active: boolean;
}

interface Sandbox {
  user_id: string;
  container_name: string;
  status: string;
  last_accessed_at: string;
  created_at: string;
  user_info?: UserInfo;
}

interface SandboxResponse {
  sandboxes: Sandbox[];
  users_without_sandbox: UserInfo[];
}

@Component({
  selector: 'app-sandboxes',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatTooltipModule,
    MatTabsModule,
    MatMenuModule,
    MatDividerModule,
  ],
  template: `
    <div class="admin-page">
      <div class="page-header">
        <div class="header-title">
          <mat-icon>dns</mat-icon>
          <div>
            <h1>Sandboxes de Usuario</h1>
            <p class="subtitle">Contenedores Docker aislados por usuario para ejecución de código y tareas</p>
          </div>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="load()" [disabled]="loading()">
            <mat-icon>refresh</mat-icon> Actualizar
          </button>
        </div>
      </div>

      @if (loading()) {
        <mat-progress-bar mode="indeterminate"></mat-progress-bar>
      }

      <!-- Stats -->
      <div class="stats-row">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-value stat-value-purple">{{ sandboxes().length }}</div>
            <div class="stat-label">Total Sandboxes</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-value stat-value-success">{{ runningCount() }}</div>
            <div class="stat-label">Activos</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-value stat-value-danger">{{ stoppedCount() }}</div>
            <div class="stat-label">Parados</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-value stat-value-warning">{{ usersWithout().length }}</div>
            <div class="stat-label">Sin Sandbox</div>
          </mat-card-content>
        </mat-card>
      </div>

      <mat-tab-group>
        <!-- Sandboxes activos -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>dns</mat-icon>&nbsp; Sandboxes ({{ sandboxes().length }})
          </ng-template>
          <div class="tab-content">
            @if (!loading() && sandboxes().length === 0) {
              <div class="empty-state">
                <mat-icon>dns</mat-icon>
                <h3>Sin sandboxes</h3>
                <p>Los sandboxes se crean automaticamente al ejecutar codigo o puedes asignarlos desde la pestana "Usuarios sin Sandbox".</p>
              </div>
            }

            @if (sandboxes().length > 0) {
              <table mat-table [dataSource]="sandboxes()" class="data-table">
                <ng-container matColumnDef="user">
                  <th mat-header-cell *matHeaderCellDef>Usuario</th>
                  <td mat-cell *matCellDef="let s">
                    <div class="user-cell">
                      <mat-icon class="user-icon">account_circle</mat-icon>
                      <div>
                        <div class="user-name">
                          {{ s.user_info ? (s.user_info.firstname || '') + ' ' + (s.user_info.lastname || '') : '' }}
                        </div>
                        <div class="user-email">{{ s.user_id }}</div>
                      </div>
                      @if (s.user_info) {
                        <span class="role-chip" [class]="'role-' + s.user_info.role">
                          {{ s.user_info.role }}
                        </span>
                      } @else {
                        <span class="role-chip role-external">externo</span>
                      }
                    </div>
                  </td>
                </ng-container>

                <ng-container matColumnDef="container">
                  <th mat-header-cell *matHeaderCellDef>Contenedor</th>
                  <td mat-cell *matCellDef="let s">
                    <code>{{ s.container_name }}</code>
                  </td>
                </ng-container>

                <ng-container matColumnDef="status">
                  <th mat-header-cell *matHeaderCellDef>Estado</th>
                  <td mat-cell *matCellDef="let s">
                    <span class="status-badge" [class]="'status-' + s.status">
                      <span class="status-dot"></span>
                      {{ s.status }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="lastAccess">
                  <th mat-header-cell *matHeaderCellDef>Ultimo acceso</th>
                  <td mat-cell *matCellDef="let s">{{ fmtDate(s.last_accessed_at) }}</td>
                </ng-container>

                <ng-container matColumnDef="created">
                  <th mat-header-cell *matHeaderCellDef>Creado</th>
                  <td mat-cell *matCellDef="let s">{{ fmtDate(s.created_at) }}</td>
                </ng-container>

                <ng-container matColumnDef="actions">
                  <th mat-header-cell *matHeaderCellDef></th>
                  <td mat-cell *matCellDef="let s">
                    <button mat-icon-button color="warn"
                            matTooltip="Eliminar sandbox"
                            (click)="removeSandbox(s)">
                      <mat-icon>delete</mat-icon>
                    </button>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="sandboxCols"></tr>
                <tr mat-row *matRowDef="let row; columns: sandboxCols;"></tr>
              </table>
            }
          </div>
        </mat-tab>

        <!-- Usuarios sin sandbox -->
        <mat-tab>
          <ng-template mat-tab-label>
            <mat-icon>person_off</mat-icon>&nbsp; Sin Sandbox ({{ usersWithout().length }})
          </ng-template>
          <div class="tab-content">
            @if (usersWithout().length === 0) {
              <div class="empty-state">
                <mat-icon>check_circle</mat-icon>
                <h3>Todos los usuarios tienen sandbox</h3>
              </div>
            }

            @if (usersWithout().length > 0) {
              <table mat-table [dataSource]="usersWithout()" class="data-table">
                <ng-container matColumnDef="user">
                  <th mat-header-cell *matHeaderCellDef>Usuario</th>
                  <td mat-cell *matCellDef="let u">
                    <div class="user-cell">
                      <mat-icon class="user-icon">account_circle</mat-icon>
                      <div>
                        <div class="user-name">{{ u.firstname || '' }} {{ u.lastname || '' }}</div>
                        <div class="user-email">{{ u.email }}</div>
                      </div>
                      <span class="role-chip" [class]="'role-' + u.role">{{ u.role }}</span>
                    </div>
                  </td>
                </ng-container>

                <ng-container matColumnDef="role">
                  <th mat-header-cell *matHeaderCellDef>Rol</th>
                  <td mat-cell *matCellDef="let u">
                    <span class="role-chip" [class]="'role-' + u.role">{{ u.role }}</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="status">
                  <th mat-header-cell *matHeaderCellDef>Estado</th>
                  <td mat-cell *matCellDef="let u">
                    <span class="status-badge" [class]="u.is_active ? 'status-running' : 'status-stopped'">
                      <span class="status-dot"></span>
                      {{ u.is_active ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="actions">
                  <th mat-header-cell *matHeaderCellDef></th>
                  <td mat-cell *matCellDef="let u">
                    <button mat-raised-button color="primary"
                            (click)="createSandbox(u)"
                            [disabled]="creatingFor === u.email">
                      <mat-icon>add_circle</mat-icon>
                      {{ creatingFor === u.email ? 'Creando...' : 'Crear Sandbox' }}
                    </button>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="usersCols"></tr>
                <tr mat-row *matRowDef="let row; columns: usersCols;"></tr>
              </table>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .role-chip { margin-left: 8px; }
  `],
})
export class SandboxesComponent implements OnInit {
  private api = environment.apiUrl;

  sandboxes = signal<Sandbox[]>([]);
  usersWithout = signal<UserInfo[]>([]);
  loading = signal(false);
  creatingFor: string | null = null;

  sandboxCols = ['user', 'container', 'status', 'lastAccess', 'created', 'actions'];
  usersCols = ['user', 'status', 'actions'];

  runningCount = computed(() => this.sandboxes().filter(s => s.status === 'running').length);
  stoppedCount = computed(() => this.sandboxes().filter(s => s.status !== 'running').length);

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.http.get<SandboxResponse>(`${this.api}/workspace/sandboxes`).subscribe({
      next: (res) => {
        this.sandboxes.set(res.sandboxes);
        this.usersWithout.set(res.users_without_sandbox);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snackBar.open('Error cargando sandboxes', 'OK', { duration: 3000 });
      },
    });
  }

  createSandbox(user: UserInfo): void {
    this.creatingFor = user.email;
    this.http.post(`${this.api}/workspace/sandboxes/${encodeURIComponent(user.email)}`, {}).subscribe({
      next: () => {
        this.snackBar.open(`Sandbox creado para ${user.email}`, 'OK', { duration: 3000 });
        this.creatingFor = null;
        this.load();
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Error creando sandbox', 'OK', { duration: 3000 });
        this.creatingFor = null;
      },
    });
  }

  removeSandbox(sandbox: Sandbox): void {
    const name = sandbox.user_info
      ? `${sandbox.user_info.firstname || ''} ${sandbox.user_info.lastname || ''} (${sandbox.user_id})`.trim()
      : sandbox.user_id;
    if (!confirm(`¿Eliminar el sandbox de ${name}? Se perderan los datos del contenedor.`)) return;

    this.http.delete(`${this.api}/workspace/sandboxes/${encodeURIComponent(sandbox.user_id)}`).subscribe({
      next: () => {
        this.snackBar.open('Sandbox eliminado', 'OK', { duration: 3000 });
        this.load();
      },
      error: () => {
        this.snackBar.open('Error eliminando sandbox', 'OK', { duration: 3000 });
      },
    });
  }

  fmtDate(iso: string): string {
    if (!iso) return '-';
    return new Date(iso).toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}
