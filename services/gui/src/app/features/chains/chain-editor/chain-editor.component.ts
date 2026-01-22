import { Component, OnInit, Input, Output, EventEmitter, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSliderModule } from '@angular/material/slider';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { NgxGraphModule } from '@swimlane/ngx-graph';
import { Subject } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

interface ChainNode {
  id: string;
  name: string;
  type: string;
  system_prompt?: string;
  config?: any;
  collection?: string;
  top_k?: number;
  tools?: string[];
}

interface ChainEdge {
  source: string;
  target: string;
  condition?: string;
}

interface ChainConfig {
  use_memory?: boolean;
  temperature?: number;
  max_memory_messages?: number;
  system_prompt?: string;
  rag_collection?: string;
  rag_top_k?: number;
  model?: string;
}

interface ChainFull {
  id: string;
  name: string;
  description: string;
  type: string;
  version: string;
  nodes: ChainNode[];
  edges: ChainEdge[];
  config: ChainConfig;
}

@Component({
  selector: 'app-chain-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatSelectModule,
    MatSliderModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    MatDividerModule,
    MatChipsModule,
    NgxGraphModule
  ],
  template: `
    <div class="editor-container">
      <!-- Header -->
      <div class="editor-header">
        <div class="chain-title">
          <mat-icon class="type-icon" [class]="chain?.type || ''">{{ getTypeIcon() }}</mat-icon>
          <div>
            <h2>{{ chain?.name || 'Cargando...' }}</h2>
            <span class="chain-meta">{{ chain?.type | uppercase }} - v{{ chain?.version }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button mat-button (click)="close.emit()">
            <mat-icon>close</mat-icon>
            Cerrar
          </button>
          <button mat-raised-button color="primary" 
                  [disabled]="saving() || !hasChanges()"
                  (click)="saveChanges()">
            @if (saving()) {
              <mat-spinner diameter="20"></mat-spinner>
            } @else {
              <mat-icon>save</mat-icon>
            }
            Guardar
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="loading-container">
          <mat-spinner diameter="48"></mat-spinner>
          <p>Cargando cadena...</p>
        </div>
      } @else if (chain) {
        <div class="editor-content">
          <!-- Graph Panel -->
          <div class="graph-panel">
            <div class="panel-header">
              <h3>
                <mat-icon>account_tree</mat-icon>
                Grafo de Ejecución
              </h3>
              <div class="graph-controls">
                <button mat-icon-button matTooltip="Centrar" (click)="centerGraph()">
                  <mat-icon>center_focus_strong</mat-icon>
                </button>
                <button mat-icon-button matTooltip="Zoom In" (click)="zoomIn()">
                  <mat-icon>zoom_in</mat-icon>
                </button>
                <button mat-icon-button matTooltip="Zoom Out" (click)="zoomOut()">
                  <mat-icon>zoom_out</mat-icon>
                </button>
              </div>
            </div>
            
            <div class="graph-container">
              <ngx-graph
                [links]="graphLinks"
                [nodes]="graphNodes"
                [layoutSettings]="layoutSettings"
                layout="dagre"
                [zoomToFit$]="zoomToFit$"
                [center$]="center$"
                [autoZoom]="true"
                [autoCenter]="true">
                
                <!-- Node Template -->
                <ng-template #nodeTemplate let-node>
                  <svg:g class="node" 
                         [class.selected]="selectedNode?.id === node.id"
                         (click)="selectNode(node)">
                    <svg:rect 
                      [attr.width]="node.dimension?.width || 160"
                      [attr.height]="node.dimension?.height || 60"
                      [attr.fill]="getNodeColor(node.data?.type)"
                      rx="8"
                      ry="8"
                      class="node-rect"/>
                    <svg:text 
                      [attr.x]="(node.dimension?.width || 160) / 2" 
                      [attr.y]="20"
                      text-anchor="middle"
                      class="node-label">
                      {{ node.label }}
                    </svg:text>
                    <svg:text 
                      [attr.x]="(node.dimension?.width || 160) / 2" 
                      [attr.y]="40"
                      text-anchor="middle"
                      class="node-type">
                      {{ node.data?.type | uppercase }}
                    </svg:text>
                    <!-- Icon -->
                    <svg:text 
                      [attr.x]="15" 
                      [attr.y]="38"
                      class="node-icon">
                      {{ getNodeIconChar(node.data?.type) }}
                    </svg:text>
                  </svg:g>
                </ng-template>

                <!-- Link Template -->
                <ng-template #linkTemplate let-link>
                  <svg:g class="link-group">
                    <svg:path 
                      [attr.d]="link.line"
                      stroke="#94a3b8"
                      stroke-width="2"
                      fill="none"
                      marker-end="url(#arrow)"/>
                  </svg:g>
                </ng-template>

              </ngx-graph>

              <!-- Arrow marker definition -->
              <svg style="position: absolute; width: 0; height: 0;">
                <defs>
                  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
                          markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/>
                  </marker>
                </defs>
              </svg>
            </div>

            <!-- Node Legend -->
            <div class="node-legend">
              <span class="legend-item"><span class="dot input"></span> Input</span>
              <span class="legend-item"><span class="dot llm"></span> LLM</span>
              <span class="legend-item"><span class="dot rag"></span> RAG</span>
              <span class="legend-item"><span class="dot tool"></span> Tool</span>
              <span class="legend-item"><span class="dot output"></span> Output</span>
            </div>
          </div>

          <!-- Properties Panel -->
          <div class="properties-panel">
            @if (selectedNode) {
              <div class="panel-header">
                <h3>
                  <mat-icon>tune</mat-icon>
                  Propiedades del Nodo
                </h3>
                <button mat-icon-button matTooltip="Deseleccionar" (click)="selectedNode = null">
                  <mat-icon>close</mat-icon>
                </button>
              </div>

              <div class="properties-content">
                <div class="node-info">
                  <mat-chip [class]="selectedNode.type">{{ selectedNode.type | uppercase }}</mat-chip>
                  <span class="node-id">ID: {{ selectedNode.id }}</span>
                </div>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Nombre</mat-label>
                  <input matInput [(ngModel)]="selectedNode.name" (ngModelChange)="markDirty()">
                </mat-form-field>

                @if (selectedNode.type === 'llm' || selectedNode.type === 'tool' || selectedNode.type === 'output') {
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>System Prompt</mat-label>
                    <textarea matInput 
                              [(ngModel)]="selectedNode.system_prompt" 
                              (ngModelChange)="markDirty()"
                              rows="8"
                              placeholder="Define el comportamiento del nodo..."></textarea>
                    <mat-hint>Define las instrucciones para el LLM</mat-hint>
                  </mat-form-field>
                }

                @if (selectedNode.type === 'rag') {
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Colección</mat-label>
                    <input matInput [(ngModel)]="selectedNode.collection" (ngModelChange)="markDirty()">
                    <mat-hint>Colección de documentos para búsqueda</mat-hint>
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Top K</mat-label>
                    <input matInput type="number" [(ngModel)]="selectedNode.top_k" (ngModelChange)="markDirty()">
                    <mat-hint>Número de documentos a recuperar</mat-hint>
                  </mat-form-field>
                }

                @if (selectedNode.type === 'tool') {
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Tools</mat-label>
                    <mat-select [(ngModel)]="selectedNode.tools" (ngModelChange)="markDirty()" multiple>
                      <mat-option value="calculator">Calculator</mat-option>
                      <mat-option value="web_search">Web Search</mat-option>
                      <mat-option value="file_reader">File Reader</mat-option>
                      <mat-option value="code_executor">Code Executor</mat-option>
                    </mat-select>
                    <mat-hint>Herramientas disponibles para el agente</mat-hint>
                  </mat-form-field>
                }
              </div>
            } @else {
              <!-- Chain Config -->
              <div class="panel-header">
                <h3>
                  <mat-icon>settings</mat-icon>
                  Configuración de Cadena
                </h3>
              </div>

              <div class="properties-content">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Nombre</mat-label>
                  <input matInput [(ngModel)]="chain!.name" (ngModelChange)="markDirty()">
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Descripción</mat-label>
                  <textarea matInput 
                            [(ngModel)]="chain!.description" 
                            (ngModelChange)="markDirty()"
                            rows="3"></textarea>
                </mat-form-field>

                <mat-divider></mat-divider>

                <h4>Parámetros de Ejecución</h4>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Temperatura</mat-label>
                  <input matInput type="number" step="0.1" min="0" max="2"
                         [(ngModel)]="chain!.config.temperature" 
                         (ngModelChange)="markDirty()">
                  <mat-hint>0 = determinista, 2 = creativo</mat-hint>
                </mat-form-field>

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>System Prompt Global</mat-label>
                  <textarea matInput 
                            [(ngModel)]="chain!.config.system_prompt" 
                            (ngModelChange)="markDirty()"
                            rows="4"
                            placeholder="Prompt global para todos los nodos LLM..."></textarea>
                </mat-form-field>

                @if (chain!.type === 'rag') {
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Colección RAG</mat-label>
                    <input matInput [(ngModel)]="chain!.config.rag_collection" (ngModelChange)="markDirty()">
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>RAG Top K</mat-label>
                    <input matInput type="number" [(ngModel)]="chain!.config.rag_top_k" (ngModelChange)="markDirty()">
                  </mat-form-field>
                }

                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>Max Memory Messages</mat-label>
                  <input matInput type="number" 
                         [(ngModel)]="chain!.config.max_memory_messages" 
                         (ngModelChange)="markDirty()">
                </mat-form-field>
              </div>
            }

            <!-- Help Section -->
            <div class="help-section">
              <mat-icon>info</mat-icon>
              <div>
                <strong>Tip:</strong> Haz clic en un nodo del grafo para editar sus propiedades específicas.
              </div>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .editor-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: #f8fafc;
    }

    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: white;
      border-bottom: 1px solid #e2e8f0;
    }

    .chain-title {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .type-icon {
      width: 48px;
      height: 48px;
      font-size: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      color: white;
    }

    .type-icon.conversational { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .type-icon.rag { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .type-icon.tools { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }

    .chain-title h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }

    .chain-meta {
      font-size: 12px;
      color: #64748b;
    }

    .header-actions {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .loading-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      color: #64748b;
    }

    .editor-content {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    .graph-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      border-right: 1px solid #e2e8f0;
    }

    .properties-panel {
      width: 400px;
      display: flex;
      flex-direction: column;
      background: white;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid #e2e8f0;
    }

    .panel-header h3 {
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 600;
      color: #334155;
    }

    .graph-controls {
      display: flex;
      gap: 4px;
    }

    .graph-container {
      flex: 1;
      position: relative;
      background: #f1f5f9;
    }

    ngx-graph {
      width: 100%;
      height: 100%;
    }

    :host ::ng-deep .node-rect {
      cursor: pointer;
      transition: all 0.2s;
      stroke: transparent;
      stroke-width: 2;
    }

    :host ::ng-deep .node.selected .node-rect {
      stroke: #3b82f6;
      stroke-width: 3;
    }

    :host ::ng-deep .node:hover .node-rect {
      filter: brightness(1.1);
    }

    :host ::ng-deep .node-label {
      fill: white;
      font-size: 12px;
      font-weight: 600;
    }

    :host ::ng-deep .node-type {
      fill: rgba(255,255,255,0.7);
      font-size: 10px;
    }

    :host ::ng-deep .node-icon {
      fill: rgba(255,255,255,0.9);
      font-size: 18px;
    }

    .node-legend {
      display: flex;
      gap: 16px;
      padding: 12px 16px;
      background: white;
      border-top: 1px solid #e2e8f0;
      justify-content: center;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #64748b;
    }

    .dot {
      width: 12px;
      height: 12px;
      border-radius: 4px;
    }

    .dot.input { background: #3b82f6; }
    .dot.llm { background: #8b5cf6; }
    .dot.rag { background: #10b981; }
    .dot.tool { background: #f59e0b; }
    .dot.output { background: #ec4899; }

    .properties-content {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
    }

    .node-info {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .node-id {
      font-size: 12px;
      color: #94a3b8;
      font-family: monospace;
    }

    .full-width {
      width: 100%;
      margin-bottom: 8px;
    }

    h4 {
      margin: 16px 0 12px;
      font-size: 13px;
      color: #475569;
      font-weight: 600;
    }

    mat-chip {
      font-size: 11px !important;
    }

    mat-chip.input { background: #dbeafe !important; color: #1d4ed8 !important; }
    mat-chip.llm { background: #ede9fe !important; color: #6d28d9 !important; }
    mat-chip.rag { background: #d1fae5 !important; color: #047857 !important; }
    mat-chip.tool { background: #fef3c7 !important; color: #b45309 !important; }
    mat-chip.output { background: #fce7f3 !important; color: #be185d !important; }

    .help-section {
      display: flex;
      gap: 12px;
      padding: 16px;
      margin: 16px;
      background: #f0f9ff;
      border-radius: 8px;
      font-size: 13px;
      color: #0369a1;
    }

    .help-section mat-icon {
      color: #0284c7;
    }
  `]
})
export class ChainEditorComponent implements OnInit {
  @Input() chainId!: string;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<void>();

