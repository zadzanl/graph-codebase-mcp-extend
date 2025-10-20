// Sample JavaScript file with variables and imports

import { helper } from './utils';
import Animal from './classes';

// Top-level const
const API_URL = 'https://api.example.com';

// Top-level let
let counter = 0;

// Top-level var
var globalConfig = {
    timeout: 5000,
    retries: 3
};

// Exported function
export function incrementCounter() {
    counter++;
    return counter;
}

// Exported class
export class DataManager {
    constructor() {
        this.data = [];
    }
    
    addItem(item) {
        this.data.push(item);
    }
}

// Default export
export default function initialize() {
    console.log('Initializing application');
}
