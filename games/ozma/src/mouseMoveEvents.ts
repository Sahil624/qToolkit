import type { App } from './app';

export const mouseMoveEvents = ({ app }: { app: App }) => {
  window.addEventListener('mousemove', (e) => {
    app.state.mouseX = e.x;
    app.state.mouseY = e.y;
  });
};