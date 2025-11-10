export class Ladder {
	constructor(startX, startY, endX, endY) {
		this.startX = startX;
		this.startY = startY;
		this.endX = endX;
		this.endY = endY;
	}
	getAngle() {
		return Math.atan((this.endY - this.startY) / (this.endX - this.startX));
	}
	getLength() {
		return Math.sqrt(Math.pow(this.endY - this.startY, 2) + Math.pow(this.endX - this.startX, 2));
	}
}