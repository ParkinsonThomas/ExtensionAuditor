const fs = require('fs');
const babelParser = require('@babel/parser');

function analyse(jsFilePath) {
    const dangerousPatterns = {};

    try {
        const code = fs.readFileSync(jsFilePath, 'utf8');
        const ast = babelParser.parse(code, {
            sourceType: 'unambiguous',
            plugins: [
                'jsx',
                'typescript',
                'classProperties',
                'dynamicImport',
                'optionalChaining',
                'nullishCoalescingOperator',
                'objectRestSpread',
                'topLevelAwait'
            ]
        });

        function increment(pattern) {
            dangerousPatterns[pattern] = (dangerousPatterns[pattern] || 0) + 1;
        }

        function analyseNode(node) {
            if (!node) return;

            // 1. eval()
            if (node.type === 'CallExpression' && node.callee?.name === 'eval') {
                increment('eval() usage');
            }

            // 2. new Function()
            if (node.type === 'NewExpression' && node.callee?.name === 'Function') {
                increment('new Function() usage');
            }

            // 3. setTimeout / setInterval with string
            if (
                node.type === 'CallExpression' &&
                (node.callee?.name === 'setTimeout' || node.callee?.name === 'setInterval') &&
                node.arguments?.[0]?.type === 'StringLiteral'
            ) {
                increment('Dynamic setTimeout/setInterval with string');
            }

            // 4. document.write / writeln
            if (
                node.type === 'CallExpression' &&
                node.callee?.type === 'MemberExpression' &&
                node.callee.object?.name === 'document' &&
                ['write', 'writeln'].includes(node.callee.property?.name)
            ) {
                increment('document.write or writeln usage');
            }

            // 5. innerHTML assignment
            if (
                node.type === 'AssignmentExpression' &&
                node.left?.type === 'MemberExpression' &&
                node.left.property?.name === 'innerHTML'
            ) {
                increment('Assignment to innerHTML');
            }

            // 6. chrome.scripting.executeScript
            if (
                node.type === 'CallExpression' &&
                node.callee?.type === 'MemberExpression' &&
                node.callee.object?.type === 'MemberExpression' &&
                node.callee.object.object?.name === 'chrome' &&
                node.callee.object.property?.name === 'scripting' &&
                node.callee.property?.name === 'executeScript'
            ) {
                increment('chrome.scripting.executeScript usage');
            }

            // 7. chrome.runtime.onMessage listener
            if (
                node.type === 'CallExpression' &&
                node.callee?.type === 'MemberExpression' &&
                node.callee.object?.type === 'MemberExpression' &&
                node.callee.object.object?.name === 'chrome' &&
                node.callee.object.property?.name === 'runtime' &&
                node.callee.property?.name === 'onMessage'
            ) {
                increment('chrome.runtime.onMessage listener added');
            }

            // 8. localStorage / sessionStorage access
            if (
                node.type === 'MemberExpression' &&
                ['localStorage', 'sessionStorage'].includes(node.object?.name)
            ) {
                increment('localStorage/sessionStorage access');
            }
        }

        function traverse(node) {
            analyseNode(node);
            for (const key in node) {
                const child = node[key];
                if (Array.isArray(child)) {
                    child.forEach(c => typeof c === 'object' && c !== null && traverse(c));
                } else if (child && typeof child.type === 'string') {
                    traverse(child);
                }
            }
        }

        traverse(ast.program || ast);
        console.log(JSON.stringify(dangerousPatterns));
    } catch (e) {
        process.exit(1);
    }
}

const jsFilePath = process.argv[2];
analyse(jsFilePath);