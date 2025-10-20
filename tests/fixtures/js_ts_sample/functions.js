// Sample JavaScript file with various function types

// Standard function declaration
function greet(name) {
    return `Hello, ${name}!`;
}

// Arrow function
const add = (a, b) => a + b;

// Async function
async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}

// Async arrow function
const processData = async (data) => {
    const processed = await transform(data);
    return processed;
};

// Function with multiple parameters
function calculate(x, y, operation) {
    if (operation === 'add') {
        return x + y;
    } else if (operation === 'multiply') {
        return x * y;
    }
    return 0;
}