  private http = inject(HttpClient);
  private snackBar = inject(MatSnackBar);

  chain: ChainFull | null = null;
  selectedNode: ChainNode | null = null;
  loading = signal(true);
  saving = signal(false);
  dirty = signal(false);

  // Graph data
  graphNodes: any[] = [];
  graphLinks: any[] = [];

  // Graph controls
  center$ = new Subject<boolean>();
  zoomToFit$ = new Subject<boolean>();

  layoutSettings = {
    orientation: 'TB',
    marginX: 50,
    marginY: 50
  };

  ngOnInit(): void {
    this.loadChain();
  }

  loadChain(): void {
    this.loading.set(true);
    
    this.http.get<any>(`${environment.apiUrl}/chains/${this.chainId}/full`)
      .subscribe({
        next: (response) => {
          this.chain = response.chain;
          this.buildGraph();
          this.loading.set(false);
          
          // Center after load
          setTimeout(() => this.centerGraph(), 100);
        },
        error: (err) => {
          console.error('Error loading chain:', err);
          this.snackBar.open('Error al cargar la cadena', 'Cerrar', { duration: 3000 });
          this.loading.set(false);
        }
      });
  }

  buildGraph(): void {
    if (!this.chain) return;

    // Build nodes
    this.graphNodes = this.chain.nodes.map(node => ({
      id: node.id,
      label: node.name,
      data: { type: node.type },
      dimension: { width: 160, height: 60 }
    }));

    // Build links
    this.graphLinks = this.chain.edges.map((edge, i) => ({
      id: `link-${i}`,
      source: edge.source,
      target: edge.target,
      label: edge.condition || ''
    }));
  }

