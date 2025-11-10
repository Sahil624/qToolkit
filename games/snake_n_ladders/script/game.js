import { Ladder } from './ladder.js';
import { Snake } from './snake.js';
import { Player } from './player.js';
import { randIntv1, calculateSquareSize, manhattanDistance } from './utils.js';
import {
    cssColorsOriginal,
    width,
    height,
    movingSpeed,
    baseEntanglementDistance,
    repeaterEntanglementExtension,
    repeaterRange,
    entanglementDuration
} from './consts.js';

const snakeScaleFactor = 1.0;
const snakeWidth = 30;

/**
 * Represents the main game logic for the Quantum Snakes and Ladders game.
 */
export class Game {

    /**
     * Creates a new Game instance.
     */
    constructor() {
        /** @type {Array<Array<Player>>} */
        this.players = []; // Array to store player data, each player having two pieces
        /** @type {Array<Player>} */
        this.currentPlayer = null; // The current player
        /** @type {Iterator} */
        this.playerIterator = null; // Iterator to cycle through players
        /** @type {Set<number>} */
        this.entangledPlayers = new Set(); // Set to track entangled players by their index
        /** @type {Object<number, number>} */
        this.entanglementTimers = {}; // Object to store entanglement timers for each player
        /** @type {Object<number, string>} */
        this.entangleMentTokens = {}; // Object to store entanglement tokens for each player
        /** @type {Array<Object>} */
        this.ladders = []; // Array to store ladder objects
        /** @type {Array<Object>} */
        this.snakes = []; // Array to store snake objects
        /** @type {Array<Object>} */
        this.entanglementSources = []; // Array to store entanglement source positions
        /** @type {Array<Object>} */
        this.repeaters = []; // Array to store repeater positions
        /** @type {Array<string>} */
        this.eventLog = []; // Array to store the event log messages

        this.initializeGame();
    }

    /**
     * Initializes the game state, including creating ladders, snakes, entanglement sources, and repeaters.
     */
    initializeGame() {
        this.snakeImages = []; // Array to store snake image elements
        this.ladderImages = []; // Array to store ladder image elements
        this.makeLadders();
        this.makeSnakes();
        this.makeEntanglementSources();
        this.makeRepeaters();
        this.initializeTokenCount();
    }

    /**
     * Creates the ladder objects for the game.
     */
    makeLadders() {
        this.ladders = [
            new Ladder(1, 0, 4, 2),
            new Ladder(2, 5, 4, 8),
            new Ladder(3, 7, 2, 8),
            new Ladder(3, 4, 4, 5),
            new Ladder(5, 1, 6, 7),
            new Ladder(6, 4, 9, 8),
            new Ladder(7, 1, 9, 3),
            new Ladder(7, 2, 4, 6),
        ];
    }

    /**
     * Creates the snake objects for the game.
     */
    makeSnakes() {
        this.snakes = [
            new Snake(0, 7, 0, 3),
            new Snake(2, 3, 4, 1),
            new Snake(3, 9, 2, 8),
            new Snake(6, 6, 9, 0),
            new Snake(6, 8, 2, 5),
            new Snake(6, 9, 8, 7),
            new Snake(8, 5, 9, 4),
        ];
    }

    /**
     * Initializes the entanglement tokens for each player.
     */
    initializeTokenCount() {
        this.entangleMentTokens = {
            0: 1,
            1: 1
        };
    }

    createSnakes() {
        const board = document.getElementById('board');
        this.snakes.forEach((snake, index) => {
            const snakeImg = new Image();
            snakeImg.src = 'https://png.pngtree.com/png-clipart/20230825/original/pngtree-snake-cartoon-picture-image_8492214.png'; // Path to your snake image
            snakeImg.id = `snake-${index}`; // Give each snake a unique ID
            snakeImg.classList.add('snake-image'); // Add a class for styling

            board.appendChild(snakeImg);
            this.snakeImages.push(snakeImg);
        });
    }

