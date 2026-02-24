import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { UserService, RolesListResponse } from '../../core/services/user.service';
import { RolePermission } from '../../core/models';

@Component({
  selector: 'app-roles-tab',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatCardModule,
    MatProgressBarModule,
  ],
  template: `
    <div class="roles-container">
      @if (loading()) {
        <mat-progress-bar mode="indeterminate"></mat-progress-bar>
      }

      <mat-accordion>
        @for (role of roles(); track role.name) {
          <mat-expansion-panel>
            <mat-expansion-panel-header>
              <mat-panel-title>
                <span class="role-chip" [class]="'role-' + role.name">
                  {{ role.name | titlecase }}
                </span>
              </mat-panel-title>
              <mat-panel-description>
                {{ role.user_count }} usuarios &middot; {{ role.permissions.length }} permisos
              </mat-panel-description>
            </mat-expansion-panel-header>

            <table mat-table [dataSource]="role.permissions" class="permissions-table">
              <ng-container matColumnDef="resource">
                <th mat-header-cell *matHeaderCellDef>Recurso</th>
                <td mat-cell *matCellDef="let p">{{ p.resource }}</td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef>Acciones</th>
                <td mat-cell *matCellDef="let p">
                  @for (a of p.actions; track a) {
                    <span class="action-chip">{{ a }}</span>
                  }
                </td>
              </ng-container>

              <ng-container matColumnDef="ops">
                <th mat-header-cell *matHeaderCellDef></th>
                <td mat-cell *matCellDef="let p">
                  <button mat-icon-button color="warn" (click)="deletePermission(role.name, p)"
                          [disabled]="role.name === 'admin' && p.resource === '*'">
                    <mat-icon>delete</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="['resource', 'actions', 'ops']"></tr>
              <tr mat-row *matRowDef="let row; columns: ['resource', 'actions', 'ops'];"></tr>
            </table>

            <!-- Add permission form -->
            <div class="add-permission">
              <mat-form-field appearance="outline" class="resource-field">
                <mat-label>Recurso</mat-label>
                <input matInput [(ngModel)]="newResource">
              </mat-form-field>

              <mat-form-field appearance="outline" class="actions-field">
                <mat-label>Acciones</mat-label>
                <mat-select [(ngModel)]="newActions" multiple>
                  <mat-option value="read">read</mat-option>
                  <mat-option value="write">write</mat-option>
                  <mat-option value="delete">delete</mat-option>
                  <mat-option value="admin">admin</mat-option>
                </mat-select>
              </mat-form-field>

              <button mat-raised-button color="primary"
                      (click)="addPermission(role.name)"
                      [disabled]="!newResource || newActions.length === 0">
                <mat-icon>add</mat-icon> Añadir
              </button>
            </div>
          </mat-expansion-panel>
        }
      </mat-accordion>
    </div>
  `,
  styles: [`
    .roles-container {
      padding: 20px 0;
    }
    .permissions-table {
      width: 100%;
      background: transparent !important;
    }
    .role-chip {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
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
    .action-chip {
      background: rgba(255,255,255,0.08);
      padding: 2px 8px;
      border-radius: 8px;
      font-size: 11px;
      margin-right: 4px;
    }
    .add-permission {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-top: 16px;
      padding: 16px 0;
      border-top: 1px solid rgba(255,255,255,0.1);
    }
    .resource-field {
      flex: 1;
    }
    .actions-field {
      flex: 1;
    }
  `]
})
export class RolesTabComponent implements OnInit {
  roles = signal<RolesListResponse['roles']>([]);
  loading = signal(false);
  newResource = '';
  newActions: string[] = [];

  constructor(
    private userService: UserService,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit() {
    this.loadRoles();
  }

  loadRoles() {
    this.loading.set(true);
    this.userService.listRoles().subscribe({
      next: (res) => {
        this.roles.set(res.roles);
        this.loading.set(false);
      },
      error: () => {
        this.snackBar.open('Error cargando roles', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  addPermission(role: string) {
    this.userService.updateRolePermission(role, this.newResource, this.newActions).subscribe({
      next: () => {
        this.snackBar.open('Permiso añadido', 'OK', { duration: 2000 });
        this.newResource = '';
        this.newActions = [];
        this.loadRoles();
      },
      error: () => this.snackBar.open('Error añadiendo permiso', 'Cerrar', { duration: 3000 })
    });
  }

  deletePermission(role: string, perm: RolePermission) {
    this.userService.deleteRolePermission(role, perm.id).subscribe({
      next: () => {
        this.snackBar.open('Permiso eliminado', 'OK', { duration: 2000 });
        this.loadRoles();
      },
      error: () => this.snackBar.open('Error eliminando permiso', 'Cerrar', { duration: 3000 })
    });
  }
}
