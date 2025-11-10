import { randIntv1 } from './utils.js'
import { cssColors } from './consts.js'

export class Player {
	constructor(x, y, id) {
		this.x = x;
		this.y = y;
		this.id = id;
	}
	getDomElement() {
		if (!this.dom) {
			this.dom = document.createElement("div");
			this.dom.classList.add("player");
			let idx = randIntv1(cssColors.length);
			this.dom.style["background"] = cssColors[idx];
			cssColors.splice(idx, 1);
			this.dom.style["marginLeft"] = `${randIntv1(20)}px`;
			this.dom.style["marginTop"] = `${randIntv1(20)}px`;
			let text = document.createTextNode(this.id);
			this.dom.appendChild(text);
		}
		return this.dom;
	}
}
