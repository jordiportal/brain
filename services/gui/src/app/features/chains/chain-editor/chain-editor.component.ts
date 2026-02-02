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
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { NgxGraphModule } from '@swimlane/ngx-graph';
import { Subject } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { StrapiService } from '../../../core/services/config.service';
import { ApiService } from '../../../core/services/api.service';
import { LlmProvider } from '../../../core/models';

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
  default_llm_provider_id?: number;
  default_llm_model?: string;
  max_iterations?: number;
  ask_before_continue?: boolean;
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

interface ToolInfo {
  id: string;
  name: string;
  description: string;
  type: string;
  category: string;
}

interface SubagentInfo {
  id: string;
  name: string;
  description: string;
  version: string;
  domain_tools: string[];
  status: string;
  icon: string;
}

interface ChainDetails {
  chain: ChainFull;
  system_prompt: string;
  tools: ToolInfo[];
  subagents: SubagentInfo[];
  default_llm: {
    provider_id: number | null;
    model: string | null;
  } | null;
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
    MatExpansionModule,
    MatTabsModule,
    MatCheckboxModule,
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
        <!-- Vista para tipo AGENT -->
        @if (isAgentType()) {
          <div class="agent-dashboard">
            <!-- Configuracion LLM -->
            <div class="llm-config-bar">
              <div class="llm-selector">
                <mat-form-field appearance="outline">
                  <mat-label>Proveedor LLM por defecto</mat-label>
                  <mat-select [(ngModel)]="selectedProviderId" (selectionChange)="onProviderChange()">
                    @for (provider of llmProviders(); track provider.id) {
                      <mat-option [value]="provider.id">
                        {{ provider.name }} ({{ provider.type }})
                      </mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                
                <mat-form-field appearance="outline">
                  <mat-label>Modelo por defecto</mat-label>
                  <mat-select [(ngModel)]="selectedModel" (selectionChange)="markDirty()" [disabled]="loadingModels()">
                    @if (loadingModels()) {
                      <mat-option disabled>Cargando...</mat-option>
                    }
                    @for (model of availableModels(); track model) {
                      <mat-option [value]="model">{{ model }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
              </div>
            </div>

            <div class="dashboard-content">
              <!-- Panel izquierdo: System Prompt -->
              <div class="prompt-panel">
                <div class="panel-header">
                  <h3>
                    <mat-icon>description</mat-icon>
                    System Prompt
                  </h3>
                  <div class="prompt-actions">
                    <button mat-icon-button matTooltip="Expandir" (click)="expandPrompt = !expandPrompt">
                      <mat-icon>{{ expandPrompt ? 'fullscreen_exit' : 'fullscreen' }}</mat-icon>
                    </button>
                  </div>
                </div>
                <div class="prompt-editor" [class.expanded]="expandPrompt">
                  <textarea 
                    [(ngModel)]="systemPrompt" 
                    (ngModelChange)="markDirty()"
                    placeholder="Define el comportamiento del agente..."
                    class="prompt-textarea"></textarea>
                </div>
                <div class="prompt-stats">
                  <span>{{ systemPrompt.length }} caracteres</span>
                  <span>{{ systemPrompt.split('\\n').length }} lineas</span>
                </div>
              </div>

              <!-- Panel derecho: Tools y Subagentes -->
              <div class="info-panels">
                <!-- Tools Section -->
                <mat-card class="tools-section">
                  <mat-card-header>
                    <mat-icon mat-card-avatar>build</mat-icon>
                    <mat-card-title>Core Tools ({{ tools().length }})</mat-card-title>
                    <mat-card-subtitle>Herramientas disponibles para el agente</mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="tools-grid">
                      @for (tool of tools(); track tool.id) {
                        <div class="tool-item" [matTooltip]="tool.description">
                          <mat-icon>{{ getToolIcon(tool.type) }}</mat-icon>
                          <span class="tool-name">{{ tool.name }}</span>
                        </div>
                      }
                    </div>
                  </mat-card-content>
                </mat-card>

                <!-- Subagents Section -->
                <mat-card class="subagents-section">
                  <mat-card-header>
                    <mat-icon mat-card-avatar>smart_toy</mat-icon>
                    <mat-card-title>Subagentes ({{ subagents().length }})</mat-card-title>
                    <mat-card-subtitle>Agentes especializados para delegacion</mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    @if (subagents().length > 0) {
                      <div class="subagents-list">
                        @for (agent of subagents(); track agent.id) {
                          <div class="subagent-item" [class]="agent.status">
                            <mat-icon>{{ agent.icon }}</mat-icon>
                            <div class="subagent-info">
                              <span class="subagent-name">{{ agent.name }}</span>
                              <span class="subagent-desc">{{ agent.description }}</span>
                            </div>
                            <mat-chip class="status-chip" [class]="agent.status">
                              {{ agent.status }}
                            </mat-chip>
                          </div>
                        }
                      </div>
                    } @else {
                      <div class="empty-subagents">
                        <mat-icon>info</mat-icon>
                        <span>No hay subagentes registrados</span>
                      </div>
                    }
                  </mat-card-content>
                </mat-card>

                <!-- Config Section -->
                <mat-card class="config-section">
                  <mat-card-header>
                    <mat-icon mat-card-avatar>settings</mat-icon>
                    <mat-card-title>Configuracion</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="config-grid">
                      <mat-form-field appearance="outline">
                        <mat-label>Temperatura</mat-label>
                        <input matInput type="number" step="0.1" min="0" max="2"
                               [(ngModel)]="chain!.config.temperature" 
                               (ngModelChange)="markDirty()">
                      </mat-form-field>
                      
                      <mat-form-field appearance="outline">
                        <mat-label>Max Memory Messages</mat-label>
                        <input matInput type="number" 
                               [(ngModel)]="chain!.config.max_memory_messages" 
                               (ngModelChange)="markDirty()">
                      </mat-form-field>
                    </div>
                    
                    <mat-divider></mat-divider>
                    
                    <h4 class="config-subtitle">Control de Iteraciones</h4>
                    <p class="config-hint">Define cuantas iteraciones puede hacer el agente antes de preguntar si continuar</p>
                    
                    <div class="config-grid">
                      <mat-form-field appearance="outline">
                        <mat-label>Max Iteraciones</mat-label>
                        <input matInput type="number" min="5" max="50"
                               [(ngModel)]="chain!.config.max_iterations" 
                               (ngModelChange)="markDirty()">
                        <mat-hint>5-50 iteraciones</mat-hint>
                      </mat-form-field>
                      
                      <div class="checkbox-field">
                        <mat-checkbox 
                               [(ngModel)]="chain!.config.ask_before_continue" 
                               (ngModelChange)="markDirty()">
                          Preguntar antes de continuar
                        </mat-checkbox>
                        <span class="checkbox-hint">Si esta activo, pregunta al usuario cuando alcance el limite</span>
                      </div>
                    </div>
                  </mat-card-content>
                </mat-card>
              </div>
            </div>
          </div>
        } @else {
          <!-- Vista de GRAFO para otros tipos -->
          <div class="editor-content">
            <!-- Graph Panel -->
            <div class="graph-panel">
              <div class="panel-header">
                <h3>
                  <mat-icon>account_tree</mat-icon>
                  Grafo de Ejecucion
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
                    </svg:g>
                  </ng-template>

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

                <svg style="position: absolute; width: 0; height: 0;">
                  <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
                            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/>
                    </marker>
                  </defs>
                </svg>
              </div>

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
                    </mat-form-field>
                  }
                </div>
              } @else {
                <div class="panel-header">
                  <h3>
                    <mat-icon>settings</mat-icon>
                    Configuracion de Cadena
                  </h3>
                </div>

                <div class="properties-content">
                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Nombre</mat-label>
                    <input matInput [(ngModel)]="chain!.name" (ngModelChange)="markDirty()">
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Descripcion</mat-label>
                    <textarea matInput 
                              [(ngModel)]="chain!.description" 
                              (ngModelChange)="markDirty()"
                              rows="3"></textarea>
                  </mat-form-field>

                  <mat-divider></mat-divider>

                  <h4>Parametros de Ejecucion</h4>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Temperatura</mat-label>
                    <input matInput type="number" step="0.1" min="0" max="2"
                           [(ngModel)]="chain!.config.temperature" 
                           (ngModelChange)="markDirty()">
                  </mat-form-field>

                  <mat-form-field appearance="outline" class="full-width">
                    <mat-label>Max Memory Messages</mat-label>
                    <input matInput type="number" 
                           [(ngModel)]="chain!.config.max_memory_messages" 
                           (ngModelChange)="markDirty()">
                  </mat-form-field>
                </div>
              }

              <div class="help-section">
                <mat-icon>info</mat-icon>
                <div>
                  <strong>Tip:</strong> Haz clic en un nodo del grafo para editar sus propiedades.
                </div>
              </div>
            </div>
          </div>
        }
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
    .type-icon.agent { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }

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

    /* Agent Dashboard Styles */
    .agent-dashboard {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .llm-config-bar {
      padding: 12px 24px;
      background: white;
      border-bottom: 1px solid #e2e8f0;
    }

    .llm-selector {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .llm-selector mat-form-field {
      min-width: 200px;
    }

    .dashboard-content {
      flex: 1;
      display: flex;
      gap: 24px;
      padding: 24px;
      overflow: hidden;
    }

    .prompt-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      overflow: hidden;
    }

    .prompt-panel .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid #e2e8f0;
    }

    .prompt-panel .panel-header h3 {
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 600;
      color: #334155;
    }

    .prompt-editor {
      flex: 1;
      padding: 16px;
      overflow: hidden;
    }

    .prompt-editor.expanded {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 1000;
      background: white;
      padding: 24px;
    }

    .prompt-textarea {
      width: 100%;
      height: 100%;
      min-height: 400px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 13px;
      line-height: 1.6;
      resize: none;
      background: #f8fafc;
    }

    .prompt-textarea:focus {
      outline: none;
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    .prompt-stats {
      display: flex;
      gap: 16px;
      padding: 8px 16px;
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
    }

    .info-panels {
      width: 400px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      overflow-y: auto;
    }

    .tools-section, .subagents-section, .config-section {
      border-radius: 12px;
    }

    .tools-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
    }

    .tool-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #f1f5f9;
      border-radius: 8px;
      cursor: default;
    }