    positionSnakes() {
        const squareSize = document.getElementById('board').offsetWidth / width;

        this.snakeImages.forEach((snakeImg, index) => {
            const snake = this.snakes[index];
            const startX = snake.startX;
            const startY = snake.startY;
            const endX = snake.endX;
            const endY = snake.endY;

            // Calculate the center of the start and end squares
            const startCenterX = (startX + 0.5) * squareSize;
            const startCenterY = (startY + 0.5) * squareSize;
            const endCenterX = (endX + 0.5) * squareSize;
            const endCenterY = (endY + 0.5) * squareSize;

            // Calculate the distance and angle between the start and end points
            const dx = endCenterX - startCenterX;
            const dy = endCenterY - startCenterY;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx) * 180 / Math.PI; // Convert to degrees

            // Set the position and size of the snake image
            snakeImg.style.width = `${distance * snakeScaleFactor}px`;
            snakeImg.style.height = `${snakeWidth}px`; // Use the desired width from consts.js
            snakeImg.style.left = `${startCenterX}px`;
            snakeImg.style.top = `${startCenterY}px`;
            snakeImg.style.transform = `translate(-50%, -50%) rotate(${angle}deg) scaleX(1.0)`;
            snakeImg.style.transformOrigin = `top left`;
        });
    }
    /**
     * Creates the entanglement source positions for the game.
     */
    makeEntanglementSources() {
        this.entanglementSources = [
            { x: 8, y: 7 },  // Near the top-right corner
            { x: 1, y: 5 },  // Near the middle-left
            { x: 4, y: 2 },  // Near the center
            { x: 2, y: 9 },  // Top-left
            { x: 9, y: 2 },  // Top-right
            { x: 3, y: 7 },  // Upper-middle-left
            { x: 7, y: 4 },  // Upper-middle-right
            { x: 5, y: 5 },  // Middle-center
            { x: 1, y: 1 },   // Bottom-left corner
            { x: 9, y: 9 }, // Bottom-right corner
            { x: 3, y: 3 },  // Lower-left-center
            { x: 7, y: 7 },  // Lower-right-center
            { x: 2, y: 4 }, // Slightly above middle-left
            { x: 8, y: 6 }, // Slightly above middle-right
            { x: 6, y: 8 }, // Slightly below middle-right
            { x: 4, y: 1 },  // Below center
            { x: 6, y: 3 }  // Below Center right
        ];
    }

    /**
     * Creates the repeater positions for the game.
     */
    makeRepeaters() {
        this.repeaters = [
            // { x: 7, y: 2 },  // Top-right quadrant
            // { x: 5, y: 4 },  // Center-right 
            // { x: 1, y: 1 },  // Bottom-left quadrant
            // { x: 2, y: 7 }   // Center-left (close to an entanglement source)
        ];
    }

    /**
     * Creates a cyclic iterator for the given array.
     * @param {Array} v - The array to iterate over.
     * @returns {Iterator} An iterator that cycles through the array indefinitely.
     */
    * cyclicIterator(v) {
        let i = 0;
        while (true) {
            yield { idx: i, value: v[i] };
            i = (i + 1) % v.length;
        }
    }

    togglePlayerEntanglementButton() {
        const buttons = document.getElementsByClassName(`token-button`);
        Array.prototype.forEach.call(buttons, (child, idx) => {
            child.disabled = (idx !== this.currentPlayer.idx);
            if (child.disabled && !child.classList.contains('disabled')) {
                child.classList.add('disabled');
            } else if (!child.disabled && child.classList.contains('disabled')) {
                child.classList.remove('disabled');
            }
        });
    }

    /**
     * Starts the game, setting up players and displaying the game board.
     */
    startGame() {
        let selector = document.querySelector("#player-num");
        if (!selector.checkValidity()) {
            alert("Please select a valid number from 2 to 4");
            selector.valueAsNumber = 2;
            return;
        }

        let v = selector.valueAsNumber;
        for (let i = 0; i < v; i++) {
            this.players.push([new Player(0, 0, i + 1), new Player(0, 0, i + 1)]);
        }

        this.playerIterator = this.cyclicIterator(this.players);
        this.currentPlayer = this.playerIterator.next().value;

        document.querySelector("#gameboard").hidden = false;
        document.querySelector("#welcome").hidden = true;
        document.getElementById("dice-results").innerText = `Player ${this.currentPlayer.idx + 1}'s turn`;
        document.getElementById("roll-dice").disabled = false;

        this.renderBoard();
        this.togglePlayerEntanglementButton();
    }

    /**
     * Resets the game state and returns to the welcome screen.
     */
    restart() {
        document.getElementById("win").hidden = true;
        document.querySelector("#gameboard").hidden = true;
        document.querySelector("#welcome").hidden = false;

        this.players = [];
        this.currentPlayer = undefined;
        this.playerIterator = undefined;
        this.entangledPlayers = new Set();
        this.entanglementTimers = {};
        this.eventLog = []; // Clear the event log
        this.updateEventLog(); // Update the event log display
    }

    /**
     * Renders the game board on the UI.
     */
    /**
         * Renders the game board on the UI.
         */
    /**
     * Renders the game board on the UI.
     */
    /**
     * Renders the game board on the UI.
     */
    renderBoard() {
        const boardSizeInfo = calculateSquareSize();
        let boardContainer = document.getElementById("board");
        boardContainer.innerHTML = "";
        boardContainer.style.gridTemplateColumns = `repeat(${width}, 1fr)`;
        boardContainer.style.gridTemplateRows = `repeat(${height}, 1fr)`;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let tile = document.createElement("div");
                tile.classList.add("tile");

                // Calculate the tile number (alternating directions)
                let tileNumber;
                if (y % 2 === 0) {
                    // Even rows: left to right
                    tileNumber = y * width + x + 1;
                } else {
                    // Odd rows: right to left
                    tileNumber = y * width + (width - x);
                }
                // tile.innerText = tileNumber;
                tile.ariaLabel = tileNumber;

                this.players.forEach((playerPieces) => {
                    playerPieces.forEach(piece => {
                        if (piece.x == x && piece.y == y) {
                            tile.appendChild(piece.getDomElement());
                        }
                    });
                });

                if (this.isEntanglementSource(x, y)) {
                    tile.classList.add('entanglement-source');
                } else if (this.isRepeater(x, y)) {
                    tile.classList.add('repeater');
                }

                boardContainer.appendChild(tile);
            }
        }
    }


    /**
     * Checks if the given coordinates are an entanglement source.
     * @param {number} x - The x-coordinate.
     * @param {number} y - The y-coordinate.
     * @returns {boolean} True if it's an entanglement source, false otherwise.
     */
    isEntanglementSource(x, y) {
        return this.entanglementSources.some(source => source.x === x && source.y === y);
    }

    /**
     * Checks if the given coordinates are a repeater.
     * @param {number} x - The x-coordinate.
     * @param {number} y - The y-coordinate.
     * @returns {boolean} True if it's a repeater, false otherwise.
     */
    isRepeater(x, y) {
        return this.repeaters.some(repeater => repeater.x === x && repeater.y === y);
    }

    /**
     * Asynchronously gets the player's selection of which piece to move.
     * @returns {Promise<number>} A promise that resolves with the index of the selected piece (0 or 1).
     */
    async getPieceSelectionFromPlayer() {
        return new Promise(resolve => {
            const controlsDiv = document.getElementById('piece-controls');
            const rollDice = document.getElementById('roll-dice');
            controlsDiv.classList.remove('hidden');
            rollDice.hidden = true;

            const piece1Button = document.getElementById('move-piece-1-btn');
            piece1Button.onclick = () => {
                controlsDiv.classList.add('hidden');
                rollDice.hidden = false;
                resolve(0);
            };

            const piece2Button = document.getElementById('move-piece-2-btn');
            piece2Button.onclick = () => {
                controlsDiv.classList.add('hidden');
                rollDice.hidden = false;
                resolve(1)
            };
        });
    }

    /**
     * Simulates rolling the dice and moves the player's piece.
     * @returns {Promise<number>} A promise that resolves with the result of the dice roll.
     */
    async rollDice(result = null, pieceIndex = null) {
        if (!result) {
            result = randIntv1(6) + 1;
        }
        animateDice(result); // Assuming this function is defined elsewhere
        document.getElementById("dice-results").innerText = `Dice: ${result}`;
        document.getElementById("roll-dice").disabled = true;

        if (pieceIndex === null) {
            pieceIndex = await this.getPieceSelectionFromPlayer();
        }

        this.updateEntanglementTimers();

        const startX = this.currentPlayer.value[pieceIndex].x;
        const startY = this.currentPlayer.value[pieceIndex].y;
        const startTileNumber = this.getTileNumber(startX, startY); // Get tile number at start

        for (let i = 0; i < result; i++) {
            await new Promise(resolve => setTimeout(resolve, movingSpeed));
            this.movePlayer(this.currentPlayer.value[pieceIndex], pieceIndex);
            if (this.checkWin(this.currentPlayer)) return i + 1;
        }

        const playerIndex = this.currentPlayer.idx;

        const endTileNumber = this.getTileNumber(this.currentPlayer.value[pieceIndex].x, this.currentPlayer.value[pieceIndex].y);
        // Add event log entry after attempting to move
        this.logEvent(`Player ${playerIndex + 1} moved piece ${pieceIndex + 1} from ${startTileNumber} to ${endTileNumber}`);

        document.getElementById("roll-dice").disabled = false;
        await new Promise(resolve => setTimeout(resolve, movingSpeed));

        this.checkLadder(this.currentPlayer.value[pieceIndex]);
        this.checkEntanglement(this.currentPlayer.idx);
        this.checksnakes(this.currentPlayer.value[pieceIndex]);

        this.currentPlayer = this.playerIterator.next().value;
        this.togglePlayerEntanglementButton();
        document.getElementById("dice-results").innerText = `Player ${this.currentPlayer.idx + 1}'s turn`;
        this.togglePlayerEntanglementButton();
        return result;
    }

    /**
     * Gets the tile number based on x and y coordinates.
     * @param {number} x - The x-coordinate.
     * @param {number} y - The y-coordinate.
     * @returns {number} The tile number.
     */
    getTileNumber(x, y) {
        if (y % 2 === 0) {
            // Even rows: left to right
            return y * width + x + 1;
        } else {
            // Odd rows: right to left
            return y * width + (width - x);
        }
    }

    /**
     * Updates the entanglement timers for all players.
     */
    updateEntanglementTimers() {
        for (let playerIdx in this.entanglementTimers) {
            this.entanglementTimers[playerIdx]--;
            if (this.entanglementTimers[playerIdx] <= 0) {
                this.disentanglePlayer(parseInt(playerIdx));
            }
        }
    }

    /**
     * Moves the specified player piece.
     * @param {Player} playerPiece - The player piece to move.
     * @param {number} pieceIndex - The index of the piece (0 or 1).
     */
    movePlayer(playerPiece, pieceIndex) {
        const playerIndex = this.currentPlayer.idx;

        if (this.entangledPlayers.has(playerIndex)) {
            this.moveEntangledPieces(playerIndex, pieceIndex);
        } else {
            this.movePiece(playerPiece);
        }

        // This is false, entanglement works till infinite distance.
        // if (this.entangledPlayers.has(playerIndex)) {
        //     const otherPieceIndex = pieceIndex === 0 ? 1 : 0;
        //     const otherPiece = this.currentPlayer.value[otherPieceIndex];
        //     if (this.checkDistance(playerPiece, otherPiece)) {
        //         this.disentanglePlayer(playerIndex);
        //     }
        // }

        this.renderBoard();
    }

    /**
     * Moves a single piece based on its current position.
     * @param {Player} piece - The piece to move.
     */
    movePiece(piece) {
        if (piece.y % 2 == 0) {
            if (piece.x >= width - 1) {
                piece.y++;
            } else {
                piece.x++;
            }
        } else {
            if (piece.x <= 0) {
                piece.y++;
            } else {
                piece.x--;
            }
        }
    }

    /**
     * Moves both pieces of an entangled player, mirroring the movement of the selected piece.
     * @param {number} playerIndex - The index of the entangled player.
     * @param {number} movedPieceIndex - The index of the piece that was selected to move (0 or 1).
     */
    moveEntangledPieces(playerIndex, movedPieceIndex) {
        const playerPieces = this.players[playerIndex];
        const movedPiece = playerPieces[movedPieceIndex];
        const otherPieceIndex = movedPieceIndex === 0 ? 1 : 0;
        const otherPiece = playerPieces[otherPieceIndex];

        this.movePiece(movedPiece);

        if (!this.isObstacle(otherPiece.x, otherPiece.y)) {
            this.movePiece(otherPiece);
        }
    }

    /**
     * Checks if the given coordinates are an obstacle.
     * @param {number} x - The x-coordinate.
     * @param {number} y - The y-coordinate.
     * @returns {boolean} True if it's an obstacle, false otherwise.
     */
    isObstacle(x, y) {
        if (x < 0 || x >= width || y < 0 || y >= height) {
            return true;
        }

        // for (const playerPieces of this.players) {
        //     for (const piece of playerPieces) {
        //         if (piece.x === x && piece.y === y) {
        //             return true;
        //         }
        //     }
        // }

        return false;
    }

    /**
     * Checks for entanglement status changes for the given player.
     * @param {number} playerIndex - The index of the player to check.
     */
    checkEntanglement(playerIndex) {
        const playerPieces = this.players[playerIndex];

        if (playerPieces.some(piece => this.isEntanglementSource(piece.x, piece.y))) {
            if (!this.entangledPlayers.has(playerIndex)) {
                // this.entanglePlayer(playerIndex);
                this.entangleMentTokens[playerIndex] = (this.entangleMentTokens[playerIndex] || 0) + 1;
                this.updateEntanglementTokenDisplay(playerIndex);
                this.logEvent(`Player ${playerIndex + 1} secured an entanglement token`);
            }
        }

        if (playerPieces.some(piece => this.isSnake(piece.x, piece.y))) {
            this.disentanglePlayer(playerIndex);
        }
    }

    updateEntanglementTokenDisplay(playerIndex) {
        const tokenClass = `token-count-${playerIndex + 1}`;
        const tokenDisplay = document.getElementById(tokenClass);
        if (!tokenDisplay) {
            console.log(`Token display not found for player ${playerIndex}. Class ${tokenClass}`);
            return;
        }

        tokenDisplay.innerText = this.entangleMentTokens[playerIndex];
    }

    /**
     * Checks if the distance between two pieces exceeds the maximum entanglement distance.
     * @param {Player} piece1 - The first piece.
     * @param {Player} piece2 - The second piece.
     * @returns {boolean} True if the distance exceeds the maximum, false otherwise.
     */
    checkDistance(piece1, piece2) {
        const distance = manhattanDistance(piece1.x, piece1.y, piece2.x, piece2.y);
        const maxDistance = this.calculateMaxEntanglementDistance(piece1, piece2);
        return distance > maxDistance;
    }

    /**
     * Calculates the maximum entanglement distance, considering repeaters.
     * @param {Player} piece1 - The first piece.
     * @param {Player} piece2 - The second piece.
     * @returns {number} The maximum entanglement distance.
     */
    calculateMaxEntanglementDistance(piece1, piece2) {
        let maxDistance = baseEntanglementDistance;
        let repeatersInRange = 0;

        for (const repeater of this.repeaters) {
            const distanceToPiece1 = manhattanDistance(piece1.x, piece1.y, repeater.x, repeater.y);
            const distanceToPiece2 = manhattanDistance(piece2.x, piece2.y, repeater.x, repeater.y);

            if (distanceToPiece1 <= repeaterRange || distanceToPiece2 <= repeaterRange) {
                repeatersInRange++;
            }
        }

        maxDistance += repeatersInRange * repeaterEntanglementExtension;
        return maxDistance;
    }

    /**
     * Checks if the given coordinates are a snake.
     * @param {number} x - The x-coordinate.
     * @param {number} y - The y-coordinate.
     * @returns {boolean} True if it's a snake, false otherwise.
     */
    isSnake(x, y) {
        return this.snakes.some(snake => snake.startX === x && snake.startY === y);
    }

    /**
     * Entangles the specified player.
     * @param {number} playerIndex - The index of the player to entangle.
     */
    entanglePlayer(playerIndex) {
        if ((playerIndex != this.currentPlayer.idx) || (this.entangleMentTokens[playerIndex] <= 0)) {
            return
        }
        this.entangleMentTokens[playerIndex] -= 1;
        this.entangledPlayers.add(playerIndex);
        this.entanglementTimers[playerIndex] = entanglementDuration;
        this.logEvent(`Player ${playerIndex + 1} got entangled`);
        console.log(`Player ${playerIndex + 1} is now entangled`);
        this.updateEntanglementStatus(playerIndex, true);
        this.updateEntanglementTokenDisplay(playerIndex);
    }

    /**
     * Disentangles the specified player.
     * @param {number} playerIndex - The index of the player to disentangle.
     */
    disentanglePlayer(playerIndex) {
        this.entangledPlayers.delete(playerIndex);
        delete this.entanglementTimers[playerIndex];
        this.logEvent(`Player ${playerIndex + 1} got disentangled`);
        console.log(`Player ${playerIndex + 1} is no longer entangled`);
        this.updateEntanglementStatus(playerIndex, false);
    }

    /**
     * Updates the entanglement status of the specified player in the UI.
     * @param {number} playerIndex - The index of the player.
     * @param {boolean} isEntangled - True if the player is entangled, false otherwise.
     */
    updateEntanglementStatus(playerIndex, isEntangled) {
        const playerPieces = this.players[playerIndex];

        playerPieces.forEach(piece => {
            const pieceElement = piece.getDomElement();
            if (isEntangled) {
                pieceElement.classList.add('entangled');
            } else {
                pieceElement.classList.remove('entangled');
            }
        });
    }

    /**
     * Checks if the specified player has landed on a ladder and moves them accordingly.
     * @param {Player} player - The player to check.
     */
    checkLadder(player) {
        this.ladders.forEach(ladder => {
            if (ladder.startX == player.x && ladder.startY == player.y) {
                const startTileNumber = this.getTileNumber(ladder.startX, ladder.startY); // Get tile number at start
                const endTileNumber = this.getTileNumber(ladder.endX, ladder.endY);

                this.logEvent(`Player ${this.currentPlayer.idx + 1} climbed a ladder from ${startTileNumber} to ${endTileNumber}`);
                player.x = ladder.endX;
                player.y = ladder.endY;
                this.renderBoard();
            }
        });
    }

    /**
     * Checks if the specified player has landed on a snake and moves them accordingly.
     * @param {Player} player - The player to check.
     */
    checksnakes(player) {
        this.snakes.forEach(snake => {
            if (snake.startX == player.x && snake.startY == player.y) {
                const startTileNumber = this.getTileNumber(snake.startX, snake.startY); // Get tile number at start
                const endTileNumber = this.getTileNumber(snake.endX, snake.endY);

                this.logEvent(`Player ${this.currentPlayer.idx + 1} hit a snake at ${startTileNumber} and moved to ${endTileNumber}`);
                player.x = snake.endX;
                player.y = snake.endY;
                this.renderBoard();
            }
        });
    }

    /**
     * Checks if the current player has won the game.
     * @param {Object} data - Data about the current player, including their pieces and index.
     * @returns {boolean} True if the player has won, false otherwise.
     */
    checkWin(data) {
        let playerPieces = data.value;
        let idx = data.idx;

        const bothPiecesAtEnd = playerPieces.every(piece => {
            if (height % 2 == 0) {
                return piece.y >= height - 1 && piece.x <= 0;
            } else {
                return piece.y >= height - 1 && piece.x >= width - 1;
            }
        });

        if (bothPiecesAtEnd) {
            console.log("WIN");
            this.logEvent(`Player ${idx + 1} won the game!`);
            document.getElementById("win").hidden = false;
            document.getElementById("win-text").innerHTML = `Player ${idx + 1} wins`;
            return true;
        }

        return false;
    }

    /**
     * Logs an event to the event log.
     * @param {string} message - The message to log.
     */
    logEvent(message) {
        this.eventLog.push(message);
        this.updateEventLog();
    }

    /**
     * Updates the event log display on the UI.
     */
    updateEventLog() {
        const eventLogElement = document.getElementById("event-log");
        eventLogElement.innerHTML = this.eventLog.map(event => `<p>${event}</p>`).join('');
        eventLogElement.scrollTo(0, eventLogElement.scrollHeight);
    }
}