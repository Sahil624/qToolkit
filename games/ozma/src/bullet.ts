import { Graphics, Sprite } from 'pixi.js';
import type { App } from './app';
import { getAngleX, getAngleY } from './utils/getAngle';
import { isInsideRectangle } from './utils/isInsideRectangle';
import Victor from 'victor';
import { isCorrectBullet } from './utils/qUtils';

// create a new graphic
const greenGraphic = new Graphics();
greenGraphic.setStrokeStyle({
  width: 1,
  color: 0x9cfc7e,
  alpha: 1,
});
greenGraphic.roundRect(-10, -1, 3, 1, 2);;
greenGraphic.roundRect(-5, -1, 5, 2, 2);
greenGraphic.roundRect(3, -2, 10, 4, 2);
greenGraphic.fill({
  color: 0x9cfc7e,
  alpha: 1,
});
greenGraphic.label = 'Red Bullet';

const blueGraphic = new Graphics();
blueGraphic.setStrokeStyle({
  width: 1,
  color: 0x667aff,
  alpha: 1,
});
blueGraphic.roundRect(-10, -1, 3, 1, 2);;
blueGraphic.roundRect(-5, -1, 5, 2, 2);
blueGraphic.roundRect(3, -2, 10, 4, 2);
blueGraphic.fill({
  color: 0x667aff,
  alpha: 1,
});
blueGraphic.label = 'Blue Bullet';

export class Bullet {
  constructor(speed: number, direction: number, app: App, isRight: boolean) {
    this.state = {
      speed: speed,
      direction: direction,
      destroyed: false,
      damage: 7,
    };

    this.isHadamardBullet = isRight;

    if (this.isHadamardBullet)
      app.soundManager.playSound('laserSound');
    else
      app.soundManager.playSound('laserSound2');

    const texture = app.pixi.renderer.generateTexture(isRight ? greenGraphic : blueGraphic);
    const sprite = new Sprite(texture);
    sprite.x = app.player.entity.x;
    sprite.y = app.player.entity.y;
    sprite.label = 'Bullet';

    // Orient the bullet
    const randomAdjustment = (Math.random() - 0.5) * 0.01;
    sprite.rotation = direction + randomAdjustment;
    this.state.direction = direction + randomAdjustment;

    this.entity = sprite;

    app.pixi.stage.addChild(sprite);

    this.destroy = () => {
      this.state.destroyed = true;
      app.player.bullets = app.player.bullets.filter((item) => item !== this);
      app.pixi.stage.removeChild(this.entity);
      this.entity.destroy(true);
    };

    this.hitTest = () => {
      const enemies = app.enemyGenerator.enemy;

      const hitEnemy = enemies.filter((enemy) => {
        // TODO: Improve the hit test based on more precise locations of the sprites
        const bulletVec = new Victor(this.entity.x, this.entity.y);
        const enemyVec = new Victor(enemy.entity.x, enemy.entity.y);

        const distanceBetween = bulletVec.distance(enemyVec);
        const enemyRadius = enemy.entity.width / 2;

        const didHit = distanceBetween < enemyRadius;

        return didHit ? enemy : false;
      });
      return hitEnemy;
    };

    this.update = (delta: number) => {
      const hitItems = this.hitTest();
      if (hitItems.length > 0) {
        let destroyBullet = false;

        // Update the items that were hit
        hitItems.forEach((item) => {
          if (!item.state.exploding && !item.state.changingState) {

            // Check if the bullet is the correct type to destroy the enemy
            if (isCorrectBullet(this.isHadamardBullet, item.quantumState)) {
              item.takeDamage({ damage: this.state.damage });
            } else {
              item.changeState(this.isHadamardBullet);
              console.log("Hit enemy with incorrect bullet. Change state");
            }

            destroyBullet = true;
          }
        });

        if (destroyBullet) {
          this.destroy();
        }
      }

      if (this.state.destroyed) return;

      // Update position from app state
      this.entity.x += getAngleX(this.state.speed, this.state.direction) * delta;
      this.entity.y += getAngleY(this.state.speed, this.state.direction) * delta;

      // Check if it is still on the screen
      const isOutOfViewport = !isInsideRectangle({
        x: this.entity.x,
        y: this.entity.y,
        width: app.pixi.screen.width,
        height: app.pixi.screen.height,
      });

      if (isOutOfViewport) {
        this.destroy();
      }
    };
  }

  entity;
  state;
  hitTest;
  destroy;
  update;
  isHadamardBullet = false;
}