    .tool-item mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #667eea;
    }

    .tool-name {
      font-size: 12px;
      font-weight: 500;
      color: #334155;
    }

    .subagents-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .subagent-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #f8fafc;
      border-radius: 8px;
      border-left: 3px solid #e2e8f0;
    }

    .subagent-item.active {
      border-left-color: #10b981;
    }

    .subagent-item.coming_soon {
      border-left-color: #f59e0b;
      opacity: 0.7;
    }

    .subagent-item mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
      color: #667eea;
    }

    .subagent-info {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .subagent-name {
      font-weight: 600;
      font-size: 13px;
      color: #1e293b;
    }

    .subagent-desc {
      font-size: 11px;
      color: #64748b;
    }

    .status-chip {
      font-size: 10px !important;
      min-height: 20px !important;
      padding: 0 8px !important;
    }

    .status-chip.active {
      background: #d1fae5 !important;
      color: #047857 !important;
    }

    .status-chip.coming_soon {
      background: #fef3c7 !important;
      color: #b45309 !important;
    }

    .empty-subagents {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px;
      color: #64748b;
      font-size: 13px;
    }

    .config-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }

    .config-subtitle {
      margin: 16px 0 4px;
      font-size: 13px;
      font-weight: 600;
      color: #475569;
    }

    .config-hint {
      margin: 0 0 12px;
      font-size: 12px;
      color: #94a3b8;
    }

    .checkbox-field {
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 4px;
    }

    .checkbox-hint {
      font-size: 11px;
      color: #94a3b8;
      margin-left: 32px;
    }

    /* Graph styles (existing) */
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

    :host ::ng-deep .node-label {
      fill: white;
      font-size: 12px;
      font-weight: 600;
    }

    :host ::ng-deep .node-type {
      fill: rgba(255,255,255,0.7);
      font-size: 10px;
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
  private strapiService = inject(StrapiService);
  private apiService = inject(ApiService);

  chain: ChainFull | null = null;
  selectedNode: ChainNode | null = null;
  loading = signal(true);
  saving = signal(false);
  dirty = signal(false);

  // Agent dashboard data
  systemPrompt = '';
  tools = signal<ToolInfo[]>([]);
  subagents = signal<SubagentInfo[]>([]);
  expandPrompt = false;

  // LLM config
  llmProviders = signal<LlmProvider[]>([]);
  availableModels = signal<string[]>([]);
  selectedProviderId: number | null = null;
  selectedModel: string = '';
  loadingModels = signal(false);

  // Graph data
  graphNodes: any[] = [];
  graphLinks: any[] = [];
  center$ = new Subject<boolean>();
  zoomToFit$ = new Subject<boolean>();
  layoutSettings = {
    orientation: 'TB',
    marginX: 50,
    marginY: 50
  };

  ngOnInit(): void {
    this.loadChain();
    this.loadLlmProviders();
  }

  isAgentType(): boolean {
    return this.chain?.type === 'agent';
  }

  loadChain(): void {
    this.loading.set(true);
    
    // Usar el nuevo endpoint /details para agentes
    this.http.get<ChainDetails>(`${environment.apiUrl}/chains/${this.chainId}/details`)
      .subscribe({
        next: (response) => {
          this.chain = response.chain;
          this.systemPrompt = response.system_prompt || '';
          this.tools.set(response.tools || []);
          this.subagents.set(response.subagents || []);
          
          // Configurar LLM por defecto
          if (response.default_llm) {
            this.selectedProviderId = response.default_llm.provider_id;
            this.selectedModel = response.default_llm.model || '';
          }
          
          this.buildGraph();
          this.loading.set(false);
          
          setTimeout(() => this.centerGraph(), 100);
        },
        error: (err) => {
          console.error('Error loading chain details:', err);
          // Fallback al endpoint anterior
          this.loadChainFallback();
        }
      });
  }

  loadChainFallback(): void {
    this.http.get<any>(`${environment.apiUrl}/chains/${this.chainId}/full`)
      .subscribe({
        next: (response) => {
          this.chain = response.chain;
          
          // Extraer system prompt del primer nodo
          if (this.chain && this.chain.nodes && this.chain.nodes.length > 0) {
            this.systemPrompt = this.chain.nodes[0]?.system_prompt || '';
          }
          
          this.buildGraph();
          this.loading.set(false);
          
          setTimeout(() => this.centerGraph(), 100);
        },
        error: (err) => {
          console.error('Error loading chain:', err);
          this.snackBar.open('Error al cargar la cadena', 'Cerrar', { duration: 3000 });
          this.loading.set(false);
        }
      });
  }

  loadLlmProviders(): void {
    this.strapiService.getLlmProviders().subscribe({
      next: (providers) => {
        this.llmProviders.set(providers);
        
        // Si hay un proveedor seleccionado, cargar sus modelos
        if (this.selectedProviderId) {
          const provider = providers.find(p => p.id === this.selectedProviderId);
          if (provider) {
            this.loadModelsForProvider(provider);
          }
        } else if (providers.length > 0) {
          // Seleccionar el primer proveedor activo
          const activeProvider = providers.find(p => p.isActive) || providers[0];
          this.selectedProviderId = activeProvider.id;
          this.loadModelsForProvider(activeProvider);
        }
      },
      error: (err) => {
        console.error('Error loading LLM providers:', err);
      }
    });
  }

  onProviderChange(): void {
    const provider = this.llmProviders().find(p => p.id === this.selectedProviderId);
    if (provider) {
      this.loadModelsForProvider(provider);
      this.markDirty();
    }
  }

  loadModelsForProvider(provider: LlmProvider): void {
    this.loadingModels.set(true);
    this.availableModels.set([]);
    
    this.apiService.getLlmModels({
      providerUrl: provider.baseUrl,
      providerType: provider.type,
      apiKey: provider.apiKey
    }).subscribe({
      next: (response) => {
        const models = response.models?.map(m => m.name) || [];
        this.availableModels.set(models);
        
        // Seleccionar modelo por defecto si no hay uno seleccionado
        if (!this.selectedModel && models.length > 0) {
          this.selectedModel = provider.defaultModel && models.includes(provider.defaultModel) 
            ? provider.defaultModel 
            : models[0];
        }
        
        this.loadingModels.set(false);
      },
      error: (err) => {
        console.error('Error loading models:', err);
        // Fallback al modelo por defecto del proveedor
        if (provider.defaultModel) {
          this.availableModels.set([provider.defaultModel]);
          this.selectedModel = provider.defaultModel;
        }
        this.loadingModels.set(false);
      }
    });
  }

  buildGraph(): void {
    if (!this.chain) return;

    this.graphNodes = (this.chain.nodes || []).map(node => ({
      id: node.id,
      label: node.name,
      data: { type: node.type },
      dimension: { width: 160, height: 60 }
    }));

    this.graphLinks = (this.chain.edges || []).map((edge, i) => ({
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

    // Si es tipo agent, guardar la configuración de LLM
    if (this.isAgentType()) {
      this.saveLlmConfig();
      this.saveSystemPrompt();
    }

    // Si hay un nodo seleccionado, actualizarlo
    if (this.selectedNode) {
      const idx = this.chain.nodes.findIndex(n => n.id === this.selectedNode!.id);
      if (idx >= 0) {
        this.chain.nodes[idx] = { ...this.selectedNode };
      }
    }

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
          this.snackBar.open('Error al guardar la cadena', 'Cerrar', { duration: 5000 });
          this.saving.set(false);
        }
      });
  }

  saveLlmConfig(): void {
    if (!this.selectedProviderId) return;

    this.http.put(`${environment.apiUrl}/chains/${this.chainId}/llm-config`, {
      provider_id: this.selectedProviderId,
      model: this.selectedModel
    }).subscribe({
      next: () => {
        console.log('LLM config saved');
      },
      error: (err) => {
        console.error('Error saving LLM config:', err);
      }
    });
  }

  saveSystemPrompt(): void {
    if (!this.systemPrompt) return;

    this.http.put(`${environment.apiUrl}/chains/${this.chainId}/prompt`, {
      system_prompt: this.systemPrompt
    }).subscribe({
      next: () => {
        console.log('System prompt saved');
      },
      error: (err) => {
        console.error('Error saving system prompt:', err);
      }
    });
  }

  centerGraph(): void {
    this.center$.next(true);
  }

  zoomIn(): void {
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

  getTypeIcon(): string {
    const icons: Record<string, string> = {
      conversational: 'chat',
      rag: 'search',
      tools: 'build',
      agent: 'psychology'
    };
    return icons[this.chain?.type || ''] || 'psychology';
  }

  getToolIcon(type: string): string {
    const icons: Record<string, string> = {
      builtin: 'extension',
      filesystem: 'folder',
      execution: 'terminal',
      web: 'language',
      reasoning: 'psychology',
      utils: 'calculate',
      delegation: 'share'
    };
    return icons[type] || 'extension';
  }
}
