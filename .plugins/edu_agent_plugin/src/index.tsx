import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ISettingRegistry } from '@jupyterlab/settingregistry';
import { INotebookTracker, NotebookTracker } from '@jupyterlab/notebook';
import { ReactWidget } from '@jupyterlab/apputils';
// import { getChatWidget } from './box';
import { Widget } from '@lumino/widgets';
import ReactDOM from 'react-dom';
import ChatFAB from './chat-fab';
import React from 'react';
import { createRoot } from 'react-dom/client';
import ChatPanel from './box';

declare const Voila: any;

/**
 * Initialization data for the edu_agents extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'edu_agents:plugin',
  description: 'A bunch of AI agents useful for education',
  autoStart: true,
  optional: [ISettingRegistry, INotebookTracker],
  activate: (app: JupyterFrontEnd, settingRegistry: ISettingRegistry | null, notebookTracker: INotebookTracker | null) => {

    const isVoila = typeof Voila !== 'undefined' || window.location.pathname.includes('/voila/');
    const shell = (app.shell as any);

    // Create a widget to hold our FAB
    const fabWidget = new Widget();
    fabWidget.id = 'chat-fab-widget';
    fabWidget.addClass('jp-chat-fab-widget');

    // Render the React FAB component
    ReactDOM.render(React.createElement(ChatPanel), fabWidget.node);

    // Create a div and attach directly to document body
    const fabContainer = document.createElement('div');
    fabContainer.id = 'chat-fab-container';
    document.body.appendChild(fabContainer);

    const fabWrapper = document.createElement('div');
    fabWrapper.id = 'chat-fab-wrapper';

    const chatWrapper = document.createElement('div');
    chatWrapper.id = 'chat-panel-wrapper';
    chatWrapper.style = `
      position: fixed;
    right: 50px;
    bottom: 100px;
    height: 70%;
    width: 400px;
    background: #f1f1f1;
    z-index: 1;
    display: flex;
    border-radius: 16px;
    `
    chatWrapper.appendChild(fabWidget.node);
    

    // Listen for clicks on the container div and toggle the visibility agent chat area
    fabWrapper.onclick = (_) => {
      if (isVoila) {
        if (!fabContainer.contains(chatWrapper))
          fabContainer.appendChild(chatWrapper);
        else
          fabContainer.removeChild(chatWrapper);
      }

      if (fabWidget.isVisible) {
        if(shell)
        shell.collapseRight()
      } else {
        app.shell.activateById('chat-fab-widget');
      }
    }

    // Render the React FAB component
    ReactDOM.render(React.createElement(ChatFAB), fabWrapper);
    fabContainer.append(fabWrapper)

    // Add the widget to the main area (it will float due to fixed positioning)
    app.shell.add(fabWidget, 'right', { rank: 1000 });

    if (notebookTracker) {
      notebookTracker.currentChanged.connect(() => {
        if (notebookTracker.currentWidget) {
          fabContainer.style.display = 'block';
        } else {
          fabContainer.style.display = 'none';
        }
      });
    } else {
      console.log("No notebook tracker available, FAB will always be visible.");
    }

    if(shell?.restored) {
      shell.restored.then(() => {
      // By default, activate the chat area when the extension is loaded
      app.shell.activateById('chat-fab-widget');
    });
    }
  }
};

export default plugin;
