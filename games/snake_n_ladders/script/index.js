import { Game } from './game.js';

let gameInstance = null;

export function getGame() {
    if (!gameInstance) {
        gameInstance = new Game();
        gameInstance.initializeGame();
    }

    return gameInstance
}

export function startGame2() {
    getGame().startGame();
}