  selectNode(graphNode: any): void {
    if (!this.chain) return;
    
    const node = this.chain.nodes.find(n => n.id === graphNode.id);
    if (node) {
      this.selectedNode = { ...node };
    }
  }

  markDirty(): void {
    this.dirty.set(true);
  }

  hasChanges(): boolean {
    return this.dirty();
  }

  saveChanges(): void {
    if (!this.chain) return;

    this.saving.set(true);

    // If a node is selected, update it in the chain
    if (this.selectedNode) {
      const idx = this.chain.nodes.findIndex(n => n.id === this.selectedNode!.id);
      if (idx >= 0) {
        this.chain.nodes[idx] = { ...this.selectedNode };
      }
    }

    // Prepare update payload
    const payload = {
      name: this.chain.name,
      description: this.chain.description,
      nodes: this.chain.nodes,
      config: this.chain.config
    };

    this.http.put(`${environment.apiUrl}/chains/${this.chainId}`, payload)
      .subscribe({
        next: () => {
          this.snackBar.open('Cadena guardada correctamente', 'Cerrar', { duration: 3000 });
          this.dirty.set(false);
          this.saving.set(false);
          this.saved.emit();
        },
        error: (err) => {
          console.error('Error saving chain:', err);
          this.snackBar.open('Error al guardar. Verifica permisos en Strapi.', 'Cerrar', { duration: 5000 });
          this.saving.set(false);
        }
      });
  }

  centerGraph(): void {
    this.center$.next(true);
  }

  zoomIn(): void {
    // ngx-graph doesn't have direct zoom control, use fit
    this.zoomToFit$.next(true);
  }

  zoomOut(): void {
    // ngx-graph doesn't have direct zoom control
  }

  getNodeColor(type: string): string {
    const colors: Record<string, string> = {
      input: '#3b82f6',
      llm: '#8b5cf6',
      rag: '#10b981',
      tool: '#f59e0b',
      output: '#ec4899',
      planner: '#6366f1',
      synthesizer: '#14b8a6'
    };
    return colors[type] || '#64748b';
  }

  getNodeIconChar(type: string): string {
    const icons: Record<string, string> = {
      input: '▶',
      llm: '🧠',
      rag: '🔍',
      tool: '🔧',
      output: '◀',
      planner: '📋',
      synthesizer: '✨'
    };
    return icons[type] || '●';
  }

  getTypeIcon(): string {
    const icons: Record<string, string> = {
      conversational: 'chat',
      rag: 'search',
      tools: 'build'
    };
    return icons[this.chain?.type || ''] || 'psychology';
  }
}
