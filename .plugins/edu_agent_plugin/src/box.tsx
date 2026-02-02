import React, { useState, useEffect, useRef } from 'react';
import { LabIcon, infoIcon, runIcon } from '@jupyterlab/ui-components';
import { makeApiRequest } from './handler';
import { InfoDialog } from './info-dialog';
import Markdown from 'react-markdown';
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'

// A utility function to make API requests to the server extension
// async function makeApiRequest(url = '', data = {}) {
//   const response = await fetch(url, {
//     method: 'POST',
//     headers: { 'Content-Type': 'application/json' },
//     body: JSON.stringify(data),
//   });
//   if (!response.ok) {
//     throw new Error(`HTTP error! status: ${response.status}`);
//   }
//   return response.json();
// }

// Define a more detailed structure for our messages
interface Message {
  sender: 'user' | 'peer' | 'tutor';
  text: string;
  // We store the original question to allow for easy escalation
  originalQuery?: string;
}

interface ChatPanelProps {
  onClose?: () => void;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ onClose }) => {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { sender: 'peer', text: "Hey! I'm your study buddy. Ask me anything about the course notes, and I'll try my best to explain it." }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInfoOpen, setIsInfoOpen] = useState(false);

  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const styleId = 'chat-panel-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.innerHTML = `
     .chat-panel-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        background-color: var(--jp-layout-color1);
        font-family: var(--jp-ui-font-family);
        color: var(--jp-ui-font-color1);
        position: relative; /* For absolute positioning of overlay */
      }
      .chat-header {
        padding: 6px 12px;
        background: var(--jp-brand-color1);
        color: white;
        font-weight: bold;
        display: flex;
        justify-content: space-between; /* Space for info button */
        align-items: center;
        flex-shrink: 0;
        border-bottom: 1px solid var(--jp-border-color1);
        height: 40px;
        box-sizing: border-box;
      }
      .header-title {
        flex-grow: 1;
        text-align: center;
      }
      .header-btn {
        color: #fff;
        background: transparent;
        border: none;
        color: white;
        cursor: pointer;
        padding: 4px;
        border-radius: 4px;
        display: flex;
        align-items: center;
      }
      .header-btn:hover {
        background-color: rgba(255,255,255,0.2);
      }
      .message-list {
        flex-grow: 1;
        overflow-y: auto;
        padding: 10px;
        display: flex;
        flex-direction: column;
      }
      .input-area {
        display: flex;
        align-items: center;
        padding: 10px;
        border-top: 1px solid var(--jp-border-color1);
        background-color: var(--jp-layout-color0);
        flex-shrink: 0;
      }
      .jp-chat-input {
        flex-grow: 1;
        border: 1px solid var(--jp-border-color1);
        border-radius: var(--jp-border-radius);
        padding: 8px 12px;
        margin-right: 8px;
        background-color: var(--jp-layout-color1);
        color: var(--jp-ui-font-color1);
      }
      .jp-chat-send-button {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        width: 32px;
        height: 32px;
        border: none;
        background-color: var(--jp-brand-color1);
        color: white;
        border-radius: var(--jp-border-radius);
        cursor: pointer;
      }
      .jp-chat-send-button:disabled {
          background-color: var(--jp-layout-color3);
      }
      .message-container {
        display: flex;
        flex-direction: column;
        margin-bottom: 10px;
        max-width: 85%;
      }
      .message-container.user { align-self: flex-end; }
      .message-container.peer, .message-container.tutor { align-self: flex-start; }
      
      .message-bubble {
        padding: 8px 12px;
        border-radius: 12px;
        line-height: 1.4;
        word-wrap: break-word;
      }
      .message-bubble.user { background-color: var(--jp-brand-color1); color: white; }
      .message-bubble.peer { background-color: var(--jp-layout-color2); color: var(--jp-ui-font-color1); }
      .message-bubble.tutor { background-color: var(--jp-info-color2); color: var(--jp-info-color0); border: 1px solid var(--jp-info-color3); }

      .escalate-button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background-color: var(--jp-layout-color1);
        border: 1px solid var(--jp-brand-color1);
        color: var(--jp-brand-color1);
        padding: 4px 10px;
        border-radius: 12px;
        cursor: pointer;
        font-size: 0.8em;
        margin-top: 8px;
        align-self: flex-start;
        transition: background-color 0.2s;
      }
      .escalate-button:hover {
        background-color: var(--jp-brand-color3);
      }
      .escalate-button .jp-icon-svg {
        width: 14px;
        height: 14px;
      }

      /* Info Dialog Styles */
      .info-dialog-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 100;
        display: flex;
        justify-content: center;
        align-items: flex-start;
        padding-top: 20px;
      }
      .info-dialog {
        background-color: var(--jp-layout-color1);
        width: 90%;
        max-height: 90%;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid var(--jp-border-color1);
      }
      .info-header {
        padding: 10px 15px;
        border-bottom: 1px solid var(--jp-border-color2);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: bold;
        font-size: 1.1em;
      }
      .close-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: var(--jp-ui-font-color1);
      }
      .info-content {
        padding: 15px;
        overflow-y: auto;
      }
      .info-section {
        margin-bottom: 20px;
      }
      .info-section h3 {
        margin-top: 0;
        border-bottom: 1px solid var(--jp-border-color2);
        padding-bottom: 5px;
        margin-bottom: 10px;
        color: var(--jp-ui-font-color0);
      }
      .progress-bar-container {
        background-color: var(--jp-layout-color3);
        height: 10px;
        border-radius: 5px;
        overflow: hidden;
      }
      .progress-bar {
        background-color: var(--jp-success-color1);
        height: 100%;
      }
      .progress-text {
        text-align: right;
        font-size: 0.9em;
        margin-top: 4px;
        color: var(--jp-ui-font-color2);
      }
      
      /* Roadmap Styles */
      .roadmap-list {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      .roadmap-item {
        display: flex;
        align-items: center;
        padding: 6px 0;
        font-size: 0.95em;
        border-left: 2px solid var(--jp-border-color2);
        padding-left: 10px;
        margin-left: 5px;
        position: relative;
      }
      .status-dot {
        position: absolute;
        left: -6px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: var(--jp-layout-color3);
        border: 2px solid var(--jp-layout-color1);
      }
      .roadmap-item.completed { color: var(--jp-ui-font-color2); }
      .roadmap-item.completed .status-dot { background-color: var(--jp-success-color1); }
      
      .roadmap-item.current { font-weight: bold; color: var(--jp-brand-color1); }
      .roadmap-item.current .status-dot { background-color: var(--jp-brand-color1); width: 12px; height: 12px; left: -7px; }
      
      .check-mark { margin-left: auto; color: var(--jp-success-color1); }
      .current-badge { 
        margin-left: auto; 
        background: var(--jp-brand-color1); 
        color: white; 
        font-size: 0.75em; 
        padding: 2px 6px; 
        border-radius: 10px; 
      }

      .reindex-btn {
        width: 100%;
        padding: 8px;
        background-color: var(--jp-error-color1);
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
      }
      .reindex-btn:disabled { opacity: 0.7; cursor: not-allowed; }
    `;
    document.head.appendChild(style);

    return () => {
      const styleElement = document.getElementById(styleId);
      if (styleElement) styleElement.remove();
    };
  }, []);

  const getCurrentOpenedLOid = (): string | null => {
    // get Lo ID from url (ex "http://localhost:8888/voila/render/generated_course/LO-3.1/LO-3.1.ipynb" LO ID is "LO-3.1")
    const pathParts = window.location.pathname.split('/');
    for (let i = 0; i < pathParts.length; i++) {
      if (pathParts[i].startsWith('LO-')) {
        return pathParts[i];
      }
    }
    return null;
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    const query = inputValue;

    const userMessage: Message = { sender: 'user', text: query };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    var studentProgress = -1;
    // Find lesson number from url (Ex */04_core_protocols/*)
    const pathParts = window.location.pathname.split('/');
    for (let i = 0; i < pathParts.length; i++) {
      if (pathParts[i].match(/^\d{2}_/)) {
        studentProgress = parseInt(pathParts[i].substring(0, 2), 10);
        console.log("Detected student progress from URL:", studentProgress);
        break;
      }
    }

    const currentLOid = getCurrentOpenedLOid();

    try {
      const response = await makeApiRequest('/ask', {
        query: query,
        agent_type: 'peer',
        student_progress: studentProgress,
        current_lo_id: currentLOid,
        history: messages,
      }, {
        method: 'POST',
      });

      // Check if backend signaled escalation is needed
      if (response.escalate) {
        // Show Peer's escalation message with visual indicator
        const escalateMessage: Message = {
          sender: 'peer',
          text: response.data + "\n\n🔄 *Auto-escalating to Tutor...*",
          originalQuery: query
        };
        setMessages(prev => [...prev, escalateMessage]);

        // Auto-trigger Tutor
        console.log("Auto-escalating to Tutor based on relevance grading");
        await handleEscalate(query);
        return;
      }

      const peerMessage: Message = { sender: 'peer', text: response.data, originalQuery: query };
      setMessages(prev => [...prev, peerMessage]);

    } catch (error) {
      handleApiError(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEscalate = async (originalQuery: string) => {
    setIsLoading(true);
    const thinkingMessage: Message = { sender: 'tutor', text: "Thinking..." };
    setMessages(prev => [...prev, thinkingMessage]);

    try {

      var studentProgress = -1;
      // Find lesson number from url (Ex */04_core_protocols/*)
      const pathParts = window.location.pathname.split('/');
      for (let i = 0; i < pathParts.length; i++) {
        if (pathParts[i].match(/^\d{2}_/)) {
          studentProgress = parseInt(pathParts[i].substring(0, 2), 10);
          console.log("Detected student progress from URL:", studentProgress);
          break;
        }
      }

      const response = await makeApiRequest('/ask', {
        query: originalQuery,
        agent_type: 'tutor',
        student_progress: studentProgress,
        history: messages,
      });

      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = { sender: 'tutor', text: response.data };
        return newMessages;
      });

    } catch (error) {
      handleApiError(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApiError = (error: unknown) => {
    const err = error as Error;
    console.error('Failed to get answer:', err);
    const errorMessage: Message = { sender: 'peer', text: `Sorry, an error occurred: ${err.message}` };
    setMessages(prev => [...prev, errorMessage]);
  };

  return (
    <div className="chat-panel-container">
      <div className="chat-header">
        Q-Toolkit Assistant

        <button className="header-btn" onClick={() => setIsInfoOpen(true)} title="Course Info">
          <infoIcon.react tag="span" />
        </button>
      </div>

      {/* Info Dialog Overlay */}
      <InfoDialog
        isOpen={isInfoOpen}
        onClose={() => setIsInfoOpen(false)}
        currentLOid={getCurrentOpenedLOid()}
      />

      <div className="message-list">
        {messages.map((msg, index) => (
          <div key={index} className={`message-container ${msg.sender}`}>
            <div className={`message-bubble ${msg.sender}`}>
              <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{msg.text}</Markdown>
            </div>
            {msg.sender === 'peer' && msg.originalQuery && (
              <button
                className="escalate-button"
                onClick={() => handleEscalate(msg.originalQuery!)}
                disabled={isLoading}
              >
                <infoIcon.react tag="span" />
                Ask Tutor for a deeper explanation
              </button>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="input-area">
        <input
          className="jp-chat-input"
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
          placeholder="Ask your peer a question..."
          disabled={isLoading}
        />
        <button className="jp-chat-send-button" onClick={handleSendMessage} disabled={isLoading}>
          {isLoading ? '...' : <runIcon.react tag="span" />}
        </button>
      </div>
    </div>
  );
};

export default ChatPanel;

