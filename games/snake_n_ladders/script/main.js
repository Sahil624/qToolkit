import { startGame2, getGame } from "./index.js";

const drawer = document.getElementById("drawer");

document.getElementById('start-btn').addEventListener('click', () => {
    startGame2();
});

document.getElementById('roll-dice').addEventListener('click', () => {
    getGame().rollDice();
});

document.getElementById('open-drawer').addEventListener('click', () => {
    toggleDrawer();
});

document.getElementById('close-drawer').addEventListener('click', () => {
    toggleDrawer();
});

document.getElementById('p1-token').addEventListener('click', () => {
    getGame().entanglePlayer(0);
});

document.getElementById('p2-token').addEventListener('click', () => {
    getGame().entanglePlayer(1);
});

function toggleDrawer() {
    if(!drawer.style.width || drawer.style.width.startsWith('0')) {
        drawer.style.width = '60%';
    } else {
        drawer.style.width = '0';
    }
}

startGame2();


// Debug Functions Below
async function debugMove(move, pieceIndex) {
    while (move > 0) {
        var thisMove = Math.min(move, 6);
        await getGame().rollDice(thisMove, pieceIndex);
        move -= thisMove;
    }
}

window.debugMove = debugMove;