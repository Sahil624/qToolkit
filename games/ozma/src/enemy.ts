import type { App } from './app';
import { getAngleX, getAngleY } from './utils/getAngle';
import { getRandomArbitrary, getRandomInt } from './utils/getRandomRange';
import { isInsideRectangle } from './utils/isInsideRectangle';
import { Explosion } from './Explosion';
import { lerp } from './utils/lerp';
import { Assets, Container, Sprite, Texture } from 'pixi.js';

interface EnemyProps {
  position?: { x: number; y: number };
  speed?: number;
  health?: number;
  direction?: number;
  app: App;
}

const spriteDimension = 247;
// const spriteRowSize = 247;
// const spriteRows = 8;

export class Enemy {
  constructor({
    position = { x: 0, y: 0 },
    direction = 1.5,
    health = getRandomInt(5, 30),
    speed = 2,
    app,
  }: EnemyProps) {
    this.state = {
      speed: speed,
      direction: direction,
      exploding: false,
      health: health,
      maxHealth: health,
      takingDamage: false,
      changingState: false,
    };

    this.quantumState = this.getRandomQuantumState(); // Initialize a random state
    this.canBeDestroyed = false;

    setTimeout(() => {
      this.canBeDestroyed = true;
    }, 5000);

    const container = new Container();

    this.container = container;

    let texture: Texture = Assets.get('enemy_green');
    if (this.quantumState == "|+>" || this.quantumState == "|->") {
      texture = Assets.get('enemy_green');
    } else {
      texture = Assets.get('enemy_blue')
    }
    // texture.frame.x = spriteRowSize * getRandomInt(0, 7);
    // texture.frame.y = spriteRowSize * getRandomInt(0, 7);
    texture.frame.width = spriteDimension;
    // texture.frame.height = spriteDimension;
    texture.updateUvs();


    // create a new Sprite from texture
    const sprite = Sprite.from(texture);
    sprite.position.x = position.x;
    sprite.position.y = position.y;
    sprite.anchor.set(0.5);
    sprite.scale.set(0.2);
    sprite.rotation = 1;
    sprite.label = 'Enemy';

    this.entity = sprite;
    this.setEnemyTexture();

    this.container.addChild(sprite);

    app.pixi.stage.addChild(this.container);

    this.explosion = null;

    this.takeDamage = ({ damage }: { damage: number }) => {
      this.state.health -= damage;
      this.state.speed = this.state.speed * 0.65;
      this.state.takingDamage = true;
      this.entity.tint = 0xff8359;
      if (this.state.health <= 0) {
        this.explode();
        app.player.state.score++;
      }
    };

    this.explode = () => {
      this.container.zIndex = 9;
      // Create a new explosion
      this.explosion = new Explosion(app);
      this.explosion.entity.position.set(this.entity.width / 2, this.entity.height / 2);
      this.state.exploding = true;
      this.container.addChild(this.explosion.entity);
      app.soundManager.playSound('exploding');
    };

    this.destroy = () => {
      app.enemyGenerator.enemy = app.enemyGenerator.enemy.filter((enemy) => enemy !== this);
      app.pixi.stage.removeChild(this.container);
      //   this.container.destroy({ children: true, texture: false, baseTexture: true });
      this.container.destroy({
        children: true,
        texture: false
      })
    };

    this.changeState = (isHadamardBullet: boolean) => {
      const oldSpeed = this.state.speed;
      this.state.speed = 0;
      this.state.changingState = true;

      const outcome = this.measureQubit(isHadamardBullet ? "hadamard" : "computational");
      this.quantumState = outcome;
      this.setEnemyTexture();
      app.soundManager.playSound('stateChange');
      setTimeout(() => {
        // this.state.direction += (Math.random() - 0.5) * 0.75; // Slight change in direction
        this.state.changingState = false;
        this.entity.visible = true;
        this.state.speed = oldSpeed * 1.5; // Increase speed
        this.state.health = this.state.maxHealth; // Reset health
        this.entity.position.x = getRandomArbitrary(0, this.entity.x); // Reset position
        this.entity.position.y = getRandomArbitrary(0, this.entity.y); // Reset position
      }, 2000);
    }
  }

  entity;
  state;
  canBeDestroyed = false;
  isInsideViewport = false;
  takeDamage;
  destroy;
  explosion: Explosion | null;
  explode;
  container;
  quantumState: string;
  changeState;

  measureQubit = (basis: string): string => {
    const randomNumber = Math.random();

    if (this.quantumState == "|0>") {
      if (basis == "computational") {
        return "|0>";
      } else if (basis == "hadamard") {
        if (randomNumber < 0.5)
          return "|+>";
        else
          return "|->";
      }
    } else if (this.quantumState == "|1>") {
      if (basis == "computational") {
        return "|1>";
      } else if (basis == "hadamard") {
        if (randomNumber < 0.5)
          return "|+>";
        else
          return "|->";
      }

    } else if (this.quantumState == "|+>") {
      if (basis == "computational") {
        if (randomNumber < 0.5)
          return "|0>";
        else
          return "|1>";

      } else if (basis == "hadamard") {
        return "|+>";
      }
    } else if (this.quantumState == "|->") {
      if (basis == "computational") {
        if (randomNumber < 0.5)
          return "|0>";
        else
          return "|1>";
      } else if (basis == "hadamard") {
        return "|->";
      }
    }
    return "|0>";
  };

  setEnemyTexture = () => {
    if (this.quantumState == "|0>" || this.quantumState == "|1>") {
      this.entity.texture = Assets.get('enemy_blue');
    } else if (this.quantumState == "|+>" || this.quantumState == "|->") {
      this.entity.texture = Assets.get('enemy_green');
    }
  }

  private getRandomQuantumState(): string { // Function for setting a random quantum state
    const states = ["|0>", "|1>", "|+>", "|->"];
    return states[Math.floor(Math.random() * states.length)];
  }

  update({ delta, app }: { delta: number; app: App }) {
    const { speed, direction } = this.state;
    // Update position from app state
    this.entity.x += getAngleX(speed, direction) * delta;
    this.entity.y += getAngleY(speed, direction) * delta;

    // Check if it is still on the screen
    this.isInsideViewport = isInsideRectangle({
      x: this.entity.x,
      y: this.entity.y,
      width: app.pixi.screen.width + this.entity.width,
      height: app.pixi.screen.height + this.entity.height,
    });

    if (this.isInsideViewport) {
      this.canBeDestroyed = true;
    }

    if (!this.state.takingDamage) {
      this.entity.tint = 0xffffff;
    }

    this.state.takingDamage = false;

    if (this.canBeDestroyed && !this.isInsideViewport) {
      this.destroy();
    }

    if (this.state.changingState) {
      this.entity.visible = !this.entity.visible;
    }

    if ((this.state.exploding = true && this.explosion !== null)) {
      this.explosion.update({ delta, position: { x: this.entity.position.x, y: this.entity.position.y } });

      if (this.explosion.state.step > 2) {
        this.entity.scale.set(lerp(this.entity.scale.x, 0.75, 0.2));
        this.entity.alpha = lerp(1, 0, 0.75);
      }
      if (this.explosion.state.step > 7) {
        this.entity.visible = false;
      }
      if (this.explosion.state.finished) {
        this.destroy();
      }
    }
  }
}