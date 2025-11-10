import { getRandomArbitrary } from './utils/getRandomRange';
import { Enemy } from './enemy';
import { getAngleBetweenTwoPoints } from './utils/getAngle';
import { App } from './app';

interface EnemyGeneratorProps {
  app: App;
  frequency: number;
}

export class EnemyGenerator {
  constructor({ app, frequency }: EnemyGeneratorProps) {
    this.enemy = [];
    this.maxFrequency = frequency;
    this.state = {
      frequency: frequency*3, // Start with a high frequency
      isRunning: false,
    };

    this.createEnemy = () => {
      const posX = getRandomArbitrary(0, app.pixi.screen.width);
      const posY = -100;
      const speed = getRandomArbitrary(1, 3);
      const angleToPlayer = getAngleBetweenTwoPoints(
        app.player.entity.position.x,
        app.player.entity.position.y,
        posX,
        posY,
      );

      const newEnemy = new Enemy({ position: { x: posX, y: posY }, speed, direction: angleToPlayer, app });

      this.enemy.push(newEnemy);
    };
  }

  enemy: Enemy[];
  _enemyTimeout = 0;
  createEnemy;
  state;
  maxFrequency;

  start = () => {
    this.state.isRunning = true;
    this.createEnemy();
    this.state.frequency = Math.max(this.maxFrequency, this.state.frequency - 500);

    if (this.state.isRunning) {
      clearTimeout(this._enemyTimeout);

      this._enemyTimeout = setTimeout(this.start, Math.random() * this.state.frequency + 300);
    }
  };

  stop = () => {
    this.state.isRunning = false;
    clearTimeout(this._enemyTimeout);
  };

  update = ({ delta, app }: { delta: number; app: App }) => {
    this.enemy.forEach((enemy) => {
      enemy.update({ delta, app });
    });
  };
}