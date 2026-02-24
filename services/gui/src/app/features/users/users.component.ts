import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { UserService } from '../../core/services/user.service';
import { BrainUser } from '../../core/models';
import { UserDialogComponent } from './user-dialog.component';
import { PasswordDialogComponent } from './password-dialog.component';
import { RolesTabComponent } from './roles-tab.component';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatChipsModule,
    MatSnackBarModule,
    MatCardModule,
    MatProgressBarModule,
    MatSlideToggleModule,
    MatTabsModule,
    MatTooltipModule,
    MatMenuModule,
    MatBadgeModule,
    MatDividerModule,
    RolesTabComponent,
  ],
  template: `
    <div class="users-container">
      <div class="page-header">
        <h1>Gestión de Usuarios</h1>
        <p class="subtitle">Administra usuarios, roles y permisos del sistema</p>
      </div>

      @if (loading()) {
        <mat-progress-bar mode="indeterminate"></mat-progress-bar>
      }

      <!-- Stats Cards -->
      <div class="stats-row">
        @for (stat of roleStats(); track stat.role) {
          <mat-card class="stat-card">
            <mat-card-content>
              <div class="stat-value">{{ stat.count }}</div>
              <div class="stat-label">{{ stat.role | titlecase }}</div>
            </mat-card-content>
          </mat-card>
        }
        <mat-card class="stat-card total">
          <mat-card-content>
            <div class="stat-value">{{ totalUsers() }}</div>
            <div class="stat-label">Total</div>
          </mat-card-content>
        </mat-card>
      </div>

      <mat-tab-group>
        <!-- Users Tab -->
        <mat-tab label="Usuarios">
          <div class="tab-content">
            <div class="actions-bar">
              <mat-slide-toggle
                [(ngModel)]="showInactive"
                (change)="loadUsers()"
                color="primary">
                Mostrar inactivos
              </mat-slide-toggle>
              <button mat-raised-button color="primary" (click)="openCreateDialog()">
                <mat-icon>person_add</mat-icon>
                Nuevo Usuario
              </button>
            </div>

            <table mat-table [dataSource]="users()" class="users-table">
              <ng-container matColumnDef="id">
                <th mat-header-cell *matHeaderCellDef>ID</th>
                <td mat-cell *matCellDef="let u">{{ u.id }}</td>
              </ng-container>

              <ng-container matColumnDef="email">
                <th mat-header-cell *matHeaderCellDef>Email</th>
                <td mat-cell *matCellDef="let u">
                  <div class="user-email-cell">
                    <mat-icon class="user-avatar">account_circle</mat-icon>
                    <div>
                      <div class="user-name">{{ u.firstname || '' }} {{ u.lastname || '' }}</div>
                      <div class="user-email">{{ u.email }}</div>
                    </div>
                  </div>
                </td>
              </ng-container>

              <ng-container matColumnDef="role">
                <th mat-header-cell *matHeaderCellDef>Rol</th>
                <td mat-cell *matCellDef="let u">
                  <span class="role-chip" [class]="'role-' + u.role">
                    {{ u.role | titlecase }}
                  </span>
                </td>
              </ng-container>

              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Estado</th>
                <td mat-cell *matCellDef="let u">
                  <span class="status-chip" [class.active]="u.is_active" [class.inactive]="!u.is_active">
                    {{ u.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
              </ng-container>

              <ng-container matColumnDef="lastLogin">
                <th mat-header-cell *matHeaderCellDef>Último acceso</th>
                <td mat-cell *matCellDef="let u">
                  {{ u.last_login_at ? (u.last_login_at | date: 'short') : 'Nunca' }}
                </td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Acciones</th>
                <td mat-cell *matCellDef="let u">
                  <button mat-icon-button [matMenuTriggerFor]="actionMenu" matTooltip="Acciones">
                    <mat-icon>more_vert</mat-icon>
                  </button>
                  <mat-menu #actionMenu="matMenu">
                    <button mat-menu-item (click)="openEditDialog(u)">
                      <mat-icon>edit</mat-icon> Editar
                    </button>
                    <button mat-menu-item (click)="openPasswordDialog(u)">
                      <mat-icon>lock_reset</mat-icon> Cambiar contraseña
                    </button>
                    <button mat-menu-item (click)="toggleActive(u)">
                      <mat-icon>{{ u.is_active ? 'block' : 'check_circle' }}</mat-icon>
                      {{ u.is_active ? 'Desactivar' : 'Activar' }}
                    </button>
                    <mat-divider></mat-divider>
                    <button mat-menu-item class="delete-action" (click)="deleteUser(u)">
                      <mat-icon color="warn">delete</mat-icon> Eliminar
                    </button>
                  </mat-menu>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
            </table>
          </div>
        </mat-tab>

        <!-- Roles Tab -->
        <mat-tab label="Roles y Permisos">
          <app-roles-tab></app-roles-tab>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .users-container {
      padding: 24px;
      max-width: 1400px;
      margin: 0 auto;
    }
    .page-header h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 500;
    }
    .subtitle {
      color: rgba(255,255,255,0.5);
      margin: 4px 0 20px;
    }
    .stats-row {
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }
    .stat-card {
      flex: 1;
      min-width: 120px;
      background: #1e1e2e !important;
      text-align: center;
    }
    .stat-card.total {
      background: #2d2d44 !important;
    }
    .stat-value {
      font-size: 32px;
      font-weight: 700;
      color: #7c4dff;
    }
    .stat-label {
      color: rgba(255,255,255,0.6);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .tab-content {
      padding: 20px 0;
    }
    .actions-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .users-table {
      width: 100%;
      background: transparent !important;
    }
    .user-email-cell {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .user-avatar {
      font-size: 36px;
      width: 36px;
      height: 36px;
      color: rgba(255,255,255,0.3);
    }
    .user-name {
      font-weight: 500;
    }
    .user-email {
      font-size: 12px;
      color: rgba(255,255,255,0.5);
    }
    .role-chip {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .role-admin {
      background: rgba(124, 77, 255, 0.2);
      color: #b388ff;
    }
    .role-user {
      background: rgba(0, 200, 83, 0.15);
      color: #69f0ae;
    }
    .role-viewer {
      background: rgba(255, 171, 0, 0.15);
      color: #ffd740;
    }
    .status-chip {
      padding: 3px 10px;
      border-radius: 10px;
      font-size: 12px;
    }
    .status-chip.active {
      background: rgba(0, 200, 83, 0.15);
      color: #69f0ae;
    }
    .status-chip.inactive {
      background: rgba(255, 82, 82, 0.15);
      color: #ff5252;
    }
    .delete-action {
      color: #ff5252 !important;
    }
    ::ng-deep .mat-mdc-tab-body-wrapper {
      padding-top: 8px;
    }
  `]
})
export class UsersComponent implements OnInit {
  users = signal<BrainUser[]>([]);
  loading = signal(false);
  showInactive = false;
  displayedColumns = ['id', 'email', 'role', 'status', 'lastLogin', 'actions'];

