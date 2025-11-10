import { lerp } from './utils/lerp';
import { getAngleX, getAngleY, getAngleBetweenTwoPoints } from './utils/getAngle';
import { Bullet } from './bullet';
import { playerKeyboardEvents } from './playerKeyboardEvents';
import { App } from './app';
import { Assets, Rectangle, Sprite, Texture, Text as PixiText } from 'pixi.js';


const spriteCoords = {
  x: [0, 64, 128],
  y: [0, 64, 128, 192],
};

const constants = {
  maxThrust: 10,
  maxLevel: 2,
};

interface PlayerProps {
  app: App;
  health?: number;
}

export class Player {

  texture!: Texture;
  entity: any;
  bullets!: Bullet[];
  state!: any;
  _shootInterval!: number;
  shoot !: any;
  scoreDisplay = new PixiText({
    text: 'Score: 0',
    style: {
      fill: 'white',
      align: 'center',
    }
  });


  constructor({ app, health = 100 }: PlayerProps) {

    // Set up some state
    this.state = {
      health: health,
      maxHealth: health,
      velocity: { x: 0, y: 0 },
      idealPosition: { x: app.pixi.screen.width / 2, y: app.pixi.screen.height / 2 },
      prevPosition: {
        x: app.pixi.screen.width / 2,
        y: app.pixi.screen.height / 2,
      },
      angleToMouse: 0,
      thrustAngle: 1.5,
      _score: 0,
      get score() {
        return this._score;
      },
      set score(value: number) {
        this._score = value;
        this.level = Math.trunc(value * 0.1);
      },
      _thrust: 0,
      get thrust() {
        return this._thrust;
      },
      set thrust(value: number) {
        this.thrustAngle = this.angleToMouse;
        value <= constants.maxThrust ? (this._thrust = value) : null;
      },
      _level: 0,
      get level() {
        return this._level;
      },
      set level(value: number) {
        this._level = value <= constants.maxLevel ? value : constants.maxLevel;
      },
    };

    // create a new Sprite from an image texture
    //   const texture = app.pixi.loader.resources.ship.texture || PIXI.Texture.EMPTY;
    const texture = Assets.get('ship');
    texture.trim = new Rectangle(0, 0, 100, 120);
    texture.frame.x = spriteCoords.x[0];
    texture.frame.y = spriteCoords.y[this.state.level];
    texture.frame.width = 64;
    texture.frame.height = 64;
    texture.updateUvs();

    this.texture = texture;
    const ship = Sprite.from(texture);
    ship.x = this.state.idealPosition.x;
    ship.y = this.state.idealPosition.y;
    ship.anchor.set(0.78, 0.9);
    ship.zIndex = 10;

    this.entity = ship;

    app.player = this;

    app.pixi.stage.addChild(ship);
    app.pixi.stage.addChild(this.scoreDisplay);

    this.shoot = (isRight = false) => {
      this.bullets.push(new Bullet(15, this.entity.rotation - 1.5, app, isRight));
    };

    // Create an array for the bullets
    this.bullets = [];

    this._shootInterval = 0;

    // Listen for clicks and shoot
    window.addEventListener('mousedown', (e) => {
      clearInterval(this._shootInterval);
      this.shoot(e.which === 3);
      this._shootInterval = setInterval(this.shoot, 100, e.which === 3);
    });

    window.addEventListener(`contextmenu`, (e) => {
      e.preventDefault();
  });

    // Listen for mouse up and stop shooting
    window.addEventListener('mouseup', () => {
      clearInterval(this._shootInterval);
    });

    playerKeyboardEvents({ player: this });
    this.increaseThrust = () => {
      // TODO: Find better sound if possible.
      // app.soundManager.playSound('thrusters');
      this.state.thrust++;
    }
  }
  increaseThrust;

  decreaseThrust = () => {
    this.state.thrust !== 0 ? this.state.thrust-- : null;
  };

  cancelThrust = () => {
    this.state.thrust = 0;
  };

  update = ({ delta, app }: { delta: number; app: App }) => {
    // Update sprites if thrust has changed
    const limitedThrust =
      this.state.thrust >= spriteCoords.x.length - 1 ? spriteCoords.x.length - 1 : this.state.thrust;
    if (
      this.texture.frame.x !== spriteCoords.x[limitedThrust] ||
      this.texture.frame.y !== spriteCoords.x[this.state.level]
    ) {
      this.texture.frame.x = spriteCoords.x[limitedThrust];
      this.texture.frame.y = spriteCoords.x[this.state.level];
      this.texture.updateUvs();
    }

    // Update position from app state
    const currentPositionX = lerp(this.entity.position.x, this.state.idealPosition.x, delta * 0.01);
    const currentPositionY = lerp(this.entity.position.y, this.state.idealPosition.y, delta * 0.01);
    this.entity.position.x = currentPositionX;
    this.entity.position.y = currentPositionY;

    // Update velocity state
    this.state.velocity = {
      x: currentPositionX - this.state.prevPosition.x,
      y: currentPositionY - this.state.prevPosition.y,
    };

    // Update prev position
    this.state.prevPosition.x = currentPositionX;
    this.state.prevPosition.y = currentPositionY;

    // Point ship towards mouse
    // TODO: Normalise the angle when it loops so I can lerp the values
    const angleToMouse = getAngleBetweenTwoPoints(
      app.state.mouseX,
      app.state.mouseY,
      currentPositionX,
      currentPositionY,
    );
    this.state.angleToMouse = angleToMouse;
    this.entity.rotation = angleToMouse + 1.5;

    // Move ship if thrust is above 0
    this.state.idealPosition.x += getAngleX(this.state.thrust, this.state.thrustAngle);
    this.state.idealPosition.y += getAngleY(this.state.thrust, this.state.thrustAngle);

    // Update the bullets
    this.bullets.forEach((bullet) => {
      bullet.update(delta);
    });

    this.scoreDisplay.text = `Score: ${this.state.score}`
  };
}