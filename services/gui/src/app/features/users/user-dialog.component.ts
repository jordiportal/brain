import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { UserService } from '../../core/services/user.service';
import { BrainUser } from '../../core/models';

interface DialogData {
  mode: 'create' | 'edit';
  user?: BrainUser;
}

@Component({
  selector: 'app-user-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatSnackBarModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ data.mode === 'create' ? 'Nuevo Usuario' : 'Editar Usuario' }}</h2>
    <mat-dialog-content>
      <div class="form-grid">
        <mat-form-field appearance="outline">
          <mat-label>Email</mat-label>
          <input matInput [(ngModel)]="form.email" type="email" required>
        </mat-form-field>

        @if (data.mode === 'create') {
          <mat-form-field appearance="outline">
            <mat-label>Contraseña</mat-label>
            <input matInput [(ngModel)]="form.password" type="password" required>
          </mat-form-field>
        }

        <mat-form-field appearance="outline">
          <mat-label>Nombre</mat-label>
          <input matInput [(ngModel)]="form.firstname">
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Apellidos</mat-label>
          <input matInput [(ngModel)]="form.lastname">
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Rol</mat-label>
          <mat-select [(ngModel)]="form.role">
            <mat-option value="admin">Admin</mat-option>
            <mat-option value="user">User</mat-option>
            <mat-option value="viewer">Viewer</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-slide-toggle [(ngModel)]="form.is_active" color="primary">
          Activo
        </mat-slide-toggle>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancelar</button>
      <button mat-raised-button color="primary" (click)="save()" [disabled]="saving">
        {{ saving ? 'Guardando...' : 'Guardar' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .form-grid {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 400px;
    }
    mat-form-field {
      width: 100%;
    }
  `]
})
export class UserDialogComponent {
  form = {
    email: '',
    password: '',
    firstname: '',
    lastname: '',
    role: 'user',
    is_active: true
  };
  saving = false;

  constructor(
    public dialogRef: MatDialogRef<UserDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData,
    private userService: UserService,
    private snackBar: MatSnackBar,
  ) {
    if (data.mode === 'edit' && data.user) {
      this.form.email = data.user.email;
      this.form.firstname = data.user.firstname || '';
      this.form.lastname = data.user.lastname || '';
      this.form.role = data.user.role;
      this.form.is_active = data.user.is_active;
    }
  }

  save() {
    if (!this.form.email) {
      this.snackBar.open('El email es obligatorio', 'OK', { duration: 2000 });
      return;
    }

    this.saving = true;

    if (this.data.mode === 'create') {
      if (!this.form.password) {
        this.snackBar.open('La contraseña es obligatoria', 'OK', { duration: 2000 });
        this.saving = false;
        return;
      }
      this.userService.createUser({
        email: this.form.email,
        password: this.form.password,
        firstname: this.form.firstname || undefined,
        lastname: this.form.lastname || undefined,
        role: this.form.role,
        is_active: this.form.is_active,
      }).subscribe({
        next: () => {
          this.snackBar.open('Usuario creado', 'OK', { duration: 2000 });
          this.dialogRef.close(true);
        },
        error: (err) => {
          this.snackBar.open(err.error?.detail || 'Error creando usuario', 'Cerrar', { duration: 3000 });
          this.saving = false;
        }
      });
    } else {
      this.userService.updateUser(this.data.user!.id, {
        email: this.form.email,
        firstname: this.form.firstname || undefined,
        lastname: this.form.lastname || undefined,
        role: this.form.role,
        is_active: this.form.is_active,
      }).subscribe({
        next: () => {
          this.snackBar.open('Usuario actualizado', 'OK', { duration: 2000 });
          this.dialogRef.close(true);
        },
        error: (err) => {
          this.snackBar.open(err.error?.detail || 'Error actualizando usuario', 'Cerrar', { duration: 3000 });
          this.saving = false;
        }
      });
    }
  }
}
