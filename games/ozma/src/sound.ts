import { Sound } from '@pixi/sound';
import laserSound from './sound/shooter_sound.wav';
import laserSound2 from './sound/shooter_sound_2.wav';
import exploding from './sound/exploding.wav';
import stateChange from './sound/state_change.wav';
import thrusters from './sound/thrusters.mp3';

export class SoundManager {
    constructor() {
        const textures = [
            { name: 'laserSound', url: laserSound , volume: 0.7},
            { name: 'laserSound2', url: laserSound2 , volume: 0.2 },
            { name: 'exploding', url: exploding },
            { name: 'stateChange', url: stateChange },
            { name: 'thrusters', url: thrusters },
        ]

        // Add the sprites data when creating sounds
        textures.forEach((texture) => {
            const sound = Sound.from(texture.url);

            if(texture.volume) {
                sound.volume = texture.volume;
            }

            this.sound.set(texture.name, sound);
        })
    }
    sound: Map<string, Sound> = new Map();

    playSound(soundName: string) {
        this.sound.get(soundName)?.play();
    }
}