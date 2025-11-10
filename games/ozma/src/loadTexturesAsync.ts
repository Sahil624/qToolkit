import { Assets } from "pixi.js";

export const loadTexturesAsync = async (textures:{ name: string; url: string }[] ) => {
  return Assets.load(textures.map(x => ({alias: x.name, src: x.url})));
};