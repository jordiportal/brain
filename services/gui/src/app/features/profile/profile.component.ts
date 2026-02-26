import { Component, OnInit, signal, inject } from '@angular/core';
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
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatMenuModule } from '@angular/material/menu';
import { ProfileService, UserProfile, UserTask, UserPreferences, WorkspaceFile } from '../../core/services/profile.service';
import { ArtifactService, Artifact, ArtifactListResponse } from '../../core/services/artifact.service';
import { ArtifactViewerComponent } from '../../shared/components/artifact-viewer/artifact-viewer.component';
import { AuthService } from '../../core/services/auth.service';

@Component({
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatTabsModule, MatFormFieldModule, MatInputModule, MatSelectModule,
    MatButtonModule, MatSlideToggleModule, MatChipsModule, MatIconModule,
    MatCardModule, MatSnackBarModule, MatProgressSpinnerModule,
    MatTooltipModule, MatDividerModule, MatTableModule, MatPaginatorModule,
    MatMenuModule, ArtifactViewerComponent,
  ],
  selector: 'app-profile',
  template: `
    <div class="admin-page" style="max-width: 960px;">
      <div class="page-header">
        <div class="header-title">
          <mat-icon>person</mat-icon>
          <div>
            <h1>Mi Perfil</h1>
            <p class="subtitle">Configuración personal, tareas, artefactos y archivos del sandbox</p>
          </div>
        </div>
      </div>

      <mat-tab-group>
        <!-- TAB: Mi Asistente -->
        <mat-tab label="Mi Asistente">
          <div class="tab-content">
            @if (loading()) {
              <div class="loading-container">
                <mat-spinner diameter="32"></mat-spinner>
              </div>
            } @else {
              <mat-card class="profile-section-card">
                <mat-card-content>
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Instrucciones personales para el LLM</mat-label>
                    <textarea matInput
                      [ngModel]="personalPrompt()"
                      (ngModelChange)="personalPrompt.set($event)"
                      rows="5"
                      placeholder="Ej: Tutéame, responde en catalán, soy director de IT..."></textarea>
                    <mat-hint>Se inyecta como instrucción adicional en cada conversación</mat-hint>
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="mt-2">
                    <mat-label>Zona horaria</mat-label>
                    <mat-select [ngModel]="timezone()" (ngModelChange)="timezone.set($event)">
                      @for (tz of timezones; track tz) {
                        <mat-option [value]="tz">{{ tz }}</mat-option>
                      }
                    </mat-select>
                  </mat-form-field>
                </mat-card-content>
              </mat-card>

              <mat-card class="profile-section-card mt-3">
                <mat-card-content>
                  <h3>Remitentes importantes</h3>
                  <mat-chip-set>
                    @for (s of importantSenders(); track s; let i = $index) {
                      <mat-chip (removed)="removeSender(i)">
                        {{ s }}
                        <button matChipRemove><mat-icon>cancel</mat-icon></button>
                      </mat-chip>
                    }
                  </mat-chip-set>
                  <mat-form-field appearance="outline" class="full-width mt-1">
                    <mat-label>Añadir remitente</mat-label>
                    <input matInput
                      [ngModel]="newSender()"
                      (ngModelChange)="newSender.set($event)"
                      (keydown.enter)="$event.preventDefault(); addSender()"
                      placeholder="email@ejemplo.com" />
                  </mat-form-field>

                  <h3 class="mt-2">Palabras clave de proyectos</h3>
                  <mat-chip-set>
                    @for (k of projectKeywords(); track k; let i = $index) {
                      <mat-chip (removed)="removeKeyword(i)">
                        {{ k }}
                        <button matChipRemove><mat-icon>cancel</mat-icon></button>
                      </mat-chip>
                    }
                  </mat-chip-set>
                  <mat-form-field appearance="outline" class="full-width mt-1">
                    <mat-label>Añadir palabra clave</mat-label>
                    <input matInput
                      [ngModel]="newKeyword()"
                      (ngModelChange)="newKeyword.set($event)"
                      (keydown.enter)="$event.preventDefault(); addKeyword()"
                      placeholder="proyecto-x" />
                  </mat-form-field>
                </mat-card-content>
              </mat-card>

              <div class="mt-3">
                <button mat-raised-button color="primary" (click)="saveProfile()" [disabled]="saving()">
                  {{ saving() ? 'Guardando...' : 'Guardar perfil' }}
                </button>
              </div>
            }
          </div>
        </mat-tab>

        <!-- TAB: Tareas Programadas -->
        <mat-tab label="Tareas Programadas">
          <div class="tab-content">
            <p class="text-secondary">Gestiona resúmenes de correo, agenda y otras tareas programadas.</p>

            @for (task of tasks(); track task.id) {
              <mat-card class="task-card">
                <mat-card-header>
                  <mat-card-title>{{ task.name }}</mat-card-title>
                  <mat-card-subtitle>{{ task.type }} · {{ cronLabel(task.cron_expression) }}</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <mat-slide-toggle [checked]="task.is_active" (change)="toggleTask(task)">Activa</mat-slide-toggle>
                  @if (task.last_run_at) {
                    <p class="task-last-run">
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
              <div class="empty-state">
                <mat-icon>schedule</mat-icon>
                <h3>No hay tareas programadas</h3>
                <p>Las tareas de resumen de correo, agenda y otras tareas automáticas aparecerán aquí.</p>
              </div>
            }
          </div>
        </mat-tab>

        <!-- TAB: Artefactos -->
        <mat-tab label="Artefactos">
          <div class="tab-content">
            <!-- Filters -->
            <div class="artifacts-toolbar">
              <mat-form-field appearance="outline" class="filter-field">
                <mat-label>Tipo</mat-label>
                <mat-select [ngModel]="artifactType()" (ngModelChange)="artifactType.set($event); loadArtifacts()">
                  <mat-option value="all">Todos</mat-option>
                  <mat-option value="image">Imágenes</mat-option>
                  <mat-option value="video">Videos</mat-option>
                  <mat-option value="spreadsheet">Hojas de cálculo</mat-option>
                  <mat-option value="presentation">Presentaciones</mat-option>
                  <mat-option value="document">Documentos</mat-option>
                  <mat-option value="code">Código</mat-option>
                  <mat-option value="html">HTML</mat-option>
                </mat-select>
              </mat-form-field>
              <span class="artifacts-count">{{ artifactTotal() }} artefactos</span>
              <span style="flex:1"></span>
              <button mat-icon-button (click)="loadArtifacts()" matTooltip="Refrescar">
                <mat-icon>refresh</mat-icon>
              </button>
            </div>

            @if (artifactLoading()) {
              <div class="loading-container"><mat-spinner diameter="32"></mat-spinner></div>
            } @else if (artifactList().length === 0) {
              <div class="empty-state">
                <mat-icon>folder_open</mat-icon>
                <h3>No hay artefactos</h3>
                <p>Los archivos generados por los agentes aparecerán aquí.</p>
              </div>
            } @else {
              <table mat-table [dataSource]="artifactList()" class="artifacts-table">
                <ng-container matColumnDef="icon">
                  <th mat-header-cell *matHeaderCellDef></th>
                  <td mat-cell *matCellDef="let a">
                    <div class="artifact-icon" [class]="a.type">
                      <mat-icon>{{ getArtifactIcon(a.type) }}</mat-icon>
                    </div>
                  </td>
                </ng-container>
                <ng-container matColumnDef="name">
                  <th mat-header-cell *matHeaderCellDef>Nombre</th>
                  <td mat-cell *matCellDef="let a">
                    <span class="artifact-name-text">{{ a.title || a.file_name }}</span>
                    <span class="artifact-type-badge">{{ a.type }}</span>
                  </td>
                </ng-container>
                <ng-container matColumnDef="size">
                  <th mat-header-cell *matHeaderCellDef>Tamaño</th>
                  <td mat-cell *matCellDef="let a">{{ formatSize(a.file_size) }}</td>
                </ng-container>
                <ng-container matColumnDef="created">
                  <th mat-header-cell *matHeaderCellDef>Fecha</th>
                  <td mat-cell *matCellDef="let a">{{ artifactService.formatDate(a.created_at) }}</td>
                </ng-container>
                <ng-container matColumnDef="actions">
                  <th mat-header-cell *matHeaderCellDef></th>
                  <td mat-cell *matCellDef="let a">
                    <button mat-icon-button [matMenuTriggerFor]="artMenu" (click)="$event.stopPropagation()">
                      <mat-icon>more_vert</mat-icon>
                    </button>
                    <mat-menu #artMenu="matMenu">
                      <button mat-menu-item (click)="previewArtifactItem(a)"><mat-icon>visibility</mat-icon> Ver</button>
                      <button mat-menu-item (click)="copyArtifactId(a)"><mat-icon>content_copy</mat-icon> Copiar ID</button>
                      <button mat-menu-item (click)="downloadArtifact(a)"><mat-icon>download</mat-icon> Descargar</button>
                      <mat-divider></mat-divider>
                      <button mat-menu-item (click)="deleteArtifact(a)"><mat-icon color="warn">delete</mat-icon> Eliminar</button>
                    </mat-menu>
                  </td>
                </ng-container>
                <tr mat-header-row *matHeaderRowDef="artifactColumns"></tr>
                <tr mat-row *matRowDef="let row; columns: artifactColumns;" (click)="previewArtifactItem(row)" class="artifact-row"></tr>
              </table>
              <mat-paginator
                [pageSizeOptions]="[10, 25, 50]"
                [pageSize]="artifactPageSize()"
                [length]="artifactTotal()"
                (page)="onArtifactPage($event)">
              </mat-paginator>
            }
          </div>

          @if (previewArtifact()) {
            <app-artifact-viewer
              [artifact]="previewArtifact()!"
              (closed)="previewArtifact.set(undefined)"
              (downloadRequested)="downloadArtifact($event)">
            </app-artifact-viewer>
          }
        </mat-tab>

        <!-- TAB: Sandbox -->
        <mat-tab label="Sandbox">
          <div class="tab-content">
            <!-- Toolbar: Breadcrumb + Actions -->
            <div class="sandbox-toolbar">
              <div class="sandbox-breadcrumb">
                <button mat-icon-button (click)="navigateTo('')" [disabled]="currentPath() === ''" matTooltip="Inicio">
                  <mat-icon>home</mat-icon>
                </button>
                @for (crumb of breadcrumbs(); track crumb.path) {
                  <mat-icon class="breadcrumb-sep">chevron_right</mat-icon>
                  <button mat-button class="breadcrumb-btn" (click)="navigateTo(crumb.path)">{{ crumb.name }}</button>
                }
              </div>
              <div class="sandbox-toolbar-actions">
                <span class="sandbox-count" *ngIf="wsFiles().length">{{ wsFiles().length }} elementos</span>
                <button mat-icon-button (click)="toggleSandboxView()" [matTooltip]="sandboxView() === 'grid' ? 'Vista lista' : 'Vista cuadrícula'">
                  <mat-icon>{{ sandboxView() === 'grid' ? 'view_list' : 'grid_view' }}</mat-icon>
                </button>
                <button mat-icon-button (click)="loadWorkspace(currentPath())" matTooltip="Refrescar">
                  <mat-icon>refresh</mat-icon>
                </button>
              </div>
            </div>

            @if (wsLoading()) {
              <div class="loading-container">
                <mat-spinner diameter="36"></mat-spinner>
                <p>Cargando archivos...</p>
              </div>
            } @else if (wsFiles().length === 0 && currentPath() === '') {
              <div class="empty-state">
                <mat-icon>folder_open</mat-icon>
                <h3>El sandbox está vacío</h3>
                <p>Los archivos generados por los agentes aparecerán aquí.</p>
              </div>
            } @else {
              <!-- Back row -->
              @if (currentPath() !== '') {
                <div class="sandbox-back-row" (click)="navigateUp()">
                  <mat-icon>arrow_back</mat-icon>
                  <span>Subir un nivel</span>
                </div>
              }

              <!-- Grid view -->
              @if (sandboxView() === 'grid') {
                <div class="sandbox-grid">
                  @for (f of wsFiles(); track f.name) {
                    <div class="sandbox-card" [class.sandbox-card-dir]="f.is_directory"
                         (click)="onFileClick(f)">
                      <div class="sandbox-card-preview" [class]="f.is_directory ? 'folder' : getFileCategory(f.name)">
                        @if (!f.is_directory && isImage(f.name)) {
                          <img [src]="getFileThumbnailUrl(f)" [alt]="f.name" loading="lazy" />
                        } @else if (!f.is_directory && isVideo(f.name)) {
                          <mat-icon class="preview-icon">play_circle</mat-icon>
                        } @else {
                          <mat-icon class="preview-icon">{{ f.is_directory ? 'folder' : fileIcon(f.name) }}</mat-icon>
                        }
                      </div>
                      <div class="sandbox-card-body">
                        <span class="sandbox-card-name" [matTooltip]="f.name">{{ f.name }}</span>
                        <span class="sandbox-card-meta">{{ f.is_directory ? 'Carpeta' : formatSize(f.size) }}</span>
                      </div>
                      @if (!f.is_directory) {
                        <div class="sandbox-card-overlay" (click)="$event.stopPropagation()">
                          <button mat-icon-button matTooltip="Ver" (click)="onFileClick(f)">
                            <mat-icon>visibility</mat-icon>
                          </button>
                          <button mat-icon-button matTooltip="Descargar" (click)="downloadFile(f)">
                            <mat-icon>download</mat-icon>
                          </button>
                          <button mat-icon-button matTooltip="Eliminar" (click)="deleteFile(f)">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </div>
                      }
                    </div>
                  }
                </div>
              }

              <!-- List view -->
              @if (sandboxView() === 'list') {
                <div class="sandbox-file-list">
                  @for (f of wsFiles(); track f.name) {
                    <div class="sandbox-file-row" [class.sandbox-dir-row]="f.is_directory"
                         (click)="onFileClick(f)">
                      @if (!f.is_directory && isImage(f.name)) {
                        <img class="sandbox-list-thumb" [src]="getFileThumbnailUrl(f)" [alt]="f.name" loading="lazy" />
                      } @else {
                        <div class="sandbox-list-icon" [class]="f.is_directory ? 'folder' : getFileCategory(f.name)">
                          <mat-icon>{{ f.is_directory ? 'folder' : fileIcon(f.name) }}</mat-icon>
                        </div>
                      }
                      <div class="sandbox-list-info">
                        <span class="sandbox-file-name">{{ f.name }}</span>
                        <span class="sandbox-file-type">{{ f.is_directory ? 'Carpeta' : getFileExtLabel(f.name) }}</span>
                      </div>
                      <span class="sandbox-file-meta">{{ f.is_directory ? '' : formatSize(f.size) }}</span>
                      <span class="sandbox-file-actions" (click)="$event.stopPropagation()">
                        @if (!f.is_directory) {
                          @if (isPreviewable(f.name)) {
                            <button mat-icon-button matTooltip="Ver" (click)="onFileClick(f)">
                              <mat-icon>visibility</mat-icon>
                            </button>
                          }
                          <button mat-icon-button matTooltip="Descargar" (click)="downloadFile(f)">
                            <mat-icon>download</mat-icon>
                          </button>
                          <button mat-icon-button matTooltip="Eliminar" color="warn" (click)="deleteFile(f)">
                            <mat-icon>delete</mat-icon>
                          </button>
                        }
                      </span>
                    </div>
                  }
                </div>
              }
            }
          </div>

          <!-- File Viewer (reuses ArtifactViewerComponent) -->
          @if (previewArtifact()) {
            <app-artifact-viewer
              [artifact]="previewArtifact()!"
              [contentOverrideUrl]="previewContentUrl()"
              (closed)="closePreview()"
              (downloadRequested)="onPreviewDownload()">
            </app-artifact-viewer>
          }
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    /* --- Profile sections --- */
    .profile-section-card {
      margin-bottom: 0;
    }
    .task-card {
      margin-bottom: 12px;
    }
    .task-last-run {
      font-size: 13px;
      color: #64748b;
      margin-top: 8px;
    }

    /* --- Sandbox Toolbar --- */
    .sandbox-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
      padding: 8px 12px;
      background: #f8fafc;
      border-radius: 10px;
      border: 1px solid rgba(0, 0, 0, 0.06);
    }
    .sandbox-breadcrumb {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 2px;
      min-width: 0;
    }
    .breadcrumb-sep { font-size: 18px; width: 18px; height: 18px; color: #94a3b8; }
    .breadcrumb-btn { min-width: unset; padding: 0 8px; font-size: 13px; }
    .sandbox-toolbar-actions {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }
    .sandbox-count { font-size: 12px; color: #64748b; margin-right: 4px; white-space: nowrap; }

    /* --- Back row --- */
    .sandbox-back-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      margin-bottom: 12px;
      cursor: pointer;
      border-radius: 8px;
      color: #64748b;
      font-size: 13px;
      transition: background 0.15s;
    }
    .sandbox-back-row:hover { background: rgba(0, 0, 0, 0.04); }
    .sandbox-back-row mat-icon { font-size: 20px; width: 20px; height: 20px; }

    /* --- Grid View --- */
    .sandbox-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 16px;
    }
    .sandbox-card {
      position: relative;
      border-radius: 12px;
      border: 1px solid rgba(0, 0, 0, 0.06);
      overflow: hidden;
      cursor: pointer;
      transition: box-shadow 0.2s, transform 0.15s;
      background: white;
    }
    .sandbox-card:hover {
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
      transform: translateY(-2px);
    }
    .sandbox-card-dir:hover { border-color: #f59e0b; }
    .sandbox-card-preview {
      position: relative;
      width: 100%;
      aspect-ratio: 4/3;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      background: #f1f5f9;
    }
    .sandbox-card-preview img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .sandbox-card-preview .preview-icon {
      font-size: 40px; width: 40px; height: 40px; color: #94a3b8;
    }
    .sandbox-card-preview.folder { background: #fefce8; }
    .sandbox-card-preview.folder .preview-icon { color: #f59e0b; }
    .sandbox-card-preview.media { background: #eff6ff; }
    .sandbox-card-preview.media .preview-icon { color: #3b82f6; }
    .sandbox-card-preview.video-file { background: #fdf2f8; }
    .sandbox-card-preview.video-file .preview-icon { color: #ec4899; }
    .sandbox-card-preview.code-file { background: #fff7ed; }
    .sandbox-card-preview.code-file .preview-icon { color: #f97316; }
    .sandbox-card-preview.doc-file { background: #f0fdf4; }
    .sandbox-card-preview.doc-file .preview-icon { color: #22c55e; }

    .sandbox-card-body {
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .sandbox-card-name {
      font-size: 13px;
      font-weight: 500;
      color: #1e293b;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sandbox-card-meta { font-size: 11px; color: #64748b; }

    .sandbox-card-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(15, 23, 42, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      opacity: 0;
      transition: opacity 0.2s;
    }
    .sandbox-card:hover .sandbox-card-overlay { opacity: 1; }
    .sandbox-card-overlay button { color: #fff !important; }

    /* --- List View --- */
    .sandbox-file-list {
      border: 1px solid rgba(0, 0, 0, 0.06);
      border-radius: 12px;
      overflow: hidden;
    }
    .sandbox-file-row {
      display: flex;
      align-items: center;
      padding: 10px 16px;
      gap: 12px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.04);
      cursor: pointer;
      transition: background 0.15s;
    }
    .sandbox-file-row:last-child { border-bottom: none; }
    .sandbox-file-row:hover { background: rgba(0, 0, 0, 0.02); }
    .sandbox-dir-row:hover { background: #fefce8; }

    .sandbox-list-thumb {
      width: 40px;
      height: 40px;
      border-radius: 6px;
      object-fit: cover;
      flex-shrink: 0;
      background: #f1f5f9;
    }
    .sandbox-list-icon {
      width: 40px; height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      background: #f1f5f9;
    }
    .sandbox-list-icon.folder { background: #fefce8; color: #f59e0b; }
    .sandbox-list-icon.media { background: #eff6ff; color: #3b82f6; }
    .sandbox-list-icon.video-file { background: #fdf2f8; color: #ec4899; }
    .sandbox-list-icon.code-file { background: #fff7ed; color: #f97316; }
    .sandbox-list-icon.doc-file { background: #f0fdf4; color: #22c55e; }

    .sandbox-list-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .sandbox-file-name {
      font-size: 14px;
      font-weight: 400;
      color: #1e293b;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .sandbox-dir-row .sandbox-file-name { font-weight: 500; }
    .sandbox-file-type { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
    .sandbox-file-meta {
      flex-shrink: 0;
      font-size: 12px;
      color: #64748b;
      min-width: 70px;
      text-align: right;
    }
    .sandbox-file-actions {
      flex-shrink: 0;
      display: flex;
      gap: 2px;
    }

    /* --- Artifacts Tab --- */
    .artifacts-toolbar {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding: 4px 0;
    }
    .artifacts-toolbar .filter-field {
      width: 160px;
    }
    .artifacts-count {
      font-size: 13px;
      color: #64748b;
    }
    .artifacts-table { width: 100%; }
    .artifact-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: #f1f5f9;
    }
    .artifact-icon.image { background: #e0f2fe; color: #0284c7; }
    .artifact-icon.video { background: #fce7f3; color: #db2777; }
    .artifact-icon.presentation { background: #f3e8ff; color: #9333ea; }
    .artifact-icon.spreadsheet { background: #dcfce7; color: #16a34a; }
    .artifact-icon.document { background: #ecfdf5; color: #059669; }
    .artifact-icon.code { background: #fff7ed; color: #ea580c; }
    .artifact-icon.html { background: #f0fdfa; color: #0d9488; }
    .artifact-name-text { font-weight: 500; display: block; color: #1e293b; }
    .artifact-type-badge { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
    .artifact-row { cursor: pointer; transition: background 0.15s; }
    .artifact-row:hover { background: rgba(0,0,0,0.02); }
  `],
})
export class ProfileComponent implements OnInit {
  private authService = inject(AuthService);
  userId = signal(this.authService.currentUser()?.email || '');
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

  // Artifacts tab
  artifactList = signal<Artifact[]>([]);
  artifactTotal = signal(0);
  artifactLoading = signal(false);
  artifactType = signal('all');
  artifactPageSize = signal(25);
  artifactPage = signal(0);
  artifactColumns = ['icon', 'name', 'size', 'created', 'actions'];

  // Sandbox explorer
  currentPath = signal('');
  wsFiles = signal<WorkspaceFile[]>([]);
  wsLoading = signal(false);
  breadcrumbs = signal<{ name: string; path: string }[]>([]);
  sandboxView = signal<'grid' | 'list'>('grid');
  previewArtifact = signal<Artifact | undefined>(undefined);
  previewContentUrl = signal('');

  artifactService = inject(ArtifactService);

  constructor(private profileService: ProfileService, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.loadProfile();
    this.loadTasks();
    this.loadArtifacts();
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

  // --- Artifacts ---

  loadArtifacts(): void {
    this.artifactLoading.set(true);
    const type = this.artifactType() === 'all' ? undefined : this.artifactType() as any;
    this.artifactService.listArtifacts(undefined, type, undefined, this.artifactPageSize(), this.artifactPage() * this.artifactPageSize())
      .subscribe({
        next: (r: ArtifactListResponse) => {
          this.artifactList.set(r.artifacts);
          this.artifactTotal.set(r.total);
          this.artifactLoading.set(false);
        },
        error: () => {
          this.artifactList.set([]);
          this.artifactLoading.set(false);
        },
      });
  }

  onArtifactPage(event: any): void {
    this.artifactPage.set(event.pageIndex);
    this.artifactPageSize.set(event.pageSize);
    this.loadArtifacts();
  }

  previewArtifactItem(a: Artifact): void {
    this.previewContentUrl.set('');
    this.previewArtifact.set(a);
  }

  downloadArtifact(a: Artifact): void {
    this.artifactService.downloadArtifact(a.artifact_id).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const el = document.createElement('a');
      el.href = url;
      el.download = a.file_name;
      el.click();
      window.URL.revokeObjectURL(url);
    });
  }

  deleteArtifact(a: Artifact): void {
    if (!confirm(`¿Eliminar "${a.title || a.file_name}"?`)) return;
    this.artifactService.deleteArtifact(a.artifact_id).subscribe(() => {
      this.snack.open('Artefacto eliminado', 'OK', { duration: 2000 });
      this.loadArtifacts();
    });
  }

  copyArtifactId(a: Artifact): void {
    navigator.clipboard.writeText(`@${a.artifact_id}`).then(() => {
      this.snack.open(`ID copiado: @${a.artifact_id}`, 'OK', { duration: 2000 });
    });
  }

  getArtifactIcon(type: string): string {
    return this.artifactService.getIconForType(type as any);
  }

  // --- Sandbox Explorer ---

  loadWorkspace(path: string): void {
    this.wsLoading.set(true);
    this.currentPath.set(path);
    this.updateBreadcrumbs(path);
    this.profileService.listWorkspace(path, this.userId()).subscribe({
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
    const url = this.profileService.getFileUrl(filePath, this.userId());
    const a = document.createElement('a');
    a.href = url;
    a.download = f.name;
    a.target = '_blank';
    a.click();
  }

  deleteFile(f: WorkspaceFile): void {
    if (!confirm(`¿Eliminar "${f.name}"?`)) return;
    const filePath = this.joinPath(this.currentPath(), f.name);
    this.profileService.deleteWorkspaceFile(filePath, this.userId()).subscribe({
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

  // --- Enhanced Sandbox ---

  private static IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg']);
  private static VIDEO_EXTS = new Set(['mp4', 'webm', 'mov']);
  private static CODE_EXTS = new Set(['py', 'js', 'ts', 'json', 'html', 'css', 'sql', 'sh', 'bash']);

  private getExt(name: string): string {
    return name.split('.').pop()?.toLowerCase() ?? '';
  }

  isImage(name: string): boolean {
    return ProfileComponent.IMAGE_EXTS.has(this.getExt(name));
  }

  isVideo(name: string): boolean {
    return ProfileComponent.VIDEO_EXTS.has(this.getExt(name));
  }

  isPreviewable(name: string): boolean {
    return this.isImage(name) || this.isVideo(name);
  }

  getFileCategory(name: string): string {
    if (this.isImage(name)) return 'media';
    if (this.isVideo(name)) return 'video-file';
    if (ProfileComponent.CODE_EXTS.has(this.getExt(name))) return 'code-file';
    const ext = this.getExt(name);
    if (['pdf', 'txt', 'md', 'log', 'doc', 'docx'].includes(ext)) return 'doc-file';
    return '';
  }

  getFileExtLabel(name: string): string {
    const ext = this.getExt(name);
    return ext ? ext.toUpperCase() : 'Archivo';
  }

  getFileThumbnailUrl(f: WorkspaceFile): string {
    const filePath = this.joinPath(this.currentPath(), f.name);
    return this.profileService.getFileUrl(filePath, this.userId());
  }

  toggleSandboxView(): void {
    this.sandboxView.set(this.sandboxView() === 'grid' ? 'list' : 'grid');
  }

  onFileClick(f: WorkspaceFile): void {
    if (f.is_directory) {
      this.navigateTo(this.joinPath(this.currentPath(), f.name));
      return;
    }
    if (!this.isPreviewable(f.name)) {
      this.downloadFile(f);
      return;
    }
    const filePath = this.joinPath(this.currentPath(), f.name);
    const fileUrl = this.profileService.getFileUrl(filePath, this.userId());
    const fileType = this.isImage(f.name) ? 'image' : 'video';

    const syntheticArtifact: Artifact = {
      id: 0,
      artifact_id: '',
      type: fileType as Artifact['type'],
      title: f.name,
      file_name: f.name,
      file_path: filePath,
      file_size: f.size,
      source: 'sandbox',
      metadata: {},
      version: 1,
      is_latest: true,
      status: 'active',
      created_at: '',
      updated_at: '',
      accessed_at: '',
    };

    this.previewContentUrl.set(fileUrl);
    this.previewArtifact.set(syntheticArtifact);
  }

  closePreview(): void {
    this.previewArtifact.set(undefined);
    this.previewContentUrl.set('');
  }

  onPreviewDownload(): void {
    const art = this.previewArtifact();
    if (art) {
      const url = this.previewContentUrl();
      const a = document.createElement('a');
      a.href = url;
      a.download = art.file_name;
      a.target = '_blank';
      a.click();
    }
  }
}
