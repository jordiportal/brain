import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

interface Collection {
  name: string;
  total_chunks: number;
  total_documents: number;
}

interface SearchResult {
  content: string;
  metadata: any;
  score: number;
}

@Component({
  selector: 'app-rag',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatTabsModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatChipsModule,
    MatSnackBarModule,
    MatDialogModule,
    MatTableModule,
    MatTooltipModule
  ],
  template: `
    <div class="rag-page">
      <div class="page-header">
        <div>
          <h1>RAG / Documentos</h1>
          <p class="subtitle">Gestión de documentos y búsqueda semántica</p>
        </div>
        <button mat-raised-button color="primary" (click)="refreshCollections()">
          <mat-icon>refresh</mat-icon>
          Actualizar
        </button>
      </div>

      <mat-tab-group>
        <!-- Tab Colecciones -->
        <mat-tab label="Colecciones">
          <div class="tab-content">
            @if (loadingCollections()) {
              <div class="loading-container">
                <mat-spinner diameter="40"></mat-spinner>
              </div>
            } @else {
              <div class="collections-grid">
                @for (collection of collections(); track collection.name) {
                  <mat-card class="collection-card" [class.selected]="selectedCollection() === collection.name"
                            (click)="selectCollection(collection.name)">
                    <mat-card-header>
                      <div class="collection-icon">
                        <mat-icon>folder</mat-icon>
                      </div>
                      <mat-card-title>{{ collection.name }}</mat-card-title>
                    </mat-card-header>
                    <mat-card-content>
                      <div class="stats">
                        <div class="stat">
                          <span class="value">{{ collection.total_documents }}</span>
                          <span class="label">Documentos</span>
                        </div>
                        <div class="stat">
                          <span class="value">{{ collection.total_chunks }}</span>
                          <span class="label">Chunks</span>
                        </div>
                      </div>
                    </mat-card-content>
                    <mat-card-actions>
                      <button mat-button color="warn" (click)="deleteCollection(collection.name, $event)">
                        <mat-icon>delete</mat-icon>
                        Eliminar
                      </button>
                    </mat-card-actions>
                  </mat-card>
                } @empty {
                  <div class="empty-state">
                    <mat-icon>folder_open</mat-icon>
                    <h3>No hay colecciones</h3>
                    <p>Sube documentos para crear tu primera colección</p>
                  </div>
                }
              </div>
            }
          </div>
        </mat-tab>

        <!-- Tab Subir Documentos -->
        <mat-tab label="Subir Documentos">
          <div class="tab-content">
            <mat-card class="upload-card">
              <mat-card-content>
                <div class="upload-form">
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Colección</mat-label>
                    <input matInput [(ngModel)]="uploadCollection" placeholder="default">
                    <mat-hint>Nombre de la colección donde se indexará el documento</mat-hint>
                  </mat-form-field>

                  <div class="upload-area" 
                       (dragover)="onDragOver($event)"
                       (dragleave)="onDragLeave($event)"
                       (drop)="onDrop($event)"
                       [class.dragging]="isDragging">
                    <input type="file" #fileInput 
                           (change)="onFileSelected($event)"
                           accept=".pdf,.txt,.md,.docx,.html"
                           style="display: none">
                    
                    <mat-icon>cloud_upload</mat-icon>
                    <p>Arrastra archivos aquí o</p>
                    <button mat-raised-button color="primary" (click)="fileInput.click()">
                      Seleccionar Archivos
                    </button>
                    <p class="hint">Formatos: PDF, TXT, MD, DOCX, HTML</p>
                  </div>

                  @if (selectedFile()) {
                    <div class="selected-file">
                      <mat-icon>description</mat-icon>
                      <span>{{ selectedFile()!.name }}</span>
                      <span class="size">({{ formatFileSize(selectedFile()!.size) }})</span>
                      <button mat-icon-button (click)="clearFile()">
                        <mat-icon>close</mat-icon>
                      </button>
                    </div>
                  }

                  @if (uploading()) {
                    <mat-progress-bar mode="indeterminate"></mat-progress-bar>
                    <p class="upload-status">Indexando documento...</p>
                  }

                  <button mat-raised-button color="primary" 
                          [disabled]="!selectedFile() || uploading()"
                          (click)="uploadFile()"
                          class="upload-btn">
                    <mat-icon>upload</mat-icon>
                    Subir e Indexar
                  </button>
                </div>
              </mat-card-content>
            </mat-card>

            <!-- Ingestar texto directo -->
            <mat-card class="text-card">
              <mat-card-header>
                <mat-card-title>Indexar Texto Directo</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>ID del Documento</mat-label>
                  <input matInput [(ngModel)]="textDocumentId" placeholder="mi-documento">
                </mat-form-field>
                
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Texto a indexar</mat-label>
                  <textarea matInput [(ngModel)]="textContent" rows="6" 
                            placeholder="Pega aquí el texto que quieres indexar..."></textarea>
                </mat-form-field>

                <button mat-raised-button color="accent" 
                        [disabled]="!textContent || !textDocumentId || uploading()"
                        (click)="uploadText()">
                  <mat-icon>text_snippet</mat-icon>
                  Indexar Texto
                </button>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Tab Búsqueda -->
        <mat-tab label="Búsqueda">
          <div class="tab-content">
            <mat-card class="search-card">
              <mat-card-content>
                <div class="search-form">
                  <mat-form-field appearance="outline" class="collection-select">
                    <mat-label>Colección</mat-label>
                    <mat-select [(ngModel)]="searchCollection">
                      @for (col of collections(); track col.name) {
                        <mat-option [value]="col.name">{{ col.name }}</mat-option>
                      }
                    </mat-select>
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="search-input">
                    <mat-label>Buscar</mat-label>
                    <input matInput [(ngModel)]="searchQuery" 
                           placeholder="Escribe tu consulta..."
                           (keydown.enter)="search()">
                    <mat-icon matSuffix>search</mat-icon>
                  </mat-form-field>

                  <button mat-raised-button color="primary" 
                          [disabled]="!searchQuery || searching()"
                          (click)="search()">
                    @if (searching()) {
                      <mat-spinner diameter="20"></mat-spinner>
                    } @else {
                      <mat-icon>search</mat-icon>
                    }
                    Buscar
                  </button>
                </div>
              </mat-card-content>
            </mat-card>

            @if (searchResults().length > 0) {
              <div class="results-container">
                <h3>Resultados ({{ searchResults().length }})</h3>
                @for (result of searchResults(); track $index) {
                  <mat-card class="result-card">
                    <mat-card-content>
                      <div class="result-header">
                        <mat-chip>Score: {{ (result.score * 100).toFixed(1) }}%</mat-chip>
                        @if (result.metadata?.source) {
                          <span class="source">{{ result.metadata.source }}</span>
                        }
                      </div>
                      <p class="result-content">{{ result.content }}</p>
                    </mat-card-content>
                  </mat-card>
                }
              </div>
            }

            @if (searchPerformed() && searchResults().length === 0) {
              <div class="no-results">
                <mat-icon>search_off</mat-icon>
                <p>No se encontraron resultados para "{{ lastQuery() }}"</p>
              </div>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .rag-page {
      max-width: 1200px;
      margin: 0 auto;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .subtitle {
      color: #666;
      margin: 4px 0 0;
    }

    .tab-content {
      padding: 24px 0;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    /* Collections */
    .collections-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }

    .collection-card {
      cursor: pointer;
      transition: transform 0.2s, box-shadow 0.2s;
      border-radius: 12px;
    }

    .collection-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }

    .collection-card.selected {
      border: 2px solid #43e97b;
    }

    .collection-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 16px;
    }

    .collection-icon mat-icon {
      color: white;
    }

    .stats {
      display: flex;
      gap: 24px;
      margin-top: 16px;
    }

    .stat {
      text-align: center;
    }

    .stat .value {
      display: block;
      font-size: 24px;
      font-weight: 600;
      color: #1a1a2e;
    }

    .stat .label {
      font-size: 12px;
      color: #666;
    }

    .empty-state {
      grid-column: 1 / -1;
      text-align: center;
      padding: 64px;
      background: white;
      border-radius: 12px;
    }

    .empty-state mat-icon {
      font-size: 72px;
      width: 72px;
      height: 72px;
      color: #ccc;
    }

    /* Upload */
    .upload-card, .text-card {
      border-radius: 12px;
      margin-bottom: 20px;
    }

    .upload-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .full-width {
      width: 100%;
    }

    .upload-area {
      border: 2px dashed #ccc;
      border-radius: 12px;
      padding: 48px;
      text-align: center;
      transition: all 0.2s;
      cursor: pointer;
    }

    .upload-area:hover, .upload-area.dragging {
      border-color: #43e97b;
      background: #f0fff4;
    }

    .upload-area mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #43e97b;
    }

    .upload-area .hint {
      font-size: 12px;
      color: #888;
      margin-top: 8px;
    }

    .selected-file {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .selected-file .size {
      color: #888;
      margin-left: auto;
    }

    .upload-status {
      text-align: center;
      color: #666;
    }

    .upload-btn {
      align-self: flex-start;
    }

    /* Search */
    .search-card {
      border-radius: 12px;
      margin-bottom: 24px;
    }

    .search-form {
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }

    .collection-select {
      width: 200px;
    }

    .search-input {
      flex: 1;
    }

    .results-container h3 {
      margin: 0 0 16px;
      color: #1a1a2e;
    }

    .result-card {
      margin-bottom: 12px;
      border-radius: 8px;
    }

    .result-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .source {
      font-size: 12px;
      color: #888;
    }

    .result-content {
      margin: 0;
      color: #333;
      line-height: 1.6;
      white-space: pre-wrap;
    }

    .no-results {
      text-align: center;
      padding: 48px;
      color: #666;
    }

    .no-results mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #ccc;
    }
  `]
})
export class RagComponent implements OnInit {
  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);
  
  private readonly API_URL = `${environment.apiUrl}/rag`;

  // Collections
  collections = signal<Collection[]>([]);
  loadingCollections = signal(false);
  selectedCollection = signal<string>('');

  // Upload
  uploadCollection = 'default';
  selectedFile = signal<File | null>(null);
  uploading = signal(false);
  isDragging = false;

  // Text upload
  textDocumentId = '';
  textContent = '';

  // Search
  searchCollection = 'default';
  searchQuery = '';
  searchResults = signal<SearchResult[]>([]);
  searching = signal(false);
  searchPerformed = signal(false);
  lastQuery = signal('');

  ngOnInit(): void {
    this.refreshCollections();
  }

  refreshCollections(): void {
    this.loadingCollections.set(true);
    this.http.get<{collections: Collection[]}>(`${this.API_URL}/collections`).subscribe({
      next: (response) => {
        this.collections.set(response.collections || []);
        if (response.collections?.length > 0) {
          this.searchCollection = response.collections[0].name;
        }
        this.loadingCollections.set(false);
      },
      error: () => {
        this.loadingCollections.set(false);
        this.snackBar.open('Error cargando colecciones', 'Cerrar', { duration: 3000 });
      }
    });
  }

  selectCollection(name: string): void {
    this.selectedCollection.set(name);
    this.searchCollection = name;
  }

  deleteCollection(name: string, event: Event): void {
    event.stopPropagation();
    if (!confirm(`¿Eliminar la colección "${name}" y todos sus documentos?`)) return;

    this.http.delete(`${this.API_URL}/collections/${name}`).subscribe({
      next: () => {
        this.snackBar.open('Colección eliminada', 'Cerrar', { duration: 2000 });
        this.refreshCollections();
      },
      error: () => {
        this.snackBar.open('Error eliminando colección', 'Cerrar', { duration: 3000 });
      }
    });
  }

  // File upload handlers
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.selectedFile.set(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile.set(input.files[0]);
    }
  }

  clearFile(): void {
    this.selectedFile.set(null);
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  uploadFile(): void {
    const file = this.selectedFile();
    if (!file) return;

    this.uploading.set(true);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection', this.uploadCollection);

    this.http.post(`${this.API_URL}/ingest/file`, formData).subscribe({
      next: (response: any) => {
        this.uploading.set(false);
        this.selectedFile.set(null);
        this.snackBar.open(
          `Documento indexado: ${response.chunks_created} chunks creados`, 
          'Cerrar', 
          { duration: 3000 }
        );
        this.refreshCollections();
      },
      error: (err) => {
        this.uploading.set(false);
        const msg = err.error?.detail || 'Error subiendo documento';
        this.snackBar.open(msg, 'Cerrar', { duration: 5000 });
      }
    });
  }

  uploadText(): void {
    if (!this.textContent || !this.textDocumentId) return;

    this.uploading.set(true);

    this.http.post(`${this.API_URL}/ingest/text`, {
      text: this.textContent,
      document_id: this.textDocumentId,
      collection: this.uploadCollection
    }).subscribe({
      next: (response: any) => {
        this.uploading.set(false);
        this.textContent = '';
        this.textDocumentId = '';
        this.snackBar.open(
          `Texto indexado: ${response.chunks_created} chunks creados`,
          'Cerrar',
          { duration: 3000 }
        );
        this.refreshCollections();
      },
      error: (err) => {
        this.uploading.set(false);
        const msg = err.error?.detail || 'Error indexando texto';
        this.snackBar.open(msg, 'Cerrar', { duration: 5000 });
      }
    });
  }

  search(): void {
    if (!this.searchQuery) return;

    this.searching.set(true);
    this.searchPerformed.set(false);

    this.http.post<{results: SearchResult[]}>(`${this.API_URL}/search`, {
      query: this.searchQuery,
      collection: this.searchCollection,
      top_k: 5
    }).subscribe({
      next: (response) => {
        this.searchResults.set(response.results || []);
        this.lastQuery.set(this.searchQuery);
        this.searchPerformed.set(true);
        this.searching.set(false);
      },
      error: (err) => {
        this.searching.set(false);
        const msg = err.error?.detail || 'Error en la búsqueda';
        this.snackBar.open(msg, 'Cerrar', { duration: 3000 });
      }
    });
  }
}
