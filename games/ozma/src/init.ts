import { Application, ApplicationOptions} from "pixi.js";

import { loadTexturesAsync } from "./loadTexturesAsync";
import { App } from "./app";
import shipImagePath from './images/Spaceship_Asset.png';
import bgImagePath from './images/Blue_Nebula_5.png';
import explosionImagePath from './images/circle_explosion.png';
import enemyBlue from './images/enemy_blue.png';
import enemyGreen from './images/enemy_green.png';


const canvas = document.querySelector<HTMLDivElement>('#canvas');


const createPixi = async (parentEl: HTMLDivElement) => {
  const config: Partial<ApplicationOptions> = {
    backgroundColor: 0x000000,
    resizeTo: parentEl,
    resolution: window.devicePixelRatio || 1,
    autoDensity: true,
    antialias: true,
  };

  const pixiInstance = new Application();
  await pixiInstance.init(config);
  pixiInstance.stage.sortableChildren = true;

  parentEl.appendChild(pixiInstance.canvas);

  return pixiInstance;
};

export const initApp = async () => {
  if (canvas === null) return;


  const pixi = await createPixi(canvas);

  const textures = [
    { name: 'ship', url: shipImagePath },
    { name: 'background', url: bgImagePath },
    { name: 'explosion', url: explosionImagePath },
    { name: 'enemy_green', url: enemyGreen},
    { name: 'enemy_blue', url: enemyBlue},
  ];

  await loadTexturesAsync(textures);

  new App(pixi);
}