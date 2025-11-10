import './style.scss';

import { initApp } from './init';

const startButton = document.getElementById('startButton');
const startOverlay = document.getElementById('startOverlay');
const storyDetails = document.getElementById('story-details');
const toggleButton = document.getElementById('toggleButton');
const technicalExplanation = document.getElementById('technicalExplanation');


if (startButton) {
    startButton.onclick = () => {
        startOverlay?.classList.add('hidden');
        initApp();
    }
    
    // startButton.click();
}

if(toggleButton) {
    toggleButton.onclick = () => {
        storyDetails?.classList.add('hidden');
        technicalExplanation?.classList.remove('hidden');
    }
}