  roleStats = signal<{ role: string; count: number }[]>([]);
  totalUsers = computed(() => this.users().length);

  constructor(
    private userService: UserService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.loading.set(true);
    this.userService.listUsers(this.showInactive).subscribe({
      next: (res) => {
        this.users.set(res.users);
        const stats = Object.entries(res.stats).map(([role, count]) => ({ role, count }));
        this.roleStats.set(stats);
        this.loading.set(false);
      },
      error: () => {
        this.snackBar.open('Error cargando usuarios', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  openCreateDialog() {
    const ref = this.dialog.open(UserDialogComponent, {
      width: '500px',
      data: { mode: 'create' }
    });
    ref.afterClosed().subscribe(result => {
      if (result) this.loadUsers();
    });
  }

  openEditDialog(user: BrainUser) {
    const ref = this.dialog.open(UserDialogComponent, {
      width: '500px',
      data: { mode: 'edit', user }
    });
    ref.afterClosed().subscribe(result => {
      if (result) this.loadUsers();
    });
  }

  openPasswordDialog(user: BrainUser) {
    this.dialog.open(PasswordDialogComponent, {
      width: '400px',
      data: { user }
    });
  }

  toggleActive(user: BrainUser) {
    this.userService.updateUser(user.id, { is_active: !user.is_active }).subscribe({
      next: () => {
        this.snackBar.open(
          user.is_active ? 'Usuario desactivado' : 'Usuario activado',
          'OK', { duration: 2000 }
        );
        this.loadUsers();
      },
      error: () => this.snackBar.open('Error actualizando usuario', 'Cerrar', { duration: 3000 })
    });
  }

  deleteUser(user: BrainUser) {
    if (!confirm(`¿Eliminar al usuario ${user.email}? Esta acción no se puede deshacer.`)) return;
    this.userService.deleteUser(user.id).subscribe({
      next: () => {
        this.snackBar.open('Usuario eliminado', 'OK', { duration: 2000 });
        this.loadUsers();
      },
      error: (err) => this.snackBar.open(err.error?.detail || 'Error eliminando', 'Cerrar', { duration: 3000 })
    });
  }
}
