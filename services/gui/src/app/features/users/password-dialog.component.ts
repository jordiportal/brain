import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { UserService } from '../../core/services/user.service';
import { BrainUser } from '../../core/models';

@Component({
  selector: 'app-password-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSnackBarModule,
  ],
  template: `
    <h2 mat-dialog-title>Cambiar contraseña</h2>
    <mat-dialog-content>
      <p style="color: rgba(255,255,255,0.6); margin-bottom: 16px;">
        Usuario: <strong>{{ data.user.email }}</strong>
      </p>
      <mat-form-field appearance="outline" style="width: 100%;">
        <mat-label>Nueva contraseña</mat-label>
        <input matInput [(ngModel)]="newPassword" type="password">
      </mat-form-field>
      <mat-form-field appearance="outline" style="width: 100%;">
        <mat-label>Confirmar contraseña</mat-label>
        <input matInput [(ngModel)]="confirmPassword" type="password">
      </mat-form-field>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancelar</button>
      <button mat-raised-button color="primary" (click)="save()" [disabled]="saving">
        {{ saving ? 'Guardando...' : 'Cambiar' }}
      </button>
    </mat-dialog-actions>
  `
})
export class PasswordDialogComponent {
  newPassword = '';
  confirmPassword = '';
  saving = false;

  constructor(
    public dialogRef: MatDialogRef<PasswordDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { user: BrainUser },
    private userService: UserService,
    private snackBar: MatSnackBar,
  ) {}

  save() {
    if (!this.newPassword || this.newPassword.length < 4) {
      this.snackBar.open('La contraseña debe tener al menos 4 caracteres', 'OK', { duration: 2000 });
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      this.snackBar.open('Las contraseñas no coinciden', 'OK', { duration: 2000 });
      return;
    }

    this.saving = true;
    this.userService.changeUserPassword(this.data.user.id, this.newPassword).subscribe({
      next: () => {
        this.snackBar.open('Contraseña actualizada', 'OK', { duration: 2000 });
        this.dialogRef.close(true);
      },
      error: (err) => {
        this.snackBar.open(err.error?.detail || 'Error cambiando contraseña', 'Cerrar', { duration: 3000 });
        this.saving = false;
      }
    });
  }
}
