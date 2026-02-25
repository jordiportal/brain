import { 
  Component, 
  Input, 
  Output, 
  EventEmitter, 
  ViewChild, 
  ElementRef,
  ChangeDetectionStrategy,
  Signal,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeUrl } from '@angular/platform-browser';

import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { 
  ChatMessage, 
  ChatFeatures, 
  IntermediateStep,
  ImageData,
  VideoData,
  ChatAttachment
} from './chat-message.interface';
import { MarkdownPipe } from './markdown.pipe';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MarkdownPipe
  ],
  template: `
    <div class="chat-container" #chatContainer>
      <div class="messages-area">
        @if (messages().length === 0) {
          <div class="empty-chat">
            <mat-icon>chat</mat-icon>
            <p>{{ emptyMessage }}</p>
          </div>
        }

        @for (msg of messages(); track $index) {
          <div class="message" [class]="msg.role">
            <div class="message-avatar">
              <mat-icon>{{ msg.role === 'user' ? 'person' : 'smart_toy' }}</mat-icon>
            </div>
            <div class="message-content">
              @if (features.timestamps && msg.timestamp) {
                <div class="message-header">
                  <span class="message-role">{{ msg.role === 'user' ? 'Tú' : 'Asistente' }}</span>
                  <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
                </div>
              }

              @if (msg.role === 'user') {
                <div class="message-text">{{ msg.content }}</div>
                @if (msg.attachments && msg.attachments.length > 0) {
                  <div class="message-attachments">
                    @for (att of msg.attachments; track att.name) {
                      <div class="attachment-chip">
                        <mat-icon>{{ getFileIcon(att.name) }}</mat-icon>
                        <span>{{ att.name }}</span>
                        <span class="att-size">{{ formatSize(att.size) }}</span>
                      </div>
                    }
                  </div>
                }
              } @else {

                <!-- Pasos intermedios (inline) -->
                @if (features.intermediateSteps && msg.intermediateSteps && msg.intermediateSteps.length > 0) {
                  <div class="steps-container">
                    <button class="steps-toggle" (click)="toggleAllSteps($index)">
                      <mat-icon class="toggle-icon">{{ isMessageExpanded($index) ? 'unfold_less' : 'unfold_more' }}</mat-icon>
                      <span>{{ msg.intermediateSteps.length }} {{ msg.intermediateSteps.length === 1 ? 'paso' : 'pasos' }}</span>
                      @if (!msg.isStreaming && msg.intermediateSteps.length > 0) {
                        <span class="steps-total-time">{{ totalDuration(msg) }}</span>
                      }
                    </button>

                    @if (isMessageExpanded($index)) {
                      <div class="steps-list">
                        @for (step of msg.intermediateSteps; track step.id) {
                          @if (step.type === 'subtask') {
                            <!-- SubTask block -->
                            <div class="subtask-block" [class.subtask-running]="step.status === 'running'"
                                 [class.subtask-completed]="step.status === 'completed'"
                                 [class.subtask-failed]="step.status === 'failed'">
                              <div class="subtask-header" (click)="toggleStep(step.id)">
                                @if (step.status === 'running') {
                                  <mat-spinner diameter="14"></mat-spinner>
                                } @else {
                                  <mat-icon class="subtask-icon" [class]="'si-' + step.status">account_tree</mat-icon>
                                }
                                @if (step.agentType) {
                                  <span class="subtask-agent">{{ step.agentType }}</span>
                                }
                                <span class="subtask-name">{{ step.name }}</span>
                                @if (step.toolCount) {
                                  <span class="step-badge">{{ step.toolCount }} tools</span>
                                }
                                @if (step.status === 'completed' && step.endTime && step.startTime) {
                                  <span class="step-dur">{{ getDuration(step.startTime, step.endTime) }}</span>
                                }
                                @if (step.status === 'running') {
                                  <span class="step-running-text">En progreso...</span>
                                }
                              </div>

                              <!-- Children anidados -->
                              @if (isStepExpanded(step.id) && step.children && step.children.length > 0) {
                                <div class="subtask-children">
                                  @for (child of step.children; track child.id) {
                                    <div class="inline-step" [class]="'is-' + child.status"
                                         (click)="toggleStep(child.id); $event.stopPropagation()">
                                      <span class="step-indicator">
                                        @if (child.status === 'running') {
                                          <mat-spinner diameter="12"></mat-spinner>
                                        } @else {
                                          <mat-icon [class]="'si-' + child.status">{{ child.icon }}</mat-icon>
                                        }
                                      </span>
                                      <span class="step-label">{{ child.name }}</span>
                                      @if (child.status === 'completed' && child.endTime && child.startTime) {
                                        <span class="step-dur">{{ getDuration(child.startTime, child.endTime) }}</span>
                                      }
                                      @if (child.status === 'running') {
                                        <span class="step-running-text">En progreso...</span>
                                      }
                                    </div>
                                    @if (isStepExpanded(child.id) && child.content) {
                                      <div class="step-detail" [innerHTML]="child.content | markdown"></div>
                                    }
                                  }
                                </div>
                              }

                              <!-- Contenido del subtask -->
                              @if (isStepExpanded(step.id) && step.content && (!step.children || step.children.length === 0)) {
                                <div class="step-detail" [innerHTML]="step.content | markdown"></div>
                              }
                            </div>
                          } @else {
                            <!-- InlineStep (tool, thinking, generic) -->
                            <div class="inline-step" [class]="'is-' + step.status"
                                 (click)="toggleStep(step.id)">
                              <span class="step-indicator">
                                @if (step.status === 'running') {
                                  <mat-spinner diameter="12"></mat-spinner>
                                } @else {
                                  <mat-icon [class]="'si-' + step.status">{{ step.icon }}</mat-icon>
                                }
                              </span>
                              <span class="step-label">{{ step.name }}</span>
                              @if (step.status === 'completed' && step.endTime && step.startTime) {
                                <span class="step-dur">{{ getDuration(step.startTime, step.endTime) }}</span>
                              }
                              @if (step.status === 'running') {
                                <span class="step-running-text">En progreso...</span>
                              }
                            </div>
                            @if (isStepExpanded(step.id) && step.content) {
                              <div class="step-detail" [innerHTML]="step.content | markdown"></div>
                            }
                          }
                        }
                      </div>
                    }
                  </div>
                }

                <!-- Respuesta del assistant -->
                @if (msg.content) {
                  <div class="markdown-content" [innerHTML]="msg.content | markdown"></div>

                  @if (features.presentations && getPresentationHtml(msg)) {
                    <div class="presentation-viewer">
                      <button mat-stroked-button color="primary" (click)="openPresentation(getPresentationHtml(msg)!)">
                        <mat-icon>slideshow</mat-icon>
                        Ver presentación
                      </button>
                    </div>
                  }
                }

                <!-- Imágenes generadas -->
                @if (features.images && msg.images && msg.images.length > 0) {
                  <div class="generated-images">
                    @for (img of msg.images; track $index) {
                      <img 
                        [src]="sanitizeImageUrl(img)"
                        [alt]="img.altText"
                        class="generated-image"
                        loading="lazy"
                      />
                    }
                  </div>
                }

                <!-- Vídeos generados -->
                @if (features.videos && msg.videos && msg.videos.length > 0) {
                  <div class="generated-videos">
                    @for (video of msg.videos; track $index) {
                      <video 
                        [src]="sanitizeVideoUrl(video)"
                        class="generated-video"
                        controls autoplay loop muted>
                        Tu navegador no soporta vídeos HTML5.
                      </video>
                      @if (video.duration || video.resolution) {
                        <div class="video-info">
                          @if (video.duration) { <span>{{ video.duration }}s</span> }
                          @if (video.resolution) { <span>{{ video.resolution }}</span> }
                        </div>
                      }
                    }
                  </div>
                }

                <!-- Streaming cursor + iteration badge -->
                @if (features.streaming && msg.isStreaming) {
                  <span class="cursor-blink">▊</span>
                  @if (msg.currentIteration) {
                    <span class="iteration-badge">{{ msg.currentIteration }}/{{ msg.maxIterations }}</span>
                  }
                }

                <!-- Tokens -->
                @if (features.tokens && msg.tokens) {
                  <span class="token-count">{{ msg.tokens }} tokens</span>
                }
              }
            </div>
          </div>
        }

        <!-- Typing indicator -->
        @if (isLoading() && !hasStreamingMessage()) {
          <div class="message assistant">
            <div class="message-avatar">
              <mat-icon>smart_toy</mat-icon>
            </div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
              @if (currentStepName()) {
                <div class="current-step">
                  <mat-icon>{{ getStepIcon(currentStepName()!) }}</mat-icon>
                  {{ currentStepName() }}
                </div>
              }
            </div>
          </div>
        }
      </div>

      <!-- Pending attachments preview -->
      @if (pendingFiles.length > 0) {
        <div class="pending-attachments">
          @for (pf of pendingFiles; track pf.name) {
            <div class="pending-file" [class.uploading]="pf.uploadStatus === 'uploading'">
              <mat-icon>{{ getFileIcon(pf.name) }}</mat-icon>
              <span class="pf-name">{{ pf.name }}</span>
              <span class="pf-size">{{ formatSize(pf.size) }}</span>
              <button mat-icon-button class="pf-remove" (click)="removePendingFile(pf)">
                <mat-icon>close</mat-icon>
              </button>
            </div>
          }
        </div>
      }

      <!-- Input area -->
      <div class="input-area">
        @if (features.attachments) {
          <input type="file" #fileAttach (change)="onFilesSelected($event)" multiple style="display:none">
          <button mat-icon-button matTooltip="Adjuntar archivo" (click)="fileAttach.click()" [disabled]="isLoading()">
            <mat-icon>attach_file</mat-icon>
          </button>
        }
        <mat-form-field appearance="outline" class="message-input">
          <textarea matInput 
                    [(ngModel)]="newMessageText" 
                    [placeholder]="placeholder"
                    (keydown.enter)="$event.preventDefault(); sendMessage()"
                    [disabled]="isLoading()"
                    rows="1">
          </textarea>
        </mat-form-field>
        <button mat-fab color="primary" 
                (click)="sendMessage()" 
                [disabled]="isLoading() || (!newMessageText.trim() && pendingFiles.length === 0)">
          @if (isLoading()) {
            <mat-spinner diameter="24" color="accent"></mat-spinner>
          } @else {
            <mat-icon>send</mat-icon>
          }
        </button>
      </div>

      @if (features.clearButton && messages().length > 0) {
        <div class="chat-actions">
          <button mat-button color="warn" (click)="clearChat()">
            <mat-icon>delete_sweep</mat-icon>
            Limpiar chat
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .chat-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: white;
      border-radius: 12px;
      overflow: hidden;
    }

    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .empty-chat {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #999;
      padding: 64px;
    }

    .empty-chat mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
      margin-bottom: 16px;
    }

    /* Messages */
    .message {
      display: flex;
      gap: 12px;
      max-width: 90%;
    }

    .message.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }

    .message-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .message.user .message-avatar {
      background: #667eea;
      color: white;
    }

    .message.assistant .message-avatar {
      background: #e8f5e9;
      color: #2e7d32;
    }

    .message-content {
      background: #f5f5f5;
      padding: 12px 16px;
      border-radius: 16px;
      min-width: 60px;
      max-width: 100%;
    }

    .message.user .message-content {
      background: #667eea;
      color: white;
      border-bottom-right-radius: 4px;
    }

    .message.assistant .message-content {
      background: transparent;
      padding: 0;
      border-radius: 0;
    }

    .message-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      font-size: 12px;
      margin-bottom: 4px;
      opacity: 0.7;
    }

    .message-text {
      word-break: break-word;
      line-height: 1.6;
    }

    /* ===== Steps container ===== */
    .steps-container {
      margin-bottom: 12px;
    }

    .steps-toggle {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 12px;
      color: #888;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background 0.15s;
    }

    .steps-toggle:hover {
      background: #f0f0f0;
    }

    .toggle-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .steps-total-time {
      margin-left: 4px;
      padding: 1px 6px;
      background: #f0f0f0;
      border-radius: 8px;
      font-size: 11px;
    }

    .steps-list {
      padding: 4px 0 4px 4px;
    }

    /* ===== Inline step (tool / thinking / generic) ===== */
    .inline-step {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 3px 8px;
      font-size: 13px;
      cursor: pointer;
      border-radius: 4px;
      transition: background 0.15s;
      user-select: none;
    }

    .inline-step:hover {
      background: #f5f5f5;
    }

    .step-indicator {
      display: flex;
      align-items: center;
      flex-shrink: 0;
    }

    .step-indicator mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .si-completed { color: #4caf50; }
    .si-failed { color: #f44336; }
    .si-running { color: #2196f3; }

    .step-label {
      flex: 1;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .is-completed .step-label { color: #666; }
    .is-failed .step-label { color: #d32f2f; }
    .is-running .step-label { color: #1565c0; }

    .step-dur {
      flex-shrink: 0;
      font-size: 11px;
      color: #999;
      padding: 1px 6px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .step-running-text {
      flex-shrink: 0;
      font-size: 11px;
      color: #2196f3;
      font-style: italic;
    }

    .step-badge {
      flex-shrink: 0;
      font-size: 10px;
      color: #666;
      padding: 1px 5px;
      background: #e8e8e8;
      border-radius: 6px;
    }

    .step-detail {
      padding: 6px 12px 6px 32px;
      font-size: 13px;
      line-height: 1.5;
      background: #f8f9fa;
      border-radius: 4px;
      margin: 2px 0 6px;
      border-left: 2px solid #ddd;
      color: #444;
    }

    .step-detail ::ng-deep {
      p { margin: 0 0 8px; }
      p:last-child { margin-bottom: 0; }
      pre {
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 8px;
        border-radius: 6px;
        overflow-x: auto;
        font-size: 12px;
      }
      code {
        background: rgba(0,0,0,0.07);
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 12px;
      }
    }

    /* ===== SubTask block ===== */
    .subtask-block {
      margin: 4px 0;
      padding: 6px 10px;
      border-left: 3px solid #667eea;
      border-radius: 4px;
      background: rgba(102, 126, 234, 0.03);
      cursor: pointer;
      transition: background 0.15s;
    }

    .subtask-block:hover {
      background: rgba(102, 126, 234, 0.07);
    }

    .subtask-running { border-left-color: #2196f3; background: rgba(33, 150, 243, 0.04); }
    .subtask-completed { border-left-color: #4caf50; }
    .subtask-failed { border-left-color: #f44336; }

    .subtask-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }

    .subtask-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }

    .subtask-agent {
      font-weight: 600;
      font-size: 12px;
      color: #667eea;
      padding: 1px 6px;
      background: rgba(102, 126, 234, 0.1);
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .subtask-name {
      flex: 1;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #555;
    }

    .subtask-children {
      padding: 4px 0 2px 8px;
      border-left: 1px dashed #ddd;
      margin-left: 7px;
      margin-top: 4px;
    }

    /* ===== Iteration badge ===== */
    .iteration-badge {
      display: inline-block;
      font-size: 11px;
      color: #999;
      background: #f0f0f0;
      padding: 1px 6px;
      border-radius: 8px;
      margin-left: 8px;
      vertical-align: middle;
    }

    /* ===== Markdown content ===== */
    .markdown-content {
      line-height: 1.6;
    }

    .markdown-content ::ng-deep {
      p { margin: 0 0 12px; }
      p:last-child { margin-bottom: 0; }
      
      pre {
        background: #1a1a2e;
        color: #e0e0e0;
        padding: 12px;
        border-radius: 8px;
        overflow-x: auto;
      }
      
      code {
        background: rgba(0,0,0,0.1);
        padding: 2px 6px;
        border-radius: 4px;
      }
      
      table {
        border-collapse: collapse;
        width: 100%;
        margin: 12px 0;
      }
      
      th, td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
      }
      
      th {
        background: #f5f5f5;
        font-weight: 600;
      }
    }

    /* ===== Presentation ===== */
    .presentation-viewer {
      margin: 12px 0;
    }

    /* ===== Images & videos ===== */
    .generated-images {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .generated-image {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .generated-videos {
      margin-top: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .generated-video {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .video-info {
      display: flex;
      gap: 8px;
      font-size: 12px;
      color: #888;
      margin-top: 4px;
    }

    /* ===== Cursor & tokens ===== */
    .cursor-blink {
      animation: blink 1s infinite;
      color: #667eea;
      font-weight: bold;
    }

    @keyframes blink {
      0%, 50% { opacity: 1; }
      51%, 100% { opacity: 0; }
    }

    .token-count {
      display: block;
      font-size: 11px;
      color: #888;
      margin-top: 12px;
      text-align: right;
    }

    /* ===== Typing indicator ===== */
    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 0;
    }

    .typing-indicator span {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #999;
      animation: typing 1.4s infinite ease-in-out both;
    }

    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

    @keyframes typing {
      0%, 80%, 100% { transform: scale(0); }
      40% { transform: scale(1); }
    }

    .current-step {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #666;
      margin-top: 8px;
    }

    /* ===== Input area ===== */
    .input-area {
      display: flex;
      gap: 12px;
      padding: 16px;
      border-top: 1px solid #eee;
      align-items: flex-end;
    }

    .message-input {
      flex: 1;
    }

    .message-input textarea {
      min-height: 40px;
      max-height: 120px;
      resize: none;
    }

    .chat-actions {
      display: flex;
      justify-content: flex-end;
      padding: 8px 16px;
      border-top: 1px solid #f0f0f0;
      background: #fafafa;
    }

    /* ===== Attachments in user messages ===== */
    .message-attachments {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }

    .attachment-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 10px;
      background: rgba(255,255,255,0.2);
      border-radius: 12px;
      font-size: 12px;
    }

    .attachment-chip mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
    }

    .att-size {
      opacity: 0.7;
      font-size: 11px;
    }

    /* ===== Pending attachments bar ===== */
    .pending-attachments {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px 16px;
      border-top: 1px solid #eee;
      background: #fafafa;
    }

    .pending-file {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px 4px 10px;
      background: #e8eaf6;
      border-radius: 8px;
      font-size: 13px;
      transition: opacity 0.2s;
    }

    .pending-file.uploading {
      opacity: 0.6;
    }

    .pending-file mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: #5c6bc0;
    }

    .pf-name {
      max-width: 180px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .pf-size {
      font-size: 11px;
      color: #888;
    }

    .pf-remove {
      width: 20px !important;
      height: 20px !important;
      line-height: 20px !important;
    }

    .pf-remove mat-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
      color: #999;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChatComponent {
  @ViewChild('chatContainer') chatContainer!: ElementRef;

  @Input() messages: Signal<ChatMessage[]> = signal([]);
  @Input() features: ChatFeatures = {
    intermediateSteps: false,
    images: true,
    videos: true,
    presentations: false,
    streaming: true,
    tokens: true,
    timestamps: false,
    clearButton: true,
    configPanel: false
  };
  @Input() isLoading: Signal<boolean> = signal(false);
  @Input() placeholder = 'Escribe un mensaje...';
  @Input() emptyMessage = 'Envía un mensaje para comenzar';
  @Input() currentStepName: Signal<string | null> = signal(null);

  @Output() messageSent = new EventEmitter<string>();
  @Output() messageWithAttachments = new EventEmitter<{message: string; attachments: ChatAttachment[]}>();
  @Output() chatCleared = new EventEmitter<void>();
  @Output() presentationOpened = new EventEmitter<string>();

  newMessageText = '';
  pendingFiles: ChatAttachment[] = [];

  private expandedMessages = new Set<number>();
  private expandedSteps = new Set<string>();

  constructor(private sanitizer: DomSanitizer) {}

  // --- Expansion state ---

  isMessageExpanded(index: number): boolean {
    const msgs = this.messages();
    const msg = msgs[index];
    if (msg?.isStreaming) return true;
    if (this.expandedMessages.has(index)) return true;
    if (!msg?.isStreaming && msg?.intermediateSteps?.length && !this.expandedMessages.has(-index - 1)) {
      return false;
    }
    return false;
  }

  toggleAllSteps(index: number): void {
    if (this.isMessageExpanded(index)) {
      this.expandedMessages.delete(index);
      this.expandedMessages.add(-index - 1);
    } else {
      this.expandedMessages.add(index);
      this.expandedMessages.delete(-index - 1);
    }
  }

  isStepExpanded(stepId: string): boolean {
    return this.expandedSteps.has(stepId);
  }

  toggleStep(stepId: string): void {
    if (this.expandedSteps.has(stepId)) {
      this.expandedSteps.delete(stepId);
    } else {
      this.expandedSteps.add(stepId);
    }
  }

  // --- Helpers ---

  sendMessage(): void {
    const hasText = this.newMessageText.trim().length > 0;
    const hasFiles = this.pendingFiles.length > 0;
    if ((!hasText && !hasFiles) || this.isLoading()) return;

    const message = this.newMessageText.trim();
    this.newMessageText = '';

    if (hasFiles) {
      const attachments = [...this.pendingFiles];
      this.pendingFiles = [];
      this.messageWithAttachments.emit({ message, attachments });
    } else {
      this.messageSent.emit(message);
    }
    this.scrollToBottom();
  }

  onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files) return;
    for (let i = 0; i < input.files.length; i++) {
      const file = input.files[i];
      this.pendingFiles.push({
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        uploadStatus: 'pending'
      });
    }
    input.value = '';
  }

  removePendingFile(att: ChatAttachment): void {
    this.pendingFiles = this.pendingFiles.filter(f => f !== att);
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  getFileIcon(name: string): string {
    const ext = name.split('.').pop()?.toLowerCase() || '';
    const iconMap: Record<string, string> = {
      xlsx: 'table_chart', xls: 'table_chart', csv: 'table_chart',
      pdf: 'picture_as_pdf',
      doc: 'description', docx: 'description',
      png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', webp: 'image',
      mp4: 'movie', webm: 'movie',
      txt: 'text_snippet', md: 'text_snippet',
      html: 'code', json: 'data_object', xml: 'code',
      zip: 'folder_zip', rar: 'folder_zip',
      py: 'terminal', js: 'javascript', ts: 'javascript',
    };
    return iconMap[ext] || 'insert_drive_file';
  }

  clearChat(): void {
    this.expandedMessages.clear();
    this.expandedSteps.clear();
    this.chatCleared.emit();
  }

  scrollToBottom(): void {
    setTimeout(() => {
      if (this.chatContainer) {
        const container = this.chatContainer.nativeElement.querySelector('.messages-area');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }
    }, 50);
  }

  formatTime(date: Date): string {
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  }

  getDuration(start: Date, end: Date): string {
    const ms = end.getTime() - start.getTime();
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  }

  totalDuration(msg: ChatMessage): string {
    const steps = msg.intermediateSteps || [];
    if (steps.length === 0) return '';
    const first = steps[0]?.startTime;
    const last = steps[steps.length - 1]?.endTime;
    if (!first || !last) return '';
    return this.getDuration(first, last);
  }

  hasStreamingMessage(): boolean {
    const msgs = this.messages();
    return msgs.length > 0 && msgs[msgs.length - 1].role === 'assistant' && msgs[msgs.length - 1].isStreaming === true;
  }

  sanitizeImageUrl(img: ImageData): SafeUrl {
    if (img.url) return this.sanitizer.bypassSecurityTrustUrl(img.url);
    if (img.base64) return this.sanitizer.bypassSecurityTrustUrl(`data:${img.mimeType || 'image/png'};base64,${img.base64}`);
    return '' as SafeUrl;
  }

  sanitizeVideoUrl(video: VideoData): SafeUrl {
    if (video.url) return this.sanitizer.bypassSecurityTrustUrl(video.url);
    if (video.base64) return this.sanitizer.bypassSecurityTrustUrl(`data:${video.mimeType || 'video/mp4'};base64,${video.base64}`);
    return '' as SafeUrl;
  }

  openPresentation(html: string): void {
    this.presentationOpened.emit(html);
  }

  getPresentationHtml(msg: ChatMessage): string | null {
    if (!msg.intermediateSteps) return null;
    for (const step of msg.intermediateSteps) {
      if (step.data?.html) return step.data.html;
    }
    return null;
  }

  getStepIcon(stepName: string): string {
    const iconMap: Record<string, string> = {
      'input': 'input',
      'llm': 'psychology',
      'rag': 'search',
      'tool': 'build',
      'output': 'output',
      'synthesizer': 'merge_type',
      'adaptive_agent': 'smart_toy',
      'browser': 'web',
      'designer': 'palette',
      'researcher': 'search',
      'communication': 'campaign'
    };
    return iconMap[stepName?.toLowerCase()] || 'circle';
  }
}
