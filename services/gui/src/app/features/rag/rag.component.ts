import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-rag',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule],
  template: `
    <div class="rag-page">
      <div class="page-header">
        <div>
          <h1>RAG / Documentos</h1>
          <p class="subtitle">Gestión de documentos y búsqueda semántica</p>
        </div>
        <button mat-raised-button color="primary">
          <mat-icon>upload</mat-icon>
          Subir Documentos
        </button>
      </div>

      <mat-card class="info-card">
        <mat-card-content>
          <mat-icon>info</mat-icon>
          <div>
            <h3>Módulo en desarrollo</h3>
            <p>El módulo de RAG (Retrieval Augmented Generation) permitirá:</p>
            <ul>
              <li>Subir y gestionar documentos</li>
              <li>Crear colecciones temáticas</li>
              <li>Búsqueda semántica con embeddings</li>
              <li>Integración con cadenas de pensamiento</li>
            </ul>
          </div>
        </mat-card-content>
      </mat-card>
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

    .info-card {
      border-radius: 12px;
    }

    .info-card mat-card-content {
      display: flex;
      gap: 16px;
      padding: 24px;
    }

    .info-card mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #1976d2;
    }

    .info-card h3 {
      margin: 0 0 8px;
      color: #1a1a2e;
    }

    .info-card p {
      margin: 0 0 12px;
      color: #666;
    }

    .info-card ul {
      margin: 0;
      padding-left: 20px;
      color: #666;
    }

    .info-card li {
      margin-bottom: 4px;
    }
  `]
})
export class RagComponent {}
