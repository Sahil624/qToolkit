import { calculateSquareSize } from './utils.js'

export let height = 10;
export let width = 10;
export const cssColorsOriginal = ["lightblue", "lightgray", "pink", "red", "yellow"];
export let cssColors = cssColorsOriginal;
export const movingSpeed = 400;


export function updateSquareDimenstion() {
    const boardSizeInfo = calculateSquareSize();

    if(height != boardSizeInfo['height']) {
        console.info(`Updated square size. Old ${height}X${width}. New ${boardSizeInfo['height']}X${boardSizeInfo['width']}`);
    }

    height = boardSizeInfo['height'];
    width = boardSizeInfo['width'];
}

// Entanglement Parameters
export const baseEntanglementDistance = 5;       // X (base maximum entanglement distance)
export const repeaterEntanglementExtension = 2;  // Z (entanglement range extension per repeater)
export const repeaterRange = 3;                  // Y (range within which a repeater affects entanglement)
export const entanglementDuration = 5;         // T (number of dice rolls entanglement lasts)
