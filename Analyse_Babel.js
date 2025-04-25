const fs = require('fs');
const babelParser = require('@babel/parser');

function analyse(jsFilePath) {
    const dangerousPatterns = {};

    const ruleMap = {
        "eval_usage": "eval() usage",
        "new_function_usage": "new Function() usage",
        "dynamic_timer_string": "Dynamic setTimeout/setInterval with string",
        "document_write": "document.write or writeln usage",
        "innerhtml_assignment": "Assignment to innerHTML",
        "chrome_execute_script": "chrome.scripting.executeScript usage",
        "chrome_onmessage_listener": "chrome.runtime.onMessage listener added",
        "storage_access": "localStorage/sessionStorage access"
    };

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

        function increment(ruleId) {
            dangerousPatterns[ruleId] = (dangerousPatterns[ruleId] || 0) + 1;
        }

        function analyseNode(node) {
            if (!node) return;

            if (node.type === 'CallExpression' && node.callee?.name === 'eval') {
                increment('eval_usage');
            }

            if (node.type === 'NewExpression' && node.callee?.name === 'Function') {
                increment('new_function_usage');
            }

            if (
                node.type === 'CallExpression' &&
                (node.callee?.name === 'setTimeout' || node.callee?.name === 'setInterval') &&
                node.arguments?.[0]?.type === 'StringLiteral'
            ) {
                increment('dynamic_timer_string');
            }

            if (
                node.type === 'CallExpression' &&
                node.callee?.type === 'MemberExpression' &&
                node.callee.object?.name === 'document' &&
                ['write', 'writeln'].includes(node.callee.property?.name)
            ) {
                increment('document_write');
            }

            if (
                node.type === 'AssignmentExpression' &&
                node.left?.type === 'MemberExpression' &&
                node.left.property?.name === 'innerHTML'
            ) {
                increment('innerhtml_assignment');
            }

            if (
                node.type === 'CallExpression' &&
                node.callee?.type === 'MemberExpression' &&
                node.callee.object?.type === 'MemberExpression' &&
                node.callee.object.object?.name === 'chrome' &&
                node.callee.object.property?.name === 'scripting' &&
                node.callee.property?.name === 'executeScript'
            ) {
                increment('chrome_execute_script');
            }

            if (
                node.type === 'CallExpression' &&
                node.callee?.type === 'MemberExpression' &&
                node.callee.object?.type === 'MemberExpression' &&
                node.callee.object.object?.name === 'chrome' &&
                node.callee.object.property?.name === 'runtime' &&
                node.callee.property?.name === 'onMessage'
            ) {
                increment('chrome_onmessage_listener');
            }

            if (
                node.type === 'MemberExpression' &&
                ['localStorage', 'sessionStorage'].includes(node.object?.name)
            ) {
                increment('storage_access');
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