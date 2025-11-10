import { Application, Ticker } from "pixi.js";
import { Player } from "./player";
import { BackgroundEntity } from "./background";
import { EnemyGenerator as EnemyGenerator } from "./enemyGenerator";
import { mouseMoveEvents } from "./mouseMoveEvents";
import { SoundManager } from "./sound";

export class App {
  pixi: Application;
  player!: Player;
  background!: BackgroundEntity;
  enemyGenerator!: EnemyGenerator;
  state = {
    mouseX: 0,
    mouseY: 0,
    loading: true,
    loadingProgress: 0,
  };
  soundManager!: SoundManager;

  constructor(pixi: Application) {
    this.pixi = pixi;
    this.background = new BackgroundEntity(this);

    this.soundManager = new SoundManager();
    // Create our player and add to the scene
    this.player = new Player({ app: this });

    // Start the enemy generator
    this.enemyGenerator = new EnemyGenerator({ app: this, frequency: 2000 });
    this.enemyGenerator.start();

    // For debugging
    (window as any).sendEnemy = () => this.enemyGenerator.createEnemy();
    
    mouseMoveEvents({ app: this });

    // Add some stuff to the ticker
    this.pixi.ticker.add((deltaT: Ticker) => {
      // stats.begin();

      this.player.update({ delta: deltaT.deltaTime, app: this });
      this.background.update({ delta: deltaT.deltaTime, app: this });
      this.enemyGenerator.update({ delta: deltaT.deltaTime, app: this });

      // stats.end();
    });
  }
}