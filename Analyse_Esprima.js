const esprima = require('esprima');
const fs = require('fs');

// Define patterns to search for
const dangerousPatterns = {
    eval: 0,
    'document.write': 0,
    setInterval: 0,
    setTimeout: 0,
    innerHTML: 0
};

// Read the JavaScript file path from the command-line arguments
const jsFilePath = process.argv[2];

// Read the JS file content
const jsCode = fs.readFileSync(jsFilePath, 'utf-8');

// Parse the JS code into an AST
const ast = esprima.parseScript(jsCode, { loc: true });

// Function to recursively check for dangerous patterns
function checkNode(node) {
    if (typeof node === 'object' && node !== null) {
        if (node.type === 'CallExpression' && node.callee && node.callee.type === 'Identifier') {
            const functionName = node.callee.name;
            if (dangerousPatterns[functionName] !== undefined) {
                dangerousPatterns[functionName]++;
            }
        }
        for (let key in node) {
            checkNode(node[key]);  // Recurse into each child node
        }
    }
}

// Start checking the AST
checkNode(ast);

// Output the result
console.log(JSON.stringify(dangerousPatterns, null, 2));