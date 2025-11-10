export function randIntv1(x) {
	return Math.trunc((Math.random() * 100000) % x);
}

export function calculateSquareSize() {
    const boardImage = document.querySelector('.board-image');
    
    // Get the actual rendered dimensions of the image
    const boardRect = boardImage.getBoundingClientRect();
    const boardWidth = boardRect.width;
    const boardHeight = boardRect.height;
    
    // Assuming a 10x10 grid
    const GRID_SIZE = 10;
    
    // Calculate square dimensions
    const squareWidth = boardWidth / GRID_SIZE;
    const squareHeight = boardHeight / GRID_SIZE;
    
    return {
        width: squareWidth,
        height: squareHeight,
        boardWidth,
        boardHeight,
        // Return positions for a specific square index (0-99)
        getSquarePosition: (index) => {
            // Convert 0-99 index to row/col (0-9)
            const row = 9 - Math.floor(index / 10); // Start from bottom
            const col = row % 2 === 0 
                ? index % 10  // Left to right on even rows
                : 9 - (index % 10); // Right to left on odd rows
            
            return {
                x: col * squareWidth,
                y: row * squareHeight
            };
        }
    };
}

export function manhattanDistance(x1, y1, x2, y2) {
    return Math.abs(x1 - x2) + Math.abs(y1 - y2